from catalyst.finance.execution import LimitOrder, StopOrder, StopLimitOrder


class ExchangeLimitOrder(LimitOrder):
    def get_limit_price(self, is_buy):
        """
        We may be trading Satoshis with 8 decimals, we cannot round numbers
        :param is_buy:
        :return:
        """
        return self.limit_price


class ExchangeStopOrder(StopOrder):
    def get_stop_price(self, is_buy):
        """
        We may be trading Satoshis with 8 decimals, we cannot round numbers
        :param is_buy:
        :return:
        """
        return self.stop_price


class ExchangeStopLimitOrder(StopLimitOrder):
    def get_limit_price(self, is_buy):
        """
        We may be trading Satoshis with 8 decimals, we cannot round numbers
        :param is_buy:
        :return:
        """
        return self.limit_price

    def get_stop_price(self, is_buy):
        """
        We may be trading Satoshis with 8 decimals, we cannot round numbers
        :param is_buy:
        :return:
        """
        return self.stop_price
