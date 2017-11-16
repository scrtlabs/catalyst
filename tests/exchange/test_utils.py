from datetime import timedelta
from random import randint

import pandas as pd


def rnd_history_date_days(max_days=30, last_dt=None):
    if last_dt is None:
        last_dt = pd.Timestamp.utcnow()

    days = randint(0, max_days)

    return last_dt - timedelta(days=days)


def rnd_history_date_minutes(max_minutes=1440):
    now = pd.Timestamp.utcnow()
    days = randint(0, max_minutes)

    return now - timedelta(minutes=days)


def rnd_bar_count(max_bars=21):
    now = pd.Timestamp.utcnow()

    return randint(0, max_bars)
