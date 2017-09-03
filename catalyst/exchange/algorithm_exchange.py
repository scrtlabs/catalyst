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
import os
import signal
import sys
import pickle
from datetime import timedelta
from time import sleep
from os import listdir
from os.path import isfile, join
from collections import deque

import logbook
import pandas as pd

import catalyst.protocol as zp
from catalyst.algorithm import TradingAlgorithm
from catalyst.data.minute_bars import BcolzMinuteBarWriter, \
    BcolzMinuteBarReader
from catalyst.errors import OrderInBeforeTradingStart
from catalyst.exchange.exchange_clock import ExchangeClock
from catalyst.exchange.exchange_errors import (
    ExchangeRequestError,
    ExchangePortfolioDataError,
    ExchangeTransactionError
)
from catalyst.exchange.exchange_utils import get_exchange_minute_writer_root, \
    save_algo_object, get_algo_object, get_algo_folder
from catalyst.exchange.stats_utils import get_pretty_stats
from catalyst.finance.performance.period import calc_period_stats
from catalyst.gens.tradesimulation import AlgorithmSimulator
from catalyst.utils.api_support import (
    api_method,
    disallowed_in_before_trading_start)
from catalyst.utils.input_validation import error_keywords

log = logbook.Logger("ExchangeTradingAlgorithm")


class ExchangeAlgorithmExecutor(AlgorithmSimulator):
    def __init__(self, *args, **kwargs):
        super(self.__class__, self).__init__(*args, **kwargs)


class ExchangeTradingAlgorithm(TradingAlgorithm):
    def __init__(self, *args, **kwargs):
        self.exchange = kwargs.pop('exchange', None)
        self.algo_namespace = kwargs.pop('algo_namespace', None)
        self.orders = {}
        self.minute_stats = deque(maxlen=60)
        self.is_running = True

        self.retry_check_open_orders = 5
        self.retry_synchronize_portfolio = 5
        self.retry_get_open_orders = 5
        self.retry_order = 2
        self.retry_delay = 5

        self.stats_minutes = 5

        super(self.__class__, self).__init__(*args, **kwargs)
        # self._create_minute_writer()

        signal.signal(signal.SIGINT, self.signal_handler)

        log.info('exchange trading algorithm successfully initialized')

    def _create_minute_writer(self):
        root = get_exchange_minute_writer_root(self.exchange.name)
        filename = os.path.join(root, 'metadata.json')

        if os.path.isfile(filename):
            writer = BcolzMinuteBarWriter.open(
                root, self.sim_params.end_session)
        else:
            writer = BcolzMinuteBarWriter(
                rootdir=root,
                calendar=self.trading_calendar,
                minutes_per_day=1440,
                start_session=self.sim_params.start_session,
                end_session=self.sim_params.end_session,
                write_metadata=True
            )

        self.exchange.minute_writer = writer
        self.exchange.minute_reader = BcolzMinuteBarReader(root)

    def signal_handler(self, signal, frame):
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
        # TODO: should we apply a time skew? not sure to understand the utility.
        return ExchangeClock(
            self.sim_params.sessions,
            time_skew=self.exchange.time_skew
        )

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
            self._create_clock(),
            self._create_benchmark_source(),
            self.restrictions,
            universe_func=self._calculate_universe
        )

        return self.trading_client.transform()

    def updated_portfolio(self):
        """
        We skip the entire performance tracker business and update the
        portfolio directly.
        :return:
        """
        return self.exchange.portfolio

    def updated_account(self):
        return self.exchange.account

    def _synchronize_portfolio(self, attempt_index=0):
        try:
            self.exchange.synchronize_portfolio()

            # Applying the updated last_sales_price to the positions
            # in the performance tracker. This seems a bit redundant
            # but it will make sense when we have multiple exchange portfolios
            # feeding into the same performance tracker.
            tracker = self.perf_tracker.todays_performance.position_tracker
            for asset in self.exchange.portfolio.positions:
                position = self.exchange.portfolio.positions[asset]
                tracker.update_position(
                    asset=asset,
                    last_sale_date=position.last_sale_date,
                    last_sale_price=position.last_sale_price
                )
        except ExchangeRequestError as e:
            log.warn(
                'update portfolio attempt {}: {}'.format(attempt_index, e)
            )
            if attempt_index < self.retry_synchronize_portfolio:
                sleep(self.retry_delay)
                self._synchronize_portfolio(attempt_index + 1)
            else:
                raise ExchangePortfolioDataError(
                    data_type='update-portfolio',
                    attempts=attempt_index,
                    error=e
                )

    def _check_open_orders(self, attempt_index=0):
        try:
            return self.exchange.check_open_orders()
        except ExchangeRequestError as e:
            log.warn(
                'check open orders attempt {}: {}'.format(attempt_index, e)
            )
            if attempt_index < self.retry_check_open_orders:
                sleep(self.retry_delay)
                return self._check_open_orders(attempt_index + 1)
            else:
                raise ExchangePortfolioDataError(
                    data_type='order-status',
                    attempts=attempt_index,
                    error=e
                )

    def prepare_period_stats(self, start_dt, end_dt):
        """
        Creates a dictionary representing the state of the tracker.


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
        stats['transactions'] = dict()
        for date in period.processed_transactions:
            if start_dt <= date < end_dt:
                stats['transactions'][date] = \
                    period.processed_transactions[date]

        stats['orders'] = dict()
        for date in period.orders_by_modified:
            if start_dt <= date < end_dt:
                stats['orders'][date] = \
                    period.orders_by_modified[date]

        return stats

    def handle_data(self, data):
        if not self.is_running:
            return

        self._synchronize_portfolio()

        transactions = self._check_open_orders()
        for transaction in transactions:
            self.perf_tracker.process_transaction(transaction)

        if self._handle_data:
            self._handle_data(self, data)

        # Unlike trading controls which remain constant unless placing an
        # order, account controls can change each bar. Thus, must check
        # every bar no matter if the algorithm places an order or not.
        self.validate_account_controls()

        try:
            # Since the clock runs 24/7, I trying to disable the daily
            # Performance tracker and keep only minute and cumulative
            self.perf_tracker.update_performance()

            minute_stats = self.prepare_period_stats(
                data.current_dt, data.current_dt + timedelta(minutes=1))
            # Saving the last hour in memory
            self.minute_stats.append(minute_stats)

            print_df = pd.DataFrame(list(self.minute_stats))
            log.debug(
                'statistics for the last {stats_minutes} minutes:\n{stats}'.format(
                    stats_minutes=self.stats_minutes,
                    stats=get_pretty_stats(print_df, self.stats_minutes)
                ))

            today = pd.to_datetime('today', utc=True)
            daily_stats = self.prepare_period_stats(
                start_dt=today,
                end_dt=pd.Timestamp.utcnow()
            )
            save_algo_object(
                algo_name=self.algo_namespace,
                key=today.strftime('%Y-%m-%d'),
                obj=daily_stats,
                rel_path='daily_perf'
            )

        except Exception as e:
            log.warn('unable to calculate performance: {}'.format(e))

        try:
            save_algo_object(
                algo_name=self.algo_namespace,
                key='perf_tracker',
                obj=self.perf_tracker
            )
        except Exception as e:
            log.warn('unable to save minute perfs to disk: {}'.format(e))

        try:
            save_algo_object(
                algo_name=self.algo_namespace,
                key='portfolio_{}'.format(self.exchange.name),
                obj=self.exchange.portfolio
            )
        except Exception as e:
            log.warn('unable to save portfolio to disk: {}'.format(e))

    def _order(self,
               asset,
               amount,
               limit_price=None,
               stop_price=None,
               style=None,
               attempt_index=0):
        try:
            return self.exchange.order(asset, amount, limit_price,
                                       stop_price,
                                       style)
        except ExchangeRequestError as e:
            log.warn(
                'order attempt {}: {}'.format(attempt_index, e)
            )
            if attempt_index < self.retry_order:
                sleep(self.retry_delay)
                return self._order(
                    asset, amount, limit_price, stop_price, style,
                    attempt_index + 1)
            else:
                raise ExchangeTransactionError(
                    transaction_type='order',
                    attempts=attempt_index,
                    error=e
                )

    @api_method
    @disallowed_in_before_trading_start(OrderInBeforeTradingStart())
    def order(self,
              asset,
              amount,
              limit_price=None,
              stop_price=None,
              style=None):
        amount, style = self._calculate_order(asset, amount,
                                              limit_price, stop_price,
                                              style)

        order_id = self._order(asset, amount, limit_price, stop_price, style)

        if order_id is not None:
            order = self.portfolio.open_orders[order_id]
            self.perf_tracker.process_order(order)

        return order

    def round_order(self, amount):
        """
        We need fractions with cryptocurrencies

        :param amount:
        :return:
        """
        return amount

    @api_method
    def batch_market_order(self, share_counts):
        raise NotImplementedError()

    def _get_open_orders(self, asset=None, attempt_index=0):
        try:
            return self.exchange.get_open_orders(asset)
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
        return self._get_open_orders(asset)

    @api_method
    def get_order(self, order_id):
        return self.exchange.get_order(order_id)

    @api_method
    def cancel_order(self, order_param):
        order_id = order_param
        if isinstance(order_param, zp.Order):
            order_id = order_param.id
        self.exchange.cancel_order(order_id)
