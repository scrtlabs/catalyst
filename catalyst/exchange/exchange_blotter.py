from time import sleep

import pandas as pd
from catalyst.assets._assets import TradingPair
from logbook import Logger

from catalyst.constants import LOG_LEVEL
from catalyst.exchange.exchange_errors import ExchangeRequestError, \
    ExchangePortfolioDataError, ExchangeTransactionError
from catalyst.finance.blotter import Blotter
from catalyst.finance.commission import CommissionModel
from catalyst.finance.order import ORDER_STATUS
from catalyst.finance.slippage import SlippageModel
from catalyst.finance.transaction import create_transaction, Transaction
from catalyst.utils.input_validation import expect_types

log = Logger('exchange_blotter', level=LOG_LEVEL)


class TradingPairFeeSchedule(CommissionModel):
    """
    Calculates a commission for a transaction based on a per percentage fee.

    Parameters
    ----------
    maker : float, optional
        The percentage maker fee.

    taker: float, optional
        The percentage taker fee.
    """

    def __init__(self, maker=None, taker=None):
        self.maker = maker
        self.taker = taker

    def __repr__(self):
        return (
            '{class_name}(maker={maker}, '
            'taker={taker})'.format(
                class_name=self.__class__.__name__,
                maker=self.maker,
                taker=self.taker,
            )
        )

    def calculate(self, order, transaction):
        """
        Calculate the final fee based on the order parameters.

        :param order: Order
        :param transaction: Transaction

        :return float:
            The total commission.
        """
        cost = abs(transaction.amount) * transaction.price

        asset = order.asset
        maker = self.maker if self.maker is not None else asset.maker
        taker = self.taker if self.taker is not None else asset.taker

        multiplier = taker
        if order.limit is not None:
            multiplier = maker \
                if ((order.amount > 0 and order.limit < transaction.price)
                    or (order.amount < 0 and order.limit > transaction.price)) \
                   and order.limit_reached else taker

        fee = cost * multiplier
        return fee


class TradingPairFixedSlippage(SlippageModel):
    """
    Model slippage as a fixed spread.

    Parameters
    ----------
    spread : float, optional
        spread / 2 will be added to buys and subtracted from sells.
    """

    def __init__(self, spread=0.0001):
        super(TradingPairFixedSlippage, self).__init__()
        self.spread = spread

    def __repr__(self):
        return '{class_name}(spread={spread})'.format(
            class_name=self.__class__.__name__, spread=self.spread,
        )

    def simulate(self, data, asset, orders_for_asset):
        self._volume_for_bar = 0

        price = data.current(asset, 'close')

        dt = data.current_dt
        for order in orders_for_asset:
            if order.open_amount == 0:
                continue

            order.check_triggers(price, dt)
            if not order.triggered:
                log.debug('order has not reached the trigger at current '
                          'price {}'.format(price))
                continue

            execution_price, execution_volume = self.process_order(data, order)

            transaction = create_transaction(
                order, dt, execution_price, execution_volume
            )

            self._volume_for_bar += abs(transaction.amount)
            yield order, transaction

    def process_order(self, data, order):
        price = data.current(order.asset, 'close')

        if order.amount > 0:
            # Buy order
            adj_price = price * (1 + self.spread)
        else:
            # Sell order
            adj_price = price * (1 - self.spread)

        log.debug('added slippage to price: {} => {}'.format(price, adj_price))

        return adj_price, order.amount


class ExchangeBlotter(Blotter):
    def __init__(self, *args, **kwargs):
        self.simulate_orders = kwargs.pop('simulate_orders', False)

        self.exchanges = kwargs.pop('exchanges', None)
        if not self.exchanges:
            raise ValueError(
                'ExchangeBlotter must have an `exchanges` attribute.'
            )

        super(ExchangeBlotter, self).__init__(*args, **kwargs)

        # Using the equity models for now
        # We may be able to define more sophisticated models based on the fee
        # structure of each exchange.
        self.slippage_models = {
            TradingPair: TradingPairFixedSlippage()
        }
        self.commission_models = {
            TradingPair: TradingPairFeeSchedule()
        }

        self.retry_delay = 5
        self.retry_check_open_orders = 5

    def exchange_order(self, asset, amount, style=None, attempt_index=0):
        try:
            exchange = self.exchanges[asset.exchange]
            return exchange.order(
                asset, amount, style
            )
        except ExchangeRequestError as e:
            log.warn(
                'order attempt {}: {}'.format(attempt_index, e)
            )
            if attempt_index < self.retry_order:
                sleep(self.retry_delay)

                return self.exchange_order(
                    asset, amount, style, attempt_index + 1
                )
            else:
                raise ExchangeTransactionError(
                    transaction_type='order',
                    attempts=attempt_index,
                    error=e
                )

    @expect_types(asset=TradingPair)
    def order(self, asset, amount, style, order_id=None):
        log.debug('ordering {} {}'.format(amount, asset.symbol))
        if amount == 0:
            log.warn('skipping 0 amount orders')
            return None

        if self.simulate_orders:
            return super(ExchangeBlotter, self).order(
                asset, amount, style, order_id
            )

        else:
            order = self.exchange_order(
                asset, amount, style
            )

            self.open_orders[order.asset].append(order)
            self.orders[order.id] = order
            self.new_orders.append(order)

            return order.id

    def check_open_orders(self):
        """
        Loop through the list of open orders in the Portfolio object.
        For each executed order found, create a transaction and apply to the
        Portfolio.

        Returns
        -------
        list[Transaction]

        """
        for asset in self.open_orders:
            exchange = self.exchanges[asset.exchange]

            for order in self.open_orders[asset]:
                log.debug('found open order: {}'.format(order.id))

                new_order, executed_price = exchange.get_order(order.id, asset)
                log.debug(
                    'got updated order {} {}'.format(
                        new_order, executed_price
                    )
                )
                order.status = new_order.status

                if order.status == ORDER_STATUS.FILLED:
                    order.commission = new_order.commission
                    if order.amount != new_order.amount:
                        log.warn(
                            'executed order amount {} differs '
                            'from original'.format(
                                new_order.amount, order.amount
                            )
                        )
                        order.amount = new_order.amount

                    transaction = Transaction(
                        asset=order.asset,
                        amount=order.amount,
                        dt=pd.Timestamp.utcnow(),
                        price=executed_price,
                        order_id=order.id,
                        commission=order.commission
                    )
                    yield order, transaction

                elif order.status == ORDER_STATUS.CANCELLED:
                    yield order, None

                else:
                    delta = pd.Timestamp.utcnow() - order.dt
                    log.info(
                        'order {order_id} still open after {delta}'.format(
                            order_id=order.id,
                            delta=delta
                        )
                    )

    def get_exchange_transactions(self, attempt_index=0):
        closed_orders = []
        transactions = []
        commissions = []

        try:
            for order, txn in self.check_open_orders():
                order.dt = txn.dt

                transactions.append(txn)

                if not order.open:
                    closed_orders.append(order)

            return transactions, commissions, closed_orders

        except ExchangeRequestError as e:
            log.warn(
                'check open orders attempt {}: {}'.format(attempt_index, e)
            )
            if attempt_index < self.retry_check_open_orders:
                sleep(self.retry_delay)
                return self.get_exchange_transactions(attempt_index + 1)

            else:
                raise ExchangePortfolioDataError(
                    data_type='order-status',
                    attempts=attempt_index,
                    error=e
                )

    def get_transactions(self, bar_data):
        if self.simulate_orders:
            return super(ExchangeBlotter, self).get_transactions(bar_data)

        else:
            return self.get_exchange_transactions()
