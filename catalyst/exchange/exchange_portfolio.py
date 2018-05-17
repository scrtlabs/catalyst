import numpy as np
from catalyst.constants import LOG_LEVEL
from catalyst.protocol import Portfolio, Positions, Position
from logbook import Logger

log = Logger('ExchangePortfolio', level=LOG_LEVEL)


class ExchangePortfolio(Portfolio):
    """
    Since the goal is to support multiple exchanges, it makes sense to
    include additional stats in the portfolio object. This fills the role
    of Blotter and Portfolio in live mode.

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

        open_orders = self.open_orders[order.asset] \
            if order.asset is self.open_orders else []

        open_orders.append(order)

        self.open_orders[order.asset] = open_orders

        order_position = self.positions[order.asset] \
            if order.asset in self.positions else None

        if order_position is None:
            order_position = Position(order.asset)
            self.positions[order.asset] = order_position

        order_position.amount += order.amount
        log.debug('open order added to portfolio')

    def _remove_open_order(self, order):
        try:
            open_orders = self.open_orders[order.asset]
            if order in open_orders:
                open_orders.remove(order)

        except Exception:
            raise ValueError(
                'unable to clear order not found in open order list.'
            )

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
        self._remove_open_order(order)

        order_position = self.positions[order.asset] \
            if order.asset in self.positions else None

        if order_position is None:
            raise ValueError(
                'Trying to execute order for a position not held:'
                ' {}'.format(order.id)
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
        """
        Removing an open order.

        Parameters
        ----------
        order: Order

        """
        log.info('removing cancelled order {}'.format(order.id))
        self._remove_open_order(order)

        order_position = self.positions[order.asset] \
            if order.asset in self.positions else None

        if order_position is None:
            raise ValueError(
                'Trying to remove order for a position not held: %s' % order.id
            )

        order_position.amount -= order.amount

        log.debug('removed order from portfolio')
