from io import BytesIO
import tarfile

from . import core as bundles

POLONIEX_BUNDLE_URL = (
    'https://www.dropbox.com/s/9naqffawnq8o4r2/poloniex-bundle.tar?dl=1'
)

@bundles.register(
    'poloniex',
    create_writers=False,
    calendar_name='OPEN',
    minutes_per_day=1440)
def quantopian_quandl_bundle(environ,
                             asset_db_writer,
                             minute_bar_writer,
                             daily_bar_writer,
                             adjustment_writer,
                             calendar,
                             start_session,
                             end_session,
                             cache,
                             show_progress,
                             output_dir):
    if show_progress:
        data = bundles.download_with_progress(
            POLONIEX_BUNDLE_URL,
            chunk_size=bundles.ONE_MEGABYTE,
            label="Downloading Bundle: poloniex",
        )
    else:
        data = bundles.download_without_progress(POLONIEX_BUNDLE_URL)

    with tarfile.open('r', fileobj=data) as tar:
        if show_progress:
            print("Writing data to %s." % output_dir)
        tar.extractall(output_dir)
