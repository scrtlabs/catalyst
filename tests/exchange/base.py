import unittest
from abc import ABCMeta, abstractmethod


class BaseExchangeTestCase():
    __metaclass__ = ABCMeta

    @abstractmethod
    def test_positions(self):
        pass

    @abstractmethod
    def test_portfolio(self):
        pass

    @abstractmethod
    def test_account(self):
        pass

    @abstractmethod
    def test_time_skew(self):
        pass

    @abstractmethod
    def test_get_open_orders(self):
        pass

    @abstractmethod
    def test_order(self):
        pass

    @abstractmethod
    def test_get_order(self):
        pass

    @abstractmethod
    def test_cancel_order(self):
        pass

    @abstractmethod
    def test_spot_value(self):
        pass

    @abstractmethod
    def test_tickers(self):
        pass
