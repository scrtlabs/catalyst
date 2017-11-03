import numpy as np
from logbook import Logger

from catalyst.constants import LOG_LEVEL
from catalyst.protocol import Portfolio, Positions, Position
from catalyst.utils.deprecate import deprecated

log = Logger('ExchangePortfolio', level=LOG_LEVEL)


class ExchangePortfolio(Portfolio):
    """
    Since the goal is to support multiple exchanges, it makes sense to
    include additional stats in the portfolio object.

    Instead of relying on the performance tracker, each exchange portfolio
    tracks its own holding. This offers a separation between tracking an
    exchange and the statistics of the algorithm.
    """

    def __init__(self, start_date, starting_cash=None):
        self.capital_used = 0.0
        self.starting_cash = starting_cash
        self.portfolio_value = starting_cash
        self.pnl = 0.0
        self.returns = 0.0
        self.cash = starting_cash
        self.positions = Positions()
        self.start_date = start_date
        self.positions_value = 0.0
        self.open_orders = dict()

    def create_order(self, order):
        """
        Create an open order and store in memory.

        Parameters
        ----------
        order: Order

        """
        log.debug('creating order {}'.format(order.id))
        self.open_orders[order.id] = order

        order_position = self.positions[order.asset] \
            if order.asset in self.positions else None

        if order_position is None:
            order_position = Position(order.asset)
            self.positions[order.asset] = order_position

        order_position.amount += order.amount
        log.debug('open order added to portfolio')

    def execute_order(self, order, transaction):
        """
        Update the open orders and positions to apply an executed order.

        Unlike with backtesting, we do not need to add slippage and fees.
        The executed price includes transaction fees.

        Parameters
        ----------
        order: Order
        transaction: Transaction

        """
        log.debug('executing order {}'.format(order.id))
        del self.open_orders[order.id]

        order_position = self.positions[order.asset] \
            if order.asset in self.positions else None

        if order_position is None:
            raise ValueError(
                'Trying to execute order for a position not held: %s' % order.id
            )

        self.capital_used += order.amount * transaction.price

        if order.amount > 0:
            if order_position.cost_basis > 0:
                order_position.cost_basis = np.average(
                    [order_position.cost_basis, transaction.price],
                    weights=[order_position.amount, order.amount]
                )
            else:
                order_position.cost_basis = transaction.price

        log.debug('updated portfolio with executed order')

    @deprecated
    def execute_transaction(self, transaction):
        # TODO: almost duplicate of execute_order. Not sure why Poloniex needs this.
        log.debug('executing transaction {}'.format(transaction.order_id))

        order_position = self.positions[transaction.asset] \
            if transaction.asset in self.positions else None

        if order_position is None:
            raise ValueError(
                'Trying to execute transaction for a position not held: %s' % transaction.order_id
            )

        self.capital_used += transaction.amount * transaction.price

        if transaction.amount > 0:
            if order_position.cost_basis > 0:
                order_position.cost_basis = np.average(
                    [order_position.cost_basis, transaction.price],
                    weights=[order_position.amount, transaction.amount]
                )
            else:
                order_position.cost_basis = transaction.price

        log.debug('updated portfolio with executed order')

    def remove_order(self, order):
        """
        Removing an open order.

        Parameters
        ----------
        order: Order

        """
        log.info('removing cancelled order {}'.format(order.id))
        del self.open_orders[order.id]

        order_position = self.positions[order.asset] \
            if order.asset in self.positions else None

        if order_position is None:
            raise ValueError(
                'Trying to remove order for a position not held: %s' % order.id
            )

        order_position.amount -= order.amount

        log.debug('removed order from portfolio')
