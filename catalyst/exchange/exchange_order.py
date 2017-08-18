import math

import catalyst.protocol as zp
from catalyst.assets import Asset
from catalyst.finance.order import Order
from catalyst.utils.enum import enum
from catalyst.utils.input_validation import expect_types

ORDER_STATUS = enum(
    'OPEN',
    'FILLED',
    'CANCELLED',
    'REJECTED',
    'HELD',
)

SELL = 1 << 0
BUY = 1 << 1
STOP = 1 << 2
LIMIT = 1 << 3

ORDER_FIELDS_TO_IGNORE = {'type', 'direction', '_status', 'asset'}


class ExchangeOrder(Order):
    @expect_types(asset=Asset)
    def __init__(self, dt, asset, amount, stop=None, limit=None, filled=0,
                 commission=0, id=None, executed_price=None):
        """
        @dt - datetime.datetime that the order was placed
        @asset - asset for the order.
        @amount - the number of shares to buy/sell
                  a positive sign indicates a buy
                  a negative sign indicates a sell
        @filled - how many shares of the order have been filled so far
        """

        # get a string representation of the uuid.
        self.id = self.make_id() if id is None else id
        self.dt = dt
        self.reason = None
        self.created = dt
        self.asset = asset
        self.amount = amount
        self.filled = filled
        self.commission = commission
        self._status = ORDER_STATUS.OPEN
        self.stop = stop
        self.limit = limit
        self.stop_reached = False
        self.limit_reached = False
        self.direction = math.copysign(1, self.amount)
        self.type = zp.DATASOURCE_TYPE.ORDER
        self.broker_order_id = None
        self.executed_price = executed_price
