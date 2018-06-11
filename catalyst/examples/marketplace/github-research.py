import pandas as pd
import matplotlib.pyplot as plt

from catalyst import run_algorithm
from catalyst.api import symbol, get_dataset

START = '2017-01-01'
END = '2017-12-31'


def initialize(context):
    pass


def handle_data(context, data):
    context.github = get_dataset('github')
    context.github.sort_index(level=0, inplace=True)

    context.zec = data.history(symbol('zec_usdt'),
                               ['price', ],
                               bar_count=365,
                               frequency="1d")
    context.xmr = data.history(symbol('xmr_usdt'),
                               ['price', ],
                               bar_count=365,
                               frequency="1d")


def analyze(context=None, results=None):
    ax1 = plt.subplot(211)
    idx = pd.IndexSlice
    df = context.github.loc[START:END].loc[
            idx[:, [b'ZEC']], ['commits']].reset_index(
                level='symbol', drop=True)
    df.plot(ax=ax1, color='blue')
    ax1.legend(loc=2)
    ax1.set_title('Zcash')
    ax2 = ax1.twinx()
    context.zec['price'].loc[START:END].plot(ax=ax2, color='green')
    ax2.legend(loc=1)

    ax3 = plt.subplot(212)
    idx = pd.IndexSlice
    df = context.github.loc[START:END].loc[
            idx[:, [b'XMR']], ['commits']].reset_index(
                level='symbol', drop=True)
    df.plot(ax=ax3, color='blue')
    ax3.legend(loc=2)
    ax3.set_title('Monero')
    ax4 = ax3.twinx()
    context.xmr['price'].loc[START:END].plot(ax=ax4, color='green')
    ax4.legend(loc=1)

    plt.show()


if __name__ == '__main__':
    run_algorithm(
            capital_base=1000,
            data_frequency='daily',
            initialize=initialize,
            handle_data=handle_data,
            analyze=analyze,
            exchange_name='poloniex',
            algo_namespace='algo-github',
            quote_currency='usdt',
            live=False,
            start=pd.to_datetime(END, utc=True),
            end=pd.to_datetime(END, utc=True),
        )
