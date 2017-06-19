
from catalyst.utils.numpy_utils import float64_dtype

from .dataset import Column, DataSet


class CryptoPricing(DataSet):
    """
    Dataset representing daily trading prices and volumes of crypto-assets.
    """
    open = Column(float64_dtype)
    high = Column(float64_dtype)
    low = Column(float64_dtype)
    close = Column(float64_dtype)
    volume = Column(float64_dtype)
