import json
import re
from json import JSONEncoder

import pandas as pd
from catalyst.constants import DATE_TIME_FORMAT
from six import string_types


class ExchangeJSONEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, pd.Timestamp):
            return obj.strftime(DATE_TIME_FORMAT)

        # Let the base class default method raise the TypeError
        return JSONEncoder.default(self, obj)


class ExchangeJSONDecoder(json.JSONDecoder):
    def __init__(self, *args, **kwargs):
        json.JSONDecoder.__init__(
            self, object_hook=self.object_hook, *args, **kwargs
        )

    def recursive_iter(self, obj):
        if isinstance(obj, dict):
            for key, value in obj.items():
                match = isinstance(value, string_types) and re.search(
                    r'(\d{4}-\d{2}-\d{2}).*', value
                )
                if match:
                    try:
                        obj[key] = pd.to_datetime(value, utc=True)
                    except ValueError:
                        pass

        elif any(isinstance(obj, t) for t in (list, tuple)):
            for item in obj:
                self.recursive_iter(item)

    def object_hook(self, obj):
        self.recursive_iter(obj)
        return obj


def portfolio_to_dict(portfolio):
    positions = []
    for asset in portfolio.positions:
        p = portfolio.positions[asset]  # Type: Position

        position = dict(
            symbol=asset.symbol,
            exchange=asset.exchange,
            amount=p.amount,
            cost_basis=p.cost_basis,
            last_sale_price=p.last_sale_price,
            last_sale_date=p.last_sale_date,
        )
        positions.append(position)

    portfolio_dict = vars(portfolio)
    portfolio_dict['positions'] = positions

    return portfolio_dict


def portfolio_from_dict(self, portfolio_data):
    from catalyst.protocol import Portfolio
    return Portfolio()
