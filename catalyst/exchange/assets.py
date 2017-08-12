import pandas as pd
import pytz

assets = list(
    dict(
        symbol='eth-usd',
        exchange='bitfinex',
        first_traded=pd.datetime(2010, 1, 1, 0, 0, 0, 0, pytz.utc)
    )
)
