import backtrader as bt


class ForexCommission(bt.CommInfoBase):
    params = (
        ('commission', 0.000035),
        ('commtype', bt.CommInfoBase.COMM_FIXED),
        ('stocklike', True),
        ('interest', 0.00003),
        ('interest_long', True),
        ('leverage', 1),
        ('margin', None),
    )

    def __init__(self):
        super(ForexCommission, self).__init__()
        self._creditrate = self.p.interest

    def _get_credit_interest(self, data, size, price, days, dt0, dt1):
        return days * self._creditrate * abs(size)
