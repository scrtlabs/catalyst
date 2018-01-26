import sys
import traceback

from catalyst.errors import ZiplineError


def silent_except_hook(exctype, excvalue, exctraceback):
    if exctype in [MarketplacePubAddressEmpty, MarketplaceDatasetNotFound,
                   MarketplaceNoAddressMatch, MarketplaceHTTPRequest,
                   MarketplaceNoCSVFiles]:
        fn = traceback.extract_tb(exctraceback)[-1][0]
        ln = traceback.extract_tb(exctraceback)[-1][1]
        print("Error traceback: {1} (line {2})\n"
              "{0.__name__}:  {3}".format(exctype, fn, ln, excvalue))
    else:
        sys.__excepthook__(exctype, excvalue, exctraceback)


sys.excepthook = silent_except_hook


class MarketplacePubAddressEmpty(ZiplineError):
    msg = (
        'Please enter your public address to use in the Data Marketplace '
        'in the following file: {filename}'
    ).strip()


class MarketplaceDatasetNotFound(ZiplineError):
    msg = (
        'The dataset "{dataset}" is not registered in the Data Marketplace.'
    ).strip()


class MarketplaceNoAddressMatch(ZiplineError):
    msg = (
        'The address registered with the dataset {dataset}: {address} '
        'does not match any of your addresses.'
    ).strip()


class MarketplaceHTTPRequest(ZiplineError):
    msg = (
        'Request to remote server to {request} failed: {error}'
    ).strip()


class MarketplaceNoCSVFiles(ZiplineError):
    msg = (
        'No CSV files found on {datadir} to upload.'
    )
