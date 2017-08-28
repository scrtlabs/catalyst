import unittest
from abc import ABCMeta, abstractmethod


class BaseExchangeTestCase():
    __metaclass__ = ABCMeta

    @abstractmethod
    def test_order(self):
        pass

    @abstractmethod
    def test_open_orders(self):
        pass

    @abstractmethod
    def test_get_order(self):
        pass

    @abstractmethod
    def test_cancel_order(self):
        pass

    @abstractmethod
    def test_get_candles(self):
        pass

    @abstractmethod
    def test_tickers(self):
        pass

    @abstractmethod
    def get_account(self):
        pass
