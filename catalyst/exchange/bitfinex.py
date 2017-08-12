import six
import base64
import hashlib
import hmac
import json
import time
import requests
import pandas as pd
# from websocket import create_connection
from catalyst.exchange.exchange import Exchange, RTVolumeBar, Position
from logbook import Logger
from catalyst.finance.order import Order, ORDER_STATUS
from catalyst.finance.execution import (MarketOrder,
                                        LimitOrder,
                                        StopOrder,
                                        StopLimitOrder)

BITFINEX_URL = 'https://api.bitfinex.com'
BITFINEX_KEY = 'hjZ7DZzwbBZsIZPWeSSQtrWCPNwyhxw96r3LnY7jtOH'
BITFINEX_SECRET = b'LilCoxcqUnHKBcGtrttwCIv4qONTdjuFMSdz8Rxh6OM'
ASSETS = '{ "btcusd": {"symbol":"btc_usd", "start_date": "2010-01-01"}, "ltcusd": {"symbol":"ltc-usd", "start_date": "2010-01-01"}, "ltcbtc": {"symbol":"ltc_btc", "start_date": "2010-01-01"}, "ethusd": {"symbol":"eth_usd", "start_date": "2010-01-01"}, "ethbtc": {"symbol":"eth_btc", "start_date": "2010-01-01"}, "etcbtc": {"symbol":"etc_btc", "start_date": "2010-01-01"}, "etcusd": {"symbol":"etc_usd", "start_date": "2010-01-01"}, "rrtusd": {"symbol":"rrt_usd", "start_date": "2010-01-01"}, "rrtbtc": {"symbol":"rrt_btc", "start_date": "2010-01-01"}, "zecusd": {"symbol":"zec_usd", "start_date": "2010-01-01"}, "zecbtc": {"symbol":"zec_btc", "start_date": "2010-01-01"}, "xmrusd": {"symbol":"xmr_usd", "start_date": "2010-01-01"}, "xmrbtc": {"symbol":"xmr_btc", "start_date": "2010-01-01"}, "dshusd": {"symbol":"dsh_usd", "start_date": "2010-01-01"}, "dshbtc": {"symbol":"dsh_btc", "start_date": "2010-01-01"}, "bccbtc": {"symbol":"bcc_btc", "start_date": "2010-01-01"}, "bcubtc": {"symbol":"bcu_btc", "start_date": "2010-01-01"}, "bccusd": {"symbol":"bcc_usd", "start_date": "2010-01-01"}, "bcuusd": {"symbol":"bcu_usd", "start_date": "2010-01-01"}, "xrpusd": {"symbol":"xrp_usd", "start_date": "2010-01-01"}, "xrpbtc": {"symbol":"xrp_btc", "start_date": "2010-01-01"}, "iotusd": {"symbol":"iot_usd", "start_date": "2010-01-01"}, "iotbtc": {"symbol":"iot_btc", "start_date": "2010-01-01"}, "ioteth": {"symbol":"iot_eth", "start_date": "2010-01-01"}, "eosusd": {"symbol":"eos_usd", "start_date": "2010-01-01"}, "eosbtc": {"symbol":"eos_btc", "start_date": "2010-01-01"}, "eoseth": {"symbol":"eos_eth", "start_date": "2010-01-01"} }'

log = Logger('Bitfinex')
warning_logger = Logger('AlgoWarning')


class Bitfinex(Exchange):
    def __init__(self):
        self.url = BITFINEX_URL
        self.key = BITFINEX_KEY
        self.secret = BITFINEX_SECRET
        self.id = 'b'
        self.name = 'bitfinex'
        self.orders = {}
        self.assets = {}
        self.load_assets(ASSETS)

    def request(self, operation, data, version='v1'):
        payload_object = {
            'request': '/{}/{}'.format(version, operation),
            'nonce': '{0:f}'.format(time.time() * 100000),  # convert to string
            'options': {}
        }

        if data is None:
            payload_dict = payload_object
        else:
            payload_dict = payload_object.copy()
            payload_dict.update(data)

        payload_json = json.dumps(payload_dict)
        if six.PY3:
            payload = base64.b64encode(bytes(payload_json, 'utf-8'))
        else:
            payload = base64.b64encode(payload_json)

        m = hmac.new(self.secret, payload, hashlib.sha384)
        m = m.hexdigest()

        # headers
        headers = {
            'X-BFX-APIKEY': self.key,
            'X-BFX-PAYLOAD': payload,
            'X-BFX-SIGNATURE': m
        }

        if data is None:
            request = requests.get(
                self.url + '/{version}/{operation}'.format(
                    version=version,
                    operation=operation
                ), data={},
                headers=headers)
        else:
            request = requests.post(
                self.url + '/{version}/{operation}'.format(
                    version=version,
                    operation=operation
                ),
                headers=headers)

        return request

    def subscribe_to_market_data(self, symbol):
        pass

    def positions(self):
        pass

    def portfolio(self):
        pass

    def account(self):
        pass

    @property
    def time_skew(self):
        # TODO: research the time skew conditions
        return None

    def get_open_orders(self, asset):
        # TODO: map to asset
        response = self.request('orders', None)
        orders = response.json()
        # TODO: what is the right format?
        return orders

    def get_order(self, order_id):
        pass

    def get_spot_value(self, assets, field, dt, data_frequency):
        raise NotImplementedError()

    def balance(self, currencies):
        response = self.request('balances', None)
        positions = response.json()
        if 'message' in positions:
            raise ValueError(
                'unable to fetch balance %s' % positions['message']
            )

        balance = dict()
        for position in positions:
            if position['currency'] in currencies:
                balance[position['currency']] = float(position['available'])
        return balance

    # TODO: why repeating prices if already in style?
    def order(self, asset, amount, limit_price, stop_price, style):
        """
        The type of the order: LIMIT, MARKET, STOP, TRAILING STOP,
         EXCHANGE MARKET, EXCHANGE LIMIT, EXCHANGE STOP,
          EXCHANGE TRAILING STOP, FOK, EXCHANGE FOK.
        """

        is_buy = (amount > 0)

        if isinstance(style, MarketOrder):
            order_type = 'market'
        elif isinstance(style, LimitOrder):
            order_type = 'limit'
            price = limit_price
        elif isinstance(style, StopOrder):
            order_type = 'stop'
            price = stop_price
        elif isinstance(style, StopLimitOrder):
            raise NotImplementedError('Stop/limit orders not available')

        exchange_symbol = self.get_symbol(asset)
        req = dict(
            symbol=exchange_symbol,
            amount=str(float(amount)),
            price=str(float(price)),
            side='buy' if is_buy else 'sell',
            type='exchange ' + order_type,  # TODO: support margin trades
            exchange='bitfinex',
            is_hidden=False,
            is_postonly=False,
            use_all_available=0,
            ocoorder=False,
            buy_price_oco=0,
            sell_price_oco=0
        )

        response = self.request('order/new', req)
        exchange_order = response.json()
        if 'message' in exchange_order:
            raise ValueError(
                'unable to create Bitfinex order %s' % exchange_order[
                    'message']
            )

        order = Order(
            dt=pd.Timestamp.utcnow(),
            asset=asset,
            amount=amount,
            stop=style.get_stop_price(is_buy),
            limit=style.get_limit_price(is_buy),
        )

        order_id = order.broker_order_id = exchange_order['id']
        self.orders[order_id] = order

        return order_id

    def cancel_order(self, order_id):
        response = self.request('order/cancel', {'order_id': order_id})
        status = response.json()
        return status

    def order_status(self, order_id):
        response = self.request('order/status', {'order_id': int(order_id)})
        order_status = response.json()
        if 'message' in order_status:
            raise ValueError(
                'Unable to retrieve order status: %s' % order_status['message']
            )

        result = dict(exchange='b')

        if order_status['is_cancelled']:
            warning_logger.warn(
                'removing cancelled order from the open orders list %s',
                order_status)
            result['status'] = 'canceled'

        elif not order_status['is_live']:
            log.info('found executed order %s', order_status)
            result['status'] = 'closed'
            result['executed_price'] = float(
                order_status['avg_execution_price'])
            result['executed_amount'] = float(order_status['executed_amount'])

        else:
            result['status'] = 'open'

        return result

    def get_v2_symbols(self, assets):
        """
        Workaround to support Bitfinex v2
        TODO: Might require a separate asset dictionary

        :param assets:
        :return:
        """

        v2_symbols = []
        for asset in assets:
            pair = asset.symbol.split('_')
            symbol = 't' + pair[0].upper() + pair[1].upper()
            v2_symbols.append(symbol)
        return v2_symbols

    def tickers(self, date, assets):
        symbols = self.get_v2_symbols(assets)
        log.debug('fetching tickers {}'.format(symbols))

        request = requests.get(
            self.url + '/v2/tickers?symbols={}'.format(','.join(symbols))
        )
        tickers = request.json()
        if 'message' in tickers:
            raise ValueError(
                'Unable to retrieve tickers: %s' % tickers['message']
            )

        formatted_tickers = []
        for index, ticker in enumerate(tickers):
            if not len(ticker) == 11:
                raise ValueError('Invalid ticker: %s' % ticker)

            tick = dict(
                asset=assets[index],
                timestamp=date,
                bid=ticker[1],
                ask=ticker[3],
                last_price=ticker[7],
                low=ticker[10],
                high=ticker[9],
                volume=ticker[8],
            )
            formatted_tickers.append(tick)

        log.debug('got tickers {}'.format(formatted_tickers))
        return formatted_tickers
