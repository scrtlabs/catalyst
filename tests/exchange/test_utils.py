from datetime import timedelta
from random import randint

import pandas as pd


def rnd_history_date_days(max_days=30):
    now = pd.Timestamp.utcnow()
    days = randint(0, max_days)

    return now - timedelta(days=days)


def rnd_bar_count(max_bars=21):
    now = pd.Timestamp.utcnow()

    return randint(0, max_bars)
