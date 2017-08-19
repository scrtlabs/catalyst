from catalyst.errors import ZiplineError


class ExchangeRequestError(ZiplineError):
    msg = (
        'Request failed: {error}'
    ).strip()


class InvalidHistoryFrequencyError(ZiplineError):
    msg = (
        'History frequency {frequency} not supported by the exchange.'
    ).strip()
