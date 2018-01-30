# -*- coding: utf-8 -*-

import os
import logbook

''' You can override the LOG level from your environment.
    For example, if you want to see the DEBUG messages, run:
    $ export CATALYST_LOG_LEVEL=10
'''
LOG_LEVEL = int(os.environ.get('CATALYST_LOG_LEVEL', logbook.INFO))

SYMBOLS_URL = 'https://s3.amazonaws.com/enigmaco/catalyst-exchanges/' \
              '{exchange}/symbols.json'

DATE_TIME_FORMAT = '%Y-%m-%d %H:%M'
DATE_FORMAT = '%Y-%m-%d'

try:
    ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
except Exception as e:
    print('unable to get catalyst path: {}'.format(e))

AUTO_INGEST = False

AUTH_SERVER = 'https://data.enigma.co'
