from catalyst.assets._assets import TradingPair
from logbook import Logger

from catalyst.constants import LOG_LEVEL
from catalyst.finance.blotter import Blotter
from catalyst.finance.commission import CommissionModel
from catalyst.finance.slippage import SlippageModel
from catalyst.finance.transaction import create_transaction

log = Logger('exchange_blotter', level=LOG_LEVEL)

# It seems like we need to accept greater slippage risk in cryptos
# Orders won't often close at Equity levels.
# TODO: should work with set_commission and set_slippage
DEFAULT_SLIPPAGE_SPREAD = 0.0001
DEFAULT_MAKER_FEE = 0.0015
DEFAULT_TAKER_FEE = 0.0025


class TradingPairFeeSchedule(CommissionModel):
    """
    Calculates a commission for a transaction based on a per percentage fee.

    Parameters
    ----------
    fee : float, optional
        The percentage fee.
    """

    def __init__(self,
                 maker_fee=DEFAULT_MAKER_FEE,
                 taker_fee=DEFAULT_TAKER_FEE):
        self.maker_fee = maker_fee
        self.taker_fee = taker_fee

    def __repr__(self):
        return (
            '{class_name}(maker_fee={maker_fee}, '
            'taker_fee={taker_fee})'.format(
                class_name=self.__class__.__name__,
                maker_fee=self.maker_fee,
                taker_fee=self.taker_fee,
            )
        )

    def calculate(self, order, transaction):
        """
        Calculate the final fee based on the order parameters.

        :param order:
        :param transaction:

        :return float:
            The total commission.
        """
        cost = abs(transaction.amount) * transaction.price

        # Assuming just the taker fee for now
        fee = cost * self.taker_fee
        return fee


class TradingPairFixedSlippage(SlippageModel):
    """
    Model slippage as a fixed spread.

    Parameters
    ----------
    spread : float, optional
        spread / 2 will be added to buys and subtracted from sells.
    """

    def __init__(self, spread=DEFAULT_SLIPPAGE_SPREAD):
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
