from abc import ABCMeta, abstractmethod


class BaseExchangeTestCase:
    __metaclass__ = ABCMeta

    # @abstractmethod
    # def test_order(self):
    #     pass
    #
    # @abstractmethod
    # def test_open_orders(self):
    #     pass
    #
    # @abstractmethod
    # def test_get_order(self):
    #     pass
    #
    # @abstractmethod
    # def test_cancel_order(self):
    #     pass
    #
    # @abstractmethod
    # def test_get_candles(self):
    #     pass
    #
    # @abstractmethod
    # def test_tickers(self):
    #     pass
    #
    # @abstractmethod
    # def test_get_balances(self):
    #     pass
    #
    # @abstractmethod
    # def test_get_account(self):
    #     pass

    @abstractmethod
    def test_create_order_timeout_order(self):
        pass

    @abstractmethod
    def test_create_order_timeout_open(self):
        pass

    @abstractmethod
    def test_create_order_timeout_closed(self):
        pass

    @abstractmethod
    def test_create_order_timeout_trade(self):
        pass

    @abstractmethod
    def test_process_order_timeout(self):
        pass
