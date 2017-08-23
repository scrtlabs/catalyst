import numpy as np
from logbook import Logger

from catalyst.protocol import Portfolio, Positions, Position

log = Logger('ExchangePortfolio')


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

    def calculate_pnl(self):
        log.debug('calculating pnl')

    def create_order(self, order):
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

    def remove_order(self, order):
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
