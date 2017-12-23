from logbook import Logger

from catalyst.constants import LOG_LEVEL
from catalyst.exchange.factory import find_exchanges

import pandas as pd

log = Logger('AssetFinderExchange', level=LOG_LEVEL)


class AssetFinderExchange(object):
    def __init__(self):
        self._asset_cache = {}

    @property
    def sids(self):
        """
        This seems to be used to pre-fetch assets.
        I don't think that we need this for live-trading.
        Leaving the list empty.
        """
        return list()

    def retrieve_all(self, sids, default_none=False):
        """
        Retrieve all assets in `sids`.

        Parameters
        ----------
        sids : iterable of int
            Assets to retrieve.
        default_none : bool
            If True, return None for failed lookups.
            If False, raise `SidsNotFound`.

        Returns
        -------
        assets : list[Asset or None]
            A list of the same length as `sids` containing Assets (or Nones)
            corresponding to the requested sids.

        Raises
        ------
        SidsNotFound
            When a requested sid is not found and default_none=False.
        """
        # for sid in sids:
        #     if sid in self._asset_cache:
        #         log.debug('got asset from cache: {}'.format(sid))
        #     else:
        #         log.debug('fetching asset: {}'.format(sid))
        return list()

    def lookup_symbol(self, symbol, exchange, data_frequency=None,
                      as_of_date=None, fuzzy=False):
        """Lookup an asset by symbol.

        Parameters
        ----------
        symbol : str
            The ticker symbol to resolve.
        as_of_date : datetime or None
            Look up the last owner of this symbol as of this datetime.
            If ``as_of_date`` is None, then this can only resolve the equity
            if exactly one equity has ever owned the ticker.
        fuzzy : bool, optional
            Should fuzzy symbol matching be used? Fuzzy symbol matching
            attempts to resolve differences in representations for
            shareclasses. For example, some people may represent the ``A``
            shareclass of ``BRK`` as ``BRK.A``, where others could write
            ``BRK_A``.

        Returns
        -------
        equity : Asset
            The equity that held ``symbol`` on the given ``as_of_date``, or the
            only equity to hold ``symbol`` if ``as_of_date`` is None.

        Raises
        ------
        SymbolNotFound
            Raised when no equity has ever held the given symbol.
        MultipleSymbolsFound
            Raised when no ``as_of_date`` is given and more than one equity
            has held ``symbol``. This is also raised when ``fuzzy=True`` and
            there are multiple candidates for the given ``symbol`` on the
            ``as_of_date``.
        """
        log.debug('looking up symbol: {} {}'.format(symbol, exchange.name))

        if data_frequency is not None:
            key = ','.join([exchange.name, symbol, data_frequency])

        else:
            key = ','.join([exchange.name, symbol])

        if key in self._asset_cache:
            return self._asset_cache[key]
        else:
            asset = exchange.get_asset(symbol, data_frequency)
            self._asset_cache[key] = asset
            return asset

    def lifetimes(self, dates, include_start_date):
        """
        Compute a DataFrame representing asset lifetimes for the specified date
        range.

        Parameters
        ----------
        dates : pd.DatetimeIndex
            The dates for which to compute lifetimes.
        include_start_date : bool
            Whether or not to count the asset as alive on its start_date.

            This is useful in a backtesting context where `lifetimes` is being
            used to signify "do I have data for this asset as of the morning of
            this date?"  For many financial metrics, (e.g. daily close), data
            isn't available for an asset until the end of the asset's first
            day.

        Returns
        -------
        lifetimes : pd.DataFrame
            A frame of dtype bool with `dates` as index and an Int64Index of
            assets as columns.  The value at `lifetimes.loc[date, asset]` will
            be True iff `asset` existed on `date`.  If `include_start_date` is
            False, then lifetimes.loc[date, asset] will be false when date ==
            asset.start_date.

        See Also
        --------
        numpy.putmask
        catalyst.pipeline.engine.SimplePipelineEngine._compute_root_mask
        """
        exchanges = find_exchanges(features=['minuteBundle'])
        if not exchanges:
            raise ValueError('exchange with minute bundles not found')

        # TODO: find a way to support multiple exchanges
        exchange = exchanges[0]
        # Using a single exchange for now because are not unique for the
        # same asset in different exchanges. I'd like to avoid binding
        # pipeline to a single exchange.
        exchange.init()

        data = []
        for dt in dates:
            exists = []

            for asset in exchange.assets:
                if include_start_date:
                    condition = (asset.start_date <= dt < asset.end_minute)

                else:
                    condition = (asset.start_date < dt < asset.end_minute)

                exists.append(condition)

            data.append(exists)

        sids = [asset.sid for asset in exchange.assets]
        df = pd.DataFrame(data, index=dates, columns=sids)

        return df
