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
from datetime import time
import logbook

import catalyst.protocol as zp
from catalyst.algorithm import TradingAlgorithm
from catalyst.exchange.exchange_clock import ExchangeClock
from catalyst.gens.tradesimulation import AlgorithmSimulator
from catalyst.errors import OrderInBeforeTradingStart
from catalyst.utils.input_validation import error_keywords
from catalyst.utils.api_support import (
    api_method,
    disallowed_in_before_trading_start)

from catalyst.utils.calendars.trading_calendar import days_at_time

log = logbook.Logger("ExchangeTradingAlgorithm")


class ExchangeAlgorithmExecutor(AlgorithmSimulator):
    def __init__(self, *args, **kwargs):
        super(self.__class__, self).__init__(*args, **kwargs)


class ExchangeTradingAlgorithm(TradingAlgorithm):
    def __init__(self, *args, **kwargs):
        self.exchange = kwargs.pop('exchange', None)
        self.orders = {}

        super(self.__class__, self).__init__(*args, **kwargs)

        log.info('exchange trading algorithm successfully initialized')

    def _create_clock(self):
        # This method is taken from TradingAlgorithm.
        # The clock has been replaced to use RealtimeClock
        trading_o_and_c = self.trading_calendar.schedule.ix[
            self.sim_params.sessions]
        market_closes = trading_o_and_c['market_close']
        minutely_emission = False

        if self.sim_params.data_frequency == 'minute':
            market_opens = trading_o_and_c['market_open']

            minutely_emission = self.sim_params.emission_rate == "minute"
        else:
            # in daily mode, we want to have one bar per session, timestamped
            # as the last minute of the session.
            market_opens = market_closes

        # The calendar's execution times are the minutes over which we actually
        # want to run the clock. Typically the execution times simply adhere to
        # the market open and close times. In the case of the futures calendar,
        # for example, we only want to simulate over a subset of the full 24
        # hour calendar, so the execution times dictate a market open time of
        # 6:31am US/Eastern and a close of 5:00pm US/Eastern.
        execution_opens = \
            self.trading_calendar.execution_time_from_open(market_opens)
        execution_closes = \
            self.trading_calendar.execution_time_from_close(market_closes)

        # FIXME generalize these values
        before_trading_start_minutes = days_at_time(
            self.sim_params.sessions,
            time(8, 45),
            "US/Eastern"
        )

        return ExchangeClock(
            self.sim_params.sessions,
            execution_opens,
            execution_closes,
            before_trading_start_minutes,
            minute_emission=minutely_emission,
            time_skew=self.exchange.time_skew
        )

    def _create_generator(self, sim_params):
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

    def handle_data(self, data):
        self.exchange.update_portfolio()
        transactions = self.exchange.check_open_orders()
        for transaction in transactions:
            self.perf_tracker.process_transaction(transaction)

        if self._handle_data:
            self._handle_data(self, data)

        # Unlike trading controls which remain constant unless placing an
        # order, account controls can change each bar. Thus, must check
        # every bar no matter if the algorithm places an order or not.
        self.validate_account_controls()

    @api_method
    @disallowed_in_before_trading_start(OrderInBeforeTradingStart())
    def order(self,
              asset,
              amount,
              limit_price=None,
              stop_price=None,
              style=None):
        amount, style = self._calculate_order(asset, amount,
                                              limit_price, stop_price, style)

        order_id = self.exchange.order(asset, amount, limit_price, stop_price,
                                       style)
        order = self.portfolio.open_orders[order_id]
        self.perf_tracker.process_order(order)
        return order

    @api_method
    def batch_market_order(self, share_counts):
        raise NotImplementedError()

    @error_keywords(sid='Keyword argument `sid` is no longer supported for '
                        'get_open_orders. Use `asset` instead.')
    @api_method
    def get_open_orders(self, asset=None):
        return self.exchange.get_open_orders(asset)

    @api_method
    def get_order(self, order_id):
        return self.exchange.get_order(order_id)

    @api_method
    def cancel_order(self, order_param):
        order_id = order_param
        if isinstance(order_param, zp.Order):
            order_id = order_param.id
        self.exchange.cancel_order(order_id)
