import abc
from collections import namedtuple
from abc import ABCMeta, abstractmethod, abstractproperty
import json
import pandas as pd
from catalyst.assets._assets import Asset

RTVolumeBar = namedtuple('RTVolumeBar', ['last_trade_price',
                                         'last_trade_size',
                                         'last_trade_time',
                                         'total_volume',
                                         'vwap',
                                         'single_trade_flag'])

Position = namedtuple('Position', ['contract', 'position', 'market_price',
                                   'market_value', 'average_cost',
                                   'unrealized_pnl', 'realized_pnl',
                                   'account_name'])


class Exchange:
    __metaclass__ = ABCMeta

    def __init__(self):
        self.name = None
        self.trading_pairs = None
        self.assets = {}

    def get_trading_pairs(self, pairs):
        return [pair for pair in pairs if pair in self.trading_pairs]

    def get_symbol(self, asset):
        symbol = None

        for key in self.assets:
            if not symbol and self.assets[key].symbol == asset.symbol:
                symbol = key

        if not symbol:
            raise ValueError('Currency %s not supported by exchange %s' %
                             (asset['symbol'], self.name))

        return symbol

    def get_symbols(self, assets):
        symbols = []
        for asset in assets:
            symbols.append(self.get_symbol(asset))
        return symbols

    @staticmethod
    def asset_parser(asset):
        for key in asset:
            if key == 'start_date':
                asset[key] = pd.to_datetime(asset[key], utc=True)
        return asset

    def load_assets(self, assets_json):
        assets = json.loads(
            assets_json,
            object_hook=Exchange.asset_parser
        )

        for exchange_symbol in assets:
            asset_obj = Asset(
                sid=0,
                exchange=self.name,
                **assets[exchange_symbol]
            )
            self.assets[exchange_symbol] = asset_obj

    @abstractmethod
    def subscribe_to_market_data(self, symbol):
        pass

    @abstractproperty
    def positions(self):
        pass

    @abstractproperty
    def portfolio(self):
        pass

    @abstractproperty
    def account(self):
        pass

    @abstractproperty
    def time_skew(self):
        pass

    @abstractmethod
    def order(self, asset, amount, limit_price, stop_price, style):
        pass

    @abstractmethod
    def get_open_orders(self, asset):
        pass

    @abstractmethod
    def get_order(self, order_id):
        pass

    @abstractmethod
    def cancel_order(self, order_param):
        pass

    @abstractmethod
    def get_spot_value(self, assets, field, dt, data_frequency):
        pass

    @abc.abstractmethod
    def tickers(self, date, pairs):
        return

        # @abc.abstractmethod
        # def new_order(self, symbol, side, order_type, price, amount, leverage):
        #     return
        #
        # @abc.abstractmethod
        # def cancel_order(self, order_id):
        #     return
        #
        # @abc.abstractmethod
        # def order_status(self, order_id):
        #     return
        #
        # @abc.abstractmethod
        # def balance(self, currencies):
        #     return
        #
