from catalyst.finance.blotter import Blotter
from catalyst.finance.commission import PerShare
from catalyst.finance.slippage import VolumeShareSlippage
from catalyst.assets._assets import TradingPair


class ExchangeBlotter(Blotter):
    def __init__(self, *args, **kwargs):
        super(ExchangeBlotter, self).__init__(*args, **kwargs)

        # Using the equity models for now
        # We may be able to define more sophisticated models based on the fee
        # structure of each exchange.
        self.slippage_models = {
            TradingPair: VolumeShareSlippage()
        }
        self.commission_models = {
            TradingPair: PerShare()
        }
