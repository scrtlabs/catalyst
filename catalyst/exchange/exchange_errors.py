import sys
import traceback

from catalyst.errors import ZiplineError


def silent_except_hook(exctype, excvalue, exctraceback):
    if exctype in [PricingDataBeforeTradingError, PricingDataNotLoadedError,
                   SymbolNotFoundOnExchange, NoDataAvailableOnExchange,
                   ExchangeAuthEmpty]:
        fn = traceback.extract_tb(exctraceback)[-1][0]
        ln = traceback.extract_tb(exctraceback)[-1][1]
        print("Error traceback: {1} (line {2})\n"
              "{0.__name__}:  {3}".format(exctype, fn, ln, excvalue))
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


class ExchangeAuthEmpty(ZiplineError):
    msg = (
        'Please enter your API token key and secret for exchange {exchange} '
        'in the following file: {filename}'
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


class InvalidHistoryFrequencyAlias(ZiplineError):
    msg = (
        'Invalid frequency alias {freq}. Valid suffixes are M (minute) '
        'and D (day). For example, these aliases would be valid '
        '1M, 5M, 1D.'
    ).strip()


class InvalidHistoryFrequencyError(ZiplineError):
    msg = (
        'Frequency {frequency} not supported by the exchange.'
    ).strip()


class UnsupportedHistoryFrequencyError(ZiplineError):
    msg = (
        '{exchange} does not support candle frequency {freq}, please choose '
        'from: {freqs}.'
    ).strip()


class InvalidHistoryTimeframeError(ZiplineError):
    msg = (
        'CCXT timeframe {timeframe} not supported by the exchange.'
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
        '[Base Currency]_[Quote Currency]. For example: eth_usd, btc_usd, '
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
        'Order {order_id} tracked by algorithm, but not found in exchange '
        '{exchange}.'
    ).strip()


class OrderCancelError(ZiplineError):
    msg = (
        'Unable to cancel order {order_id} on exchange {exchange} {error}.'
    ).strip()


class SidHashError(ZiplineError):
    msg = (
        'Unable to hash sid from symbol {symbol}.'
    ).strip()


class QuoteCurrencyNotFoundError(ZiplineError):
    msg = (
        'Algorithm quote currency {quote_currency} not found in account '
        'balances on {exchange}: {balances}'
    ).strip()


class MismatchingQuoteCurrencies(ZiplineError):
    msg = (
        'Unable to trade with quote currency {quote_currency} when the '
        'algorithm uses {algo_currency}.'
    ).strip()


class MismatchingQuoteCurrenciesExchanges(ZiplineError):
    msg = (
        'Unable to trade with quote currency {quote_currency} when the '
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
           'starts on {first_trading_day}, but you are either trying to trade '
           'or retrieve pricing data on {dt}. Adjust your dates accordingly.'
           ).strip()


class PricingDataNotLoadedError(ZiplineError):
    msg = ('Missing data for {exchange} {symbols} in date range '
           '[{start_dt} - {end_dt}]'
           '\nPlease run: `catalyst ingest-exchange -x {exchange} -f '
           '{data_frequency} -i {symbol_list}`. See catalyst documentation '
           'for details.').strip()


class PricingDataValueError(ZiplineError):
    msg = ('Unable to retrieve pricing data for {exchange} {symbol} '
           '[{start_dt} - {end_dt}]: {error}').strip()


class DataCorruptionError(ZiplineError):
    msg = (
        'Unable to validate data for {exchange} {symbols} in date range '
        '[{start_dt} - {end_dt}]. The data is either corrupted or '
        'unavailable. Please try deleting this bundle:'
        '\n`catalyst clean-exchange -x {exchange}\n'
        'Then, ingest the data again. Please contact the Catalyst team if '
        'the issue persists.'
    ).strip()


class ApiCandlesError(ZiplineError):
    msg = (
        'Unable to fetch candles from the remote API: {error}.'
    ).strip()


class NoDataAvailableOnExchange(ZiplineError):
    msg = (
        'Requested data for trading pair {symbol} is not available on '
        'exchange {exchange} '
        'in `{data_frequency}` frequency at this time. '
        'Check `http://enigma.co/catalyst/status` for market coverage.'
    ).strip()


class NoValueForField(ZiplineError):
    msg = (
        'Value not found for field: {field}.'
    ).strip()


class OrderTypeNotSupported(ZiplineError):
    msg = (
        'Order type `{order_type}` not currency supported by Catalyst. '
        'Please use `limit` or `market` orders only.'
    ).strip()


class NotEnoughCapitalError(ZiplineError):
    msg = (
        'Not enough capital on exchange {exchange} for trading. Each '
        'exchange should contain at least as much {quote_currency} '
        'as the specified `capital_base`. The current balance {balance} is '
        'lower than the `capital_base`: {capital_base}'
    ).strip()


class NotEnoughCashError(ZiplineError):
    msg = (
        'Total {currency} amount on {exchange} is lower than the cash '
        'reserved for this algo: {free} < {cash}. While trades can be made on '
        'the exchange accounts outside of the algo, exchange must have enough '
        'free {currency} to cover the algo cash.'
    ).strip()


class LastCandleTooEarlyError(ZiplineError):
    msg = (
        'The trade date of the last candle {last_traded} is before the '
        'specified end date minus one candle {end_dt}. Please verify how '
        '{exchange} calculates the start date of OHLCV candles.'
    ).strip()


class TickerNotFoundError(ZiplineError):
    msg = (
        'Unable to fetch ticker for {symbol} on {exchange}.'
    ).strip()


class BalanceNotFoundError(ZiplineError):
    msg = (
        '{currency} not found in account balance on {exchange}: {balances}.'
    ).strip()


class BalanceTooLowError(ZiplineError):
    msg = (
        'Balance for {currency} on {exchange} too low: {free} < {amount}. '
        'Positions have likely been sold outside of this algorithm. Please '
        'add positions to hold a free amount greater than {amount}, or clean '
        'the state of this algo and restart.'
    ).strip()


class NoCandlesReceivedFromExchange(ZiplineError):
    msg = (
        'Although requesting {bar_count} candles until {end_dt} of asset {asset}, '
        'an empty list of candles was received for {exchange}.'
    ).strip()
