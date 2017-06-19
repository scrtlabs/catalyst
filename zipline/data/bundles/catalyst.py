import tarfile

from .quandl import (
    ONE_MEGABYTE,
    download_with_progress,
    download_without_progress,
)

from . import core as bundles

CATALYST_URL = (
    'https://s3.amazonaws.com/quantopian-public-zipline-data/quandl'
)

@bundles.register(
    'catalyst',
    calendar_name='NYSE',
    minutes_per_day=390,
    create_writers=False,
)
def catalyst_bundle(environ,
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
        data = download_with_progress(
            CATALYST_URL,
            chunk_size=ONE_MEGABYTE,
            label="Downloading Bundle: catalyst",
        )
    else:
        data = download_without_progress(CATALYST_URL)

    with tarfile.open('r', fileobj=data) as tar:
        if show_progress:
            print("Writing data to %s." % output_dir)
        tar.extractall(output_dir)
