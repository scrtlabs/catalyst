import sys, traceback
from catalyst.errors import ZiplineError


def silent_except_hook(exctype, excvalue, exctraceback):
    if exctype in [PricingDataBeforeTradingError, PricingDataNotLoadedError,
                   SymbolNotFoundOnExchange, ]:
        fn = traceback.extract_tb(exctraceback)[-1][0]
        ln = traceback.extract_tb(exctraceback)[-1][1]
        print "Error traceback: {1} (line {2})\n" \
              "{0.__name__}:  {3}".format(exctype, fn, ln, excvalue)
    else:
        sys.__excepthook__(exctype, excvalue, exctraceback)


sys.excepthook = silent_except_hook


class ExchangeRequestError(ZiplineError):
    msg = (
        'Request failed: {error}'
    ).strip()


class ExchangeRequestErrorTooManyAttempts(ZiplineError):
    msg = (
        'Request failed: {error}, giving up after {attempts} attempts'
    ).strip()


class ExchangeBarDataError(ZiplineError):
    msg = (
        'Unable to retrieve bar data: {data_type}, ' +
        'giving up after {attempts} attempts: {error}'
    ).strip()


class ExchangePortfolioDataError(ZiplineError):
    msg = (
        'Unable to retrieve portfolio data: {data_type}, ' +
        'giving up after {attempts} attempts: {error}'
    ).strip()


class ExchangeTransactionError(ZiplineError):
    msg = (
        'Unable to execute transaction: {transaction_type}, ' +
        'giving up after {attempts} attempts: {error}'
    ).strip()


class ExchangeNotFoundError(ZiplineError):
    msg = (
        'Exchange {exchange_name} not found. Please specify exchanges '
        'supported by Catalyst and verify spelling for accuracy.'
    ).strip()


class ExchangeAuthNotFound(ZiplineError):
    msg = (
        'Please create an auth.json file containing the api token and key for '
        'exchange {exchange}. Place the file here: {filename}'
    ).strip()


class ExchangeSymbolsNotFound(ZiplineError):
    msg = (
        'Unable to download or find a local copy of symbols.json for exchange '
        '{exchange}. The file should be here: {filename}'
    ).strip()


class AlgoPickleNotFound(ZiplineError):
    msg = (
        'Pickle not found for algo {algo} in path {filename}'
    ).strip()


class InvalidHistoryFrequencyError(ZiplineError):
    msg = (
        'Frequency {frequency} not supported by the exchange.'
    ).strip()


class MismatchingFrequencyError(ZiplineError):
    msg = (
        'Bar aggregate frequency {frequency} not compatible with '
        'data frequency {data_frequency}.'
    ).strip()


class InvalidSymbolError(ZiplineError):
    msg = (
        'Invalid trading pair symbol: {symbol}. '
        'Catalyst symbols must follow this convention: '
        '[Market Currency]_[Base Currency]. For example: eth_usd, btc_usd, '
        'neo_eth, ubq_btc. Error details: {error}'
    ).strip()


class InvalidOrderStyle(ZiplineError):
    msg = (
        'Order style {style} not supported by exchange {exchange}.'
    ).strip()


class CreateOrderError(ZiplineError):
    msg = (
        'Unable to create order on exchange {exchange} {error}.'
    ).strip()


class OrderNotFound(ZiplineError):
    msg = (
        'Order {order_id} not found on exchange {exchange}.'
    ).strip()


class OrphanOrderError(ZiplineError):
    msg = (
        'Order {order_id} found in exchange {exchange} but not tracked by '
        'the algorithm.'
    ).strip()


class OrphanOrderReverseError(ZiplineError):
    msg = (
        'Order {order_id} tracked by algorithm, but not found in exchange {exchange}.'
    ).strip()


class OrderCancelError(ZiplineError):
    msg = (
        'Unable to cancel order {order_id} on exchange {exchange} {error}.'
    ).strip()


class SidHashError(ZiplineError):
    msg = (
        'Unable to hash sid from symbol {symbol}.'
    ).strip()


class BaseCurrencyNotFoundError(ZiplineError):
    msg = (
        'Algorithm base currency {base_currency} not found in exchange '
        '{exchange}.'
    ).strip()


class MismatchingBaseCurrencies(ZiplineError):
    msg = (
        'Unable to trade with base currency {base_currency} when the '
        'algorithm uses {algo_currency}.'
    ).strip()


class MismatchingBaseCurrenciesExchanges(ZiplineError):
    msg = (
        'Unable to trade with base currency {base_currency} when the '
        'exchange {exchange_name} users {exchange_currency}.'
    ).strip()


class SymbolNotFoundOnExchange(ZiplineError):
    """
    Raised when a symbol() call contains a non-existent symbol.
    """
    msg = ('Symbol {symbol} not found on exchange {exchange}. '
           'Choose from: {supported_symbols}').strip()


class BundleNotFoundError(ZiplineError):
    msg = ('Unable to find bundle data for exchange {exchange} and '
           'data frequency {data_frequency}.'
           'Please ingest some price data.'
           'See `catalyst ingest-exchange --help` for details.').strip()


class TempBundleNotFoundError(ZiplineError):
    msg = ('Temporary bundle not found in: {path}.').strip()


class EmptyValuesInBundleError(ZiplineError):
    msg = ('{name} with end minute {end_minute} has empty rows '
           'in ranges: {dates}').strip()


class PricingDataBeforeTradingError(ZiplineError):
    msg = ('Pricing data for trading pairs {symbols} on exchange {exchange} '
           'starts on {first_trading_day}, but you are either trying to trade or '
           'retrieve pricing data on {dt}. Adjust your dates accordingly.').strip()


class PricingDataNotLoadedError(ZiplineError):
    msg = ('Pricing data {field} for trading pairs {symbols} trading on '
           'exchange {exchange} since {first_trading_day} is unavailable. '
           'The bundle data is either out-of-date or has not been loaded yet. '
           'Please ingest data using the command '
           '`catalyst ingest-exchange -x {exchange} -i {symbol_list}`. '
           'See catalyst documentation for details.').strip()


class ApiCandlesError(ZiplineError):
    msg = ('Unable to fetch candles from the remote API: {error}.').strip()
