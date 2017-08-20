from catalyst.errors import ZiplineError


class ExchangeRequestError(ZiplineError):
    msg = (
        'Request failed: {error}'
    ).strip()


class ExchangeRequestErrorTooManyAttempts(ZiplineError):
    msg = (
        'Request failed: {error}, giving up after {attempts} attempts'
    ).strip()


class InvalidHistoryFrequencyError(ZiplineError):
    msg = (
        'History frequency {frequency} not supported by the exchange.'
    ).strip()
