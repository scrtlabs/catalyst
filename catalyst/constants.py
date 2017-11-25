# -*- coding: utf-8 -*-

import logbook

LOG_LEVEL = logbook.INFO

SYMBOLS_URL = 'https://s3.amazonaws.com/enigmaco/catalyst-exchanges/' \
              '{exchange}/symbols.json'

DATE_TIME_FORMAT = '%Y-%m-%d %H:%M'
DATE_FORMAT = '%Y-%m-%d'

AUTO_INGEST = False
