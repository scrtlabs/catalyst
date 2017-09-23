from catalyst.errors import ZiplineError


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
        'History frequency {frequency} not supported by the exchange.'
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
    Raised when a symbol() call contains a non-existant symbol.
    """
    msg = ('Symbol {symbol} not found on exchange {exchange}. '
           'Choose from: {supported_symbols}').strip()


class BundleNotFoundError(ZiplineError):
    msg = ('Unable to find bundle data for exchange {exchange}. '
           'Please ingest data using the command '
           '`catalyst ingest -b exchange_{exchange}`. '
           'See catalyst documentation for details.').strip()


class PricingDataBeforeTradingError(ZiplineError):
    msg = ('Pricing data for trading pairs {symbols} on exchange {exchange} '
           'starts on {first_trading_day}.').strip()


class PricingDataNotLoadedError(ZiplineError):
    msg = ('Pricing data {field} for trading pairs {symbols} trading on '
           'exchange {exchange} since {first_trading_day} is unavailable. '
           'The bundle data is either out-of-date or has not been loaded yet.'
           'Please ingest data using the command '
           '`catalyst ingest -b exchange_{exchange}`. '
           'See catalyst documentation for details.').strip()
