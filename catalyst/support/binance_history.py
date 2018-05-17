import pandas as pd
from catalyst import run_algorithm


def initialize(context):
    context.i = -1  # counts the minutes
    context.exchange = 'cryptopia'
    context.quote_currency = 'btc'
    context.coins = context.exchanges[context.exchange].assets
    context.coins = [c for c in context.coins if
                     c.quote_currency == context.quote_currency]


def handle_data(context, data):
    # current date formatted into a string
    today = data.current_dt

    # update universe everyday
    new_day = 60 * 24  # assuming data_frequency='minute'
    if not context.i % new_day:
        context.coins = context.exchanges[context.exchange].assets
        context.coins = [c for c in context.coins if
                         c.quote_currency == context.quote_currency]

    # get data every 30 minutes
    minutes = 1
    if not context.i % minutes:
        # we iterate for every pair in the current universe
        for coin in context.coins:
            pair = str(coin.symbol)

            price = data.current(coin, 'price')
            print(today, pair, price)


def analyze(context=None, results=None):
    pass


if __name__ == '__main__':
    start_date = pd.to_datetime('2018-01-17', utc=True)
    end_date = pd.to_datetime('2018-01-18', utc=True)

    performance = run_algorithm(
        capital_base=1.0,
        # amount of quote_currency, not always in dollars unless usd
        initialize=initialize,
        handle_data=handle_data,
        analyze=analyze,
        exchange_name='cryptopia',
        data_frequency='minute',
        quote_currency='btc',
        live=True,
        live_graph=False,
        simulate_orders=True,
        algo_namespace='simple_universe'
    )
