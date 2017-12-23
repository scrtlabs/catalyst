#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
import pickle
import signal
import sys
from datetime import timedelta
from os import listdir
from os.path import isfile, join
from time import sleep

import logbook
import pandas as pd

import catalyst.protocol as zp
from catalyst.algorithm import TradingAlgorithm
from catalyst.constants import LOG_LEVEL
from catalyst.exchange.exchange_blotter import ExchangeBlotter
from catalyst.exchange.exchange_errors import (
    ExchangeRequestError,
    ExchangePortfolioDataError,
    OrderTypeNotSupported, )
from catalyst.exchange.exchange_execution import ExchangeLimitOrder
from catalyst.exchange.exchange_utils import (
    save_algo_object,
    get_algo_object,
    get_algo_folder,
    get_algo_df,
    save_algo_df,
    group_assets_by_exchange, )
from catalyst.exchange.live_graph_clock import LiveGraphClock
from catalyst.exchange.simple_clock import SimpleClock
from catalyst.exchange.stats_utils import get_pretty_stats, stats_to_s3, \
    stats_to_algo_folder
from catalyst.finance.execution import MarketOrder
from catalyst.finance.performance.period import calc_period_stats
from catalyst.gens.tradesimulation import AlgorithmSimulator
from catalyst.utils.api_support import api_method
from catalyst.utils.input_validation import error_keywords, ensure_upper_case
from catalyst.utils.math_utils import round_nearest
from catalyst.utils.preprocess import preprocess

log = logbook.Logger('exchange_algorithm', level=LOG_LEVEL)


class ExchangeAlgorithmExecutor(AlgorithmSimulator):
    def __init__(self, *args, **kwargs):
        super(self.__class__, self).__init__(*args, **kwargs)


class ExchangeTradingAlgorithmBase(TradingAlgorithm):
    def __init__(self, *args, **kwargs):
        self.exchanges = kwargs.pop('exchanges', None)
        self.simulate_orders = kwargs.pop('simulate_orders', None)

        super(ExchangeTradingAlgorithmBase, self).__init__(*args, **kwargs)

        self.current_day = None

        if self.simulate_orders is None \
                and self.sim_params.arena == 'backtest':
            self.simulate_orders = True

        self.blotter = ExchangeBlotter(
            data_frequency=self.data_frequency,
            # Default to NeverCancel in catalyst
            cancel_policy=self.cancel_policy,
            simulate_orders=self.simulate_orders,
            exchanges=self.exchanges
        )

    @staticmethod
    def __convert_order_params_for_blotter(limit_price, stop_price, style):
        """
        Helper method for converting deprecated limit_price and stop_price
        arguments into ExecutionStyle instances.

        This function assumes that either style == None or (limit_price,
        stop_price) == (None, None).
        """
        if stop_price:
            raise OrderTypeNotSupported(order_type='stop')

        if style:
            if limit_price is not None:
                raise ValueError(
                    'An order style and a limit price was included in the '
                    'order. Please pick one to avoid any possible conflict.'
                )

            # Currently limiting order types or limit and market to
            # be in-line with CXXT and many exchanges. We'll consider
            # adding more order types in the future.
            if not isinstance(style, ExchangeLimitOrder) or \
                    not isinstance(style, MarketOrder):
                raise OrderTypeNotSupported(
                    order_type=style.__class__.__name__
                )

            return style

        if limit_price:
            return ExchangeLimitOrder(limit_price)
        else:
            return MarketOrder()

    @api_method
    def set_commission(self, maker=None, taker=None):
        key = self.blotter.commission_models.keys()[0]
        if maker is not None:
            self.blotter.commission_models[key].maker = maker

        if taker is not None:
            self.blotter.commission_models[key].taker = taker

    @api_method
    def set_slippage(self, spread=None):
        key = self.blotter.slippage_models.keys()[0]
        if spread is not None:
            self.blotter.slippage_models[key].spread = spread

    def _calculate_order(self, asset, amount,
                         limit_price=None, stop_price=None, style=None):
        # Raises a ZiplineError if invalid parameters are detected.
        self.validate_order_params(asset,
                                   amount,
                                   limit_price,
                                   stop_price,
                                   style)

        # Convert deprecated limit_price and stop_price parameters to use
        # ExecutionStyle objects.
        style = self.__convert_order_params_for_blotter(limit_price,
                                                        stop_price,
                                                        style)
        return amount, style

    def round_order(self, amount, asset):
        """
        We need fractions with cryptocurrencies

        :param amount:
        :return:
        """
        return round_nearest(amount, asset.min_trade_size)

    @api_method
    @preprocess(symbol_str=ensure_upper_case)
    def symbol(self, symbol_str, exchange_name=None):
        """Lookup an Equity by its ticker symbol.

        Parameters
        ----------
        symbol_str : str
            The ticker symbol for the equity to lookup.
        exchange_name: str
            The name of the exchange containing the symbol

        Returns
        -------
        equity : Equity
            The equity that held the ticker symbol on the current
            symbol lookup date.

        Raises
        ------
        SymbolNotFound
            Raised when the symbols was not held on the current lookup date.

        See Also
        --------
        :func:`catalyst.api.set_symbol_lookup_date`
        """
        # If the user has not set the symbol lookup date,
        # use the end_session as the date for sybmol->sid resolution.

        _lookup_date = self._symbol_lookup_date \
            if self._symbol_lookup_date is not None \
            else self.sim_params.end_session

        if exchange_name is None:
            exchange = list(self.exchanges.values())[0]
        else:
            exchange = self.exchanges[exchange_name]

        data_frequency = self.data_frequency \
            if self.sim_params.arena == 'backtest' else None
        return self.asset_finder.lookup_symbol(
            symbol=symbol_str,
            exchange=exchange,
            data_frequency=data_frequency,
            as_of_date=_lookup_date
        )

    def prepare_period_stats(self, start_dt, end_dt):
        """
        Creates a dictionary representing the state of the tracker.

        Parameters
        ----------
        start_dt: datetime
        end_dt: datetime

        Notes
        -----
        I rewrote this in an attempt to better control the stats.
        I don't want things to happen magically through complex logic
        pertaining to backtesting.

        """
        tracker = self.perf_tracker
        period = tracker.todays_performance

        pos_stats = period.position_tracker.stats()
        period_stats = calc_period_stats(pos_stats, period.ending_cash)

        stats = dict(
            period_start=tracker.period_start,
            period_end=tracker.period_end,
            capital_base=tracker.capital_base,
            progress=tracker.progress,
            ending_value=period.ending_value,
            ending_exposure=period.ending_exposure,
            capital_used=period.cash_flow,
            starting_value=period.starting_value,
            starting_exposure=period.starting_exposure,
            starting_cash=period.starting_cash,
            ending_cash=period.ending_cash,
            portfolio_value=period.ending_cash + period.ending_value,
            pnl=period.pnl,
            returns=period.returns,
            period_open=period.period_open,
            period_close=period.period_close,
            gross_leverage=period_stats.gross_leverage,
            net_leverage=period_stats.net_leverage,
            short_exposure=pos_stats.short_exposure,
            long_exposure=pos_stats.long_exposure,
            short_value=pos_stats.short_value,
            long_value=pos_stats.long_value,
            longs_count=pos_stats.longs_count,
            shorts_count=pos_stats.shorts_count,
        )

        # Merging cumulative risk
        stats.update(tracker.cumulative_risk_metrics.to_dict())

        # Merging latest recorded variables
        stats.update(self.recorded_vars)

        stats['positions'] = period.position_tracker.get_positions_list()

        # we want the key to be absent, not just empty
        # Only include transactions for given dt
        stats['transactions'] = []
        for date in period.processed_transactions:
            if start_dt <= date < end_dt:
                transactions = period.processed_transactions[date]
                for t in transactions:
                    stats['transactions'].append(t.to_dict())

        stats['orders'] = []
        for date in period.orders_by_modified:
            if start_dt <= date < end_dt:
                orders = period.orders_by_modified[date]
                for order in orders:
                    stats['orders'].append(orders[order].to_dict())

        return stats


class ExchangeTradingAlgorithmBacktest(ExchangeTradingAlgorithmBase):
    def __init__(self, *args, **kwargs):
        super(ExchangeTradingAlgorithmBacktest, self).__init__(*args, **kwargs)

        self.frame_stats = list()
        log.info('initialized trading algorithm in backtest mode')

    def is_last_frame_of_day(self, data):
        # TODO: adjust here to support more intervals
        next_frame_dt = data.current_dt + timedelta(minutes=1)
        if next_frame_dt.date() > data.current_dt.date():
            return True
        else:
            return False

    def handle_data(self, data):
        super(ExchangeTradingAlgorithmBacktest, self).handle_data(data)

        if self.data_frequency == 'minute':
            frame_stats = self.prepare_period_stats(
                data.current_dt, data.current_dt + timedelta(minutes=1)
            )
            self.frame_stats.append(frame_stats)

        self.current_day = data.current_dt.floor('1D')

    def _create_stats_df(self):
        stats = pd.DataFrame(self.frame_stats)
        stats.set_index('period_close', inplace=True, drop=False)
        return stats

    def analyze(self, perf):
        stats = self._create_stats_df() if self.data_frequency == 'minute' \
            else perf
        super(ExchangeTradingAlgorithmBacktest, self).analyze(stats)

    def run(self, data=None, overwrite_sim_params=True):
        perf = super(ExchangeTradingAlgorithmBacktest, self).run(
            data, overwrite_sim_params
        )
        # Rebuilding the stats to support minute data
        stats = self._create_stats_df() if self.data_frequency == 'minute' \
            else perf
        return stats


class ExchangeTradingAlgorithmLive(ExchangeTradingAlgorithmBase):
    def __init__(self, *args, **kwargs):
        self.algo_namespace = kwargs.pop('algo_namespace', None)
        self.live_graph = kwargs.pop('live_graph', None)
        self.stats_output = kwargs.pop('stats_output', None)

        self._clock = None
        self.frame_stats = list()

        self.pnl_stats = get_algo_df(self.algo_namespace, 'pnl_stats')

        self.custom_signals_stats = \
            get_algo_df(self.algo_namespace, 'custom_signals_stats')

        self.exposure_stats = \
            get_algo_df(self.algo_namespace, 'exposure_stats')

        self.is_running = True

        self.retry_check_open_orders = 5
        self.retry_synchronize_portfolio = 5
        self.retry_get_open_orders = 5
        self.retry_order = 2
        self.retry_delay = 5

        self.stats_minutes = 10

        super(ExchangeTradingAlgorithmLive, self).__init__(*args, **kwargs)

        signal.signal(signal.SIGINT, self.signal_handler)

        log.info('initialized trading algorithm in live mode')

    def signal_handler(self, signal, frame):
        """
        Handles the keyboard interruption signal.

        Parameters
        ----------
        signal
        frame

        Returns
        -------

        """
        self.is_running = False

        if self._analyze is None:
            log.info('Interruption signal detected {}, exiting the '
                     'algorithm'.format(signal))

        else:
            log.info('Interruption signal detected {}, calling `analyze()` '
                     'before exiting the algorithm'.format(signal))

            algo_folder = get_algo_folder(self.algo_namespace)
            folder = join(algo_folder, 'daily_perf')
            files = [f for f in listdir(folder) if isfile(join(folder, f))]

            daily_perf_list = []
            for item in files:
                filename = join(folder, item)
                with open(filename, 'rb') as handle:
                    daily_perf_list.append(pickle.load(handle))

            stats = pd.DataFrame(daily_perf_list)

            self.analyze(stats)

        sys.exit(0)

    @property
    def clock(self):
        if self._clock is None:
            return self._create_clock()
        else:
            return self._clock

    def _create_clock(self):

        # The calendar's execution times are the minutes over which we actually
        # want to run the clock. Typically the execution times simply adhere to
        # the market open and close times. In the case of the futures calendar,
        # for example, we only want to simulate over a subset of the full 24
        # hour calendar, so the execution times dictate a market open time of
        # 6:31am US/Eastern and a close of 5:00pm US/Eastern.

        # In our case, we are trading around the clock, so the market close
        # corresponds to the last minute of the day.

        # This method is taken from TradingAlgorithm.
        # The clock has been replaced to use RealtimeClock
        # TODO: should we apply time skew? not sure to understand the utility.

        log.debug('creating clock')
        if self.live_graph:
            self._clock = LiveGraphClock(
                self.sim_params.sessions,
                context=self
            )
        else:
            self._clock = SimpleClock(
                self.sim_params.sessions,
            )

        return self._clock

    def _create_generator(self, sim_params):
        if self.perf_tracker is None:
            self.perf_tracker = get_algo_object(
                algo_name=self.algo_namespace,
                key='perf_tracker'
            )

        # Call the simulation trading algorithm for side-effects:
        # it creates the perf tracker
        TradingAlgorithm._create_generator(self, sim_params)
        self.trading_client = ExchangeAlgorithmExecutor(
            self,
            sim_params,
            self.data_portal,
            self.clock,
            self._create_benchmark_source(),
            self.restrictions,
            universe_func=self._calculate_universe
        )

        return self.trading_client.transform()

    def updated_portfolio(self):
        return self.perf_tracker.get_portfolio(False)

    def updated_account(self):
        return self.perf_tracker.get_account(False)

    def synchronize_portfolio(self, attempt_index=0):
        """
        Synchronizes the portfolio tracked by the algorithm to refresh
        its current value.

        This includes updating the last_sale_price of all tracked
        positions, returning the available cash, and raising error
        if the data goes out of sync.

        Parameters
        ----------
        attempt_index: int

        Returns
        -------
        float
            The amount of base currency available for trading.

        float
            The total value of all tracked positions.

        """
        tracker = self.perf_tracker.position_tracker
        total_cash = 0.0
        total_positions_value = 0.0

        try:
            # Position keys correspond to assets
            positions = self.portfolio.positions
            assets = list(positions)
            exchange_assets = group_assets_by_exchange(assets)
            for exchange_name in self.exchanges:
                assets = exchange_assets[exchange_name] \
                    if exchange_name in exchange_assets else []

                exchange_positions = \
                    [positions[asset] for asset in assets]

                check_cash = (not self.simulate_orders)

                exchange = self.exchanges[exchange_name]  # Type: Exchange
                cash, positions_value = exchange.calculate_totals(
                    positions=exchange_positions,
                    check_cash=check_cash,
                )
                total_positions_value += positions_value

                if cash is not None:
                    total_cash += cash

                for position in exchange_positions:
                    tracker.update_position(
                        asset=position.asset,
                        last_sale_date=position.last_sale_date,
                        last_sale_price=position.last_sale_price
                    )

            if cash is None:
                total_cash = self.portfolio.cash

            elif total_cash < self.portfolio.cash:
                raise ValueError('Cash on exchanges is lower than the algo.')

            return total_cash, total_positions_value

        except ExchangeRequestError as e:
            log.warn(
                'update portfolio attempt {}: {}'.format(attempt_index, e)
            )
            if attempt_index < self.retry_synchronize_portfolio:
                sleep(self.retry_delay)
                return self.synchronize_portfolio(attempt_index + 1)
            else:
                raise ExchangePortfolioDataError(
                    data_type='update-portfolio',
                    attempts=attempt_index,
                    error=e
                )

    def add_pnl_stats(self, period_stats):
        """
        Save p&l stats.

        Parameters
        ----------
        period_stats

        Returns
        -------

        """
        starting = period_stats['starting_cash']
        current = period_stats['portfolio_value']
        appreciation = (current / starting) - 1
        perc = (appreciation * 100) if current != 0 else 0

        log.debug('adding pnl stats: {:6f}%'.format(perc))

        df = pd.DataFrame(
            data=[dict(performance=perc)],
            index=[period_stats['period_close']]
        )
        self.pnl_stats = pd.concat([self.pnl_stats, df])

        save_algo_df(self.algo_namespace, 'pnl_stats', self.pnl_stats)

    def add_custom_signals_stats(self, period_stats):
        """
        Save custom signals stats.

        Parameters
        ----------
        period_stats

        Returns
        -------

        """
        log.debug('adding custom signals stats: {}'.format(self.recorded_vars))
        df = pd.DataFrame(
            data=[self.recorded_vars],
            index=[period_stats['period_close']],
        )
        self.custom_signals_stats = pd.concat([self.custom_signals_stats, df])

        save_algo_df(self.algo_namespace, 'custom_signals_stats',
                     self.custom_signals_stats)

    def add_exposure_stats(self, period_stats):
        """
        Save exposure stats.

        Parameters
        ----------
        period_stats

        Returns
        -------

        """
        data = dict(
            long_exposure=period_stats['long_exposure'],
            base_currency=period_stats['ending_cash']
        )
        log.debug('adding exposure stats: {}'.format(data))

        df = pd.DataFrame(
            data=[data],
            index=[period_stats['period_close']],
        )
        self.exposure_stats = pd.concat([self.exposure_stats, df])

        save_algo_df(
            self.algo_namespace, 'exposure_stats', self.exposure_stats
        )

    def handle_data(self, data):
        """
        Wrapper around the handle_data method of each algo.

        Parameters
        ----------
        data

        """
        if not self.is_running:
            return

        # Resetting the frame stats every day to minimize memory footprint
        today = data.current_dt.floor('1D')
        if self.current_day is not None and today > self.current_day:
            self.frame_stats = list()

        new_transactions, new_commissions, closed_orders = \
            self.blotter.get_transactions(data)

        if len(new_transactions) > 0:
            self.perf_tracker.update_performance()

        cash, positions_value = self.synchronize_portfolio()
        log.info(
            'got totals from exchanges, cash: {} positions: {}'.format(
                cash, positions_value
            )
        )
        if self._handle_data:
            self._handle_data(self, data)

        # Unlike trading controls which remain constant unless placing an
        # order, account controls can change each bar. Thus, must check
        # every bar no matter if the algorithm places an order or not.
        self.validate_account_controls()

        try:
            self._save_stats_csv(self._process_stats(data))
        except Exception as e:
            log.warn('unable to calculate performance: {}'.format(e))

        # TODO: pickle does not seem to work in python 3
        try:
            save_algo_object(
                algo_name=self.algo_namespace,
                key='perf_tracker',
                obj=self.perf_tracker
            )
        except Exception as e:
            log.warn('unable to save minute perfs to disk: {}'.format(e))

        self.current_day = data.current_dt.floor('1D')

    def _process_stats(self, data):
        today = data.current_dt.floor('1D')

        # Since the clock runs 24/7, I trying to disable the daily
        # Performance tracker and keep only minute and cumulative
        self.perf_tracker.update_performance()

        frame_stats = self.prepare_period_stats(
            data.current_dt, data.current_dt + timedelta(minutes=1)
        )

        # Saving the last hour in memory
        self.frame_stats.append(frame_stats)

        self.add_pnl_stats(frame_stats)
        if self.recorded_vars:
            self.add_custom_signals_stats(frame_stats)
            recorded_cols = list(self.recorded_vars.keys())

        else:
            recorded_cols = None

        self.add_exposure_stats(frame_stats)

        log.info(
            'statistics for the last {stats_minutes} minutes:\n'
            '{stats}'.format(
                stats_minutes=self.stats_minutes,
                stats=get_pretty_stats(
                    stats=self.frame_stats,
                    recorded_cols=recorded_cols,
                    num_rows=self.stats_minutes
                )
            ))

        # Saving the daily stats in a format usable for performance
        # analysis.
        daily_stats = self.prepare_period_stats(
            start_dt=today,
            end_dt=data.current_dt
        )
        save_algo_object(
            algo_name=self.algo_namespace,
            key=today.strftime('%Y-%m-%d'),
            obj=daily_stats,
            rel_path='daily_perf'
        )

        return recorded_cols

    def _save_stats_csv(self, recorded_cols):
        # Writing the stats output
        csv_bytes = None
        try:
            csv_bytes = stats_to_algo_folder(
                stats=self.frame_stats,
                algo_namespace=self.algo_namespace,
                recorded_cols=recorded_cols,
            )
        except Exception as e:
            log.warn('unable save stats locally: {}'.format(e))

        try:
            if self.stats_output is not None:
                if 's3://' in self.stats_output:
                    stats_to_s3(
                        uri=self.stats_output,
                        stats=self.frame_stats,
                        algo_namespace=self.algo_namespace,
                        recorded_cols=recorded_cols,
                        bytes_to_write=csv_bytes
                    )
                else:
                    raise ValueError(
                        'Only S3 stats output is supported for now.'
                    )
        except Exception as e:
            log.warn('unable save stats externally: {}'.format(e))

    @api_method
    def batch_market_order(self, share_counts):
        raise NotImplementedError()

    def _get_open_orders(self, asset=None, attempt_index=0):
        try:
            if asset:
                exchange = self.exchanges[asset.exchange]
                return exchange.get_open_orders(asset)

            else:
                open_orders = []
                for exchange_name in self.exchanges:
                    exchange = self.exchanges[exchange_name]
                    exchange_orders = exchange.get_open_orders()
                    open_orders.append(exchange_orders)

                return open_orders
        except ExchangeRequestError as e:
            log.warn(
                'open orders attempt {}: {}'.format(attempt_index, e)
            )
            if attempt_index < self.retry_get_open_orders:
                sleep(self.retry_delay)
                return self._get_open_orders(asset, attempt_index + 1)
            else:
                raise ExchangePortfolioDataError(
                    data_type='open-orders',
                    attempts=attempt_index,
                    error=e
                )

    @error_keywords(sid='Keyword argument `sid` is no longer supported for '
                        'get_open_orders. Use `asset` instead.')
    @api_method
    def get_open_orders(self, asset=None):
        """Retrieve all of the current open orders.

        Parameters
        ----------
        asset : Asset
            If passed and not None, return only the open orders for the given
            asset instead of all open orders.

        Returns
        -------
        open_orders : dict[list[Order]] or list[Order]
            If no asset is passed this will return a dict mapping Assets
            to a list containing all the open orders for the asset.
            If an asset is passed then this will return a list of the open
            orders for this asset.
        """
        return self._get_open_orders(asset)

    @api_method
    def get_order(self, order_id, exchange_name):
        """Lookup an order based on the order id returned from one of the
        order functions.

        Parameters
        ----------
        order_id : str
            The unique identifier for the order.

        Returns
        -------
        order : Order
            The order object.
        execution_price: float
            The execution price per share of the order
        """
        exchange = self.exchanges[exchange_name]
        return exchange.get_order(order_id)

    @api_method
    def cancel_order(self, order_param, exchange_name):
        """Cancel an open order.

        Parameters
        ----------
        order_param : str or Order
            The order_id or order object to cancel.
        """
        exchange = self.exchanges[exchange_name]

        order_id = order_param
        if isinstance(order_param, zp.Order):
            order_id = order_param.id

        exchange.cancel_order(order_id)
