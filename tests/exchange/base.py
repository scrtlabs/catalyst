import unittest
import abc
from abc import ABCMeta


class BaseExchangeTestCase():
    __metaclass__ = ABCMeta

    @abc.abstractmethod
    def test_order(self):
        pass

    @abc.abstractmethod
    def test_cancel_order(self):
        pass

    @abc.abstractmethod
    def test_order_status(self):
        pass

    @abc.abstractmethod
    def test_balance(self):
        pass

    @abc.abstractmethod
    def test_ticker(self):
        pass
