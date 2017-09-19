from datetime import timedelta

import pandas as pd
from logbook import Logger

from catalyst.data.minute_bars import BcolzMinuteOverlappingData
from catalyst.exchange.bitfinex.bitfinex import Bitfinex
from catalyst.exchange.bittrex.bittrex import Bittrex
from catalyst.exchange.exchange_errors import ExchangeNotFoundError
from catalyst.exchange.exchange_utils import get_exchange_auth
from catalyst.utils.cli import maybe_show_progress


def _cachpath(symbol, type_):
    return '-'.join([symbol, type_])


log = Logger('exchange_bundle')


def fetch_candles_chunk(exchange, assets, data_frequency, end_dt, bar_count):
    candles = exchange.get_candles(
        data_frequency=data_frequency,
        assets=assets,
        bar_count=bar_count,
        end_dt=end_dt
    )

    series = dict()

    for asset in assets:
        asset_candles = candles[asset]

        asset_df = pd.DataFrame(asset_candles)
        asset_df.set_index('last_traded', inplace=True, drop=True)
        asset_df.sort_index(inplace=True)

        series[asset] = asset_df

    return series


def exchange_bundle(exchange_name, symbols, start=None, end=None):
    """Create a data bundle ingest function for the specified exchange.

    Parameters
    ----------
    exchange_name: str
        The name of the exchange
    symbols : iterable[str]
        The ticker symbols to load data for.
    start : datetime, optional
        The start date to query for. By default this pulls the full history
        for the calendar.
    end : datetime, optional
        The end date to query for. By default this pulls the full history
        for the calendar.

    Returns
    -------
    ingest : callable
        The bundle ingest function for the given set of symbols.

    Examples
    --------
    This code should be added to ~/.catalyst/extension.py

    .. code-block:: python

       from catalyst.data.bundles import register

       symbols = (
           'eth_btc',
           'etc_btc',
           'neo_btc',
       )
       register('bitfinex_bundle', exchange_bundle('bitfinex', symbols))

    Notes
    -----
    The sids for each symbol will be the index into the symbols sequence.
    """
    # strict this in memory so that we can reiterate over it
    symbols = tuple(symbols)

    def ingest(environ,
               asset_db_writer,
               minute_bar_writer,  # unused
               daily_bar_writer,
               adjustment_writer,
               calendar,
               start_session,
               end_session,
               cache,
               show_progress,
               output_dir,
               # pass these as defaults to make them 'nonlocal' in py2
               start=start,
               end=end):

        # TODO: I don't understand this session vs dates idea
        if start is None:
            start = start_session
        if end is None:
            end = None

        log.info('ingesting data from {} to {}'.format(start, end))

        exchange_auth = get_exchange_auth(exchange_name)
        if exchange_name == 'bitfinex':
            exchange = Bitfinex(
                key=exchange_auth['key'],
                secret=exchange_auth['secret'],
                base_currency=None,  # TODO: make optional at the exchange
                portfolio=None
            )
        elif exchange_name == 'bittrex':
            exchange = Bittrex(
                key=exchange_auth['key'],
                secret=exchange_auth['secret'],
                base_currency=None,
                portfolio=None
            )
        else:
            raise ExchangeNotFoundError(exchange_name=exchange_name)

        assets = exchange.get_assets(symbols)

        delta = end - start
        delta_minutes = delta.total_seconds() / 60
        if delta_minutes > exchange.num_candles_limit:
            bar_count = exchange.num_candles_limit

            chunks = []
            last_chunk_date = end
            while last_chunk_date > start + timedelta(minutes=bar_count):
                # TODO: account for the partial last bar
                chunk = dict(end=last_chunk_date, bar_count=bar_count)
                chunks.append(chunk)

                last_chunk_date = \
                    last_chunk_date - timedelta(minutes=(bar_count + 1))

            chunks.reverse()

        else:
            chunks = [dict(end=end, bar_count=delta_minutes)]

        with maybe_show_progress(
                chunks,
                show_progress,
                label='Fetching {} candles: '.format(exchange_name)) as it:

            for chunk in it:
                asset_df = fetch_candles_chunk(
                    exchange=exchange,
                    assets=assets,
                    data_frequency='1m',
                    end_dt=chunk['end'],
                    bar_count=chunk['bar_count']
                )

                data = []
                for asset in asset_df:
                    df = asset_df[asset]
                    sid = asset.sid
                    data.append((sid, df))

                try:
                    log.debug(
                        'writing chunk: {sid} start: {start} end: {end}'.format(
                            sid=sid,
                            start=chunk['end'] - timedelta(
                                minutes=chunk['bar_count']),
                            end=chunk['end']
                        )
                    )
                    minute_bar_writer.write(data, show_progress=show_progress)
                except KeyError:
                    minute_bar_writer.write(data, show_progress=show_progress)
                except BcolzMinuteOverlappingData as e:
                    log.warn('Unable to write chunk {}: {}'.format(chunk, e))

    return ingest
