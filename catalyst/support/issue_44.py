import pandas as pd
from catalyst import run_algorithm
from catalyst.exchange.exchange_utils import get_exchange_symbols

from catalyst.api import (
    symbols,
)


def initialize(context):
    context.i = -1
    context.base_currency = 'btc'


def handle_data(context, data):
    lookback = 60 * 24 * 7  # (minutes, hours, days)
    context.i += 1
    if context.i < lookback:
        return

    today = context.blotter.current_dt.strftime('%Y-%m-%d %H:%M:%S')

    try:
        # update universe everyday
        new_day = 60 * 24
        if not context.i % new_day:
            context.universe = universe(context, today)

        # get data every 30 minutes
        minutes = 30
        if not context.i % minutes and context.universe:
            for coin in context.coins:
                pair = str(coin.symbol)

                # ohlcv data
                open = data.history(coin, 'open', lookback,
                                    '1m').ffill().bfill().resample(
                    '30T').first()
                high = data.history(coin, 'high', lookback,
                                    '1m').ffill().bfill().resample('30T').max()
                low = data.history(coin, 'low', lookback,
                                   '1m').ffill().bfill().resample('30T').min()
                close = data.history(coin, 'price', lookback,
                                     '1m').ffill().bfill().resample(
                    '30T').last()
                volume = data.history(coin, 'volume', lookback,
                                      '1m').ffill().bfill().resample(
                    '30T').sum()

                print(today, pair, close[-1])

    except Exception as e:
        print(e)


def analyze(context=None, results=None):
    pass


def universe(context, today):
    json_symbols = get_exchange_symbols('poloniex')
    poloniex_universe_df = pd.DataFrame.from_dict(
        json_symbols).transpose().astype(str)
    poloniex_universe_df['base_currency'] = poloniex_universe_df.apply(
        lambda row: row.symbol.split('_')[1],
        axis=1)
    poloniex_universe_df['market_currency'] = poloniex_universe_df.apply(
        lambda row: row.symbol.split('_')[0],
        axis=1)
    poloniex_universe_df = poloniex_universe_df[
        poloniex_universe_df['base_currency'] == context.base_currency]
    poloniex_universe_df = poloniex_universe_df[
        poloniex_universe_df.symbol != 'gas_btc']

    # Markets currently not working on Catalyst 0.3.1
    # 2017-01-01
    # poloniex_universe_df = poloniex_universe_df[poloniex_universe_df.symbol != 'bcn_btc']
    # poloniex_universe_df = poloniex_universe_df[poloniex_universe_df.symbol != 'burst_btc']
    # poloniex_universe_df = poloniex_universe_df[poloniex_universe_df.symbol != 'dgb_btc']
    # poloniex_universe_df = poloniex_universe_df[poloniex_universe_df.symbol != 'doge_btc']
    # poloniex_universe_df = poloniex_universe_df[poloniex_universe_df.symbol != 'emc2_btc']
    # poloniex_universe_df = poloniex_universe_df[poloniex_universe_df.symbol != 'pink_btc']
    # poloniex_universe_df = poloniex_universe_df[poloniex_universe_df.symbol != 'sc_btc']
    print(poloniex_universe_df.head())

    date = str(today).split(' ')[0]

    poloniex_universe_df = poloniex_universe_df[
        poloniex_universe_df.start_date < date]
    context.coins = symbols(*poloniex_universe_df.symbol)
    print(len(poloniex_universe_df))
    return poloniex_universe_df.symbol.tolist()


if __name__ == '__main__':
    start_date = pd.to_datetime('2017-01-01', utc=True)
    end_date = pd.to_datetime('2017-10-15', utc=True)

    performance = run_algorithm(start=start_date, end=end_date,
                                capital_base=10000.0,
                                initialize=initialize,
                                handle_data=handle_data,
                                analyze=analyze,
                                exchange_name='poloniex',
                                data_frequency='minute',
                                base_currency='btc',
                                live=False,
                                live_graph=False,
                                algo_namespace='test')
