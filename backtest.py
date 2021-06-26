import sys
import os
import django
# Connect to existing Django Datebase
sys.path.append('/home/paullam/fyp/fyp/')
os.environ['DJANGO_SETTINGS_MODULE'] = 'fyp.settings'
django.setup()

from candlesticks.models import Candlestick
from datetime import datetime, timedelta, timezone
import pandas_datareader as dr

from backtesting import Backtest, Strategy
from backtesting.lib import crossover

from backtesting.test import SMA, GOOG

def load_my_data(symbol: str = 'EURUSD', ):

    pass

class SmaCross(Strategy):
    n1 = 10
    n2 = 20

    def init(self):
        close = self.data.Close
        self.sma1 = self.I(SMA, close, self.n1)
        self.sma2 = self.I(SMA, close, self.n2)

    def next(self):
        if crossover(self.sma1, self.sma2):
            self.buy()
        elif crossover(self.sma2, self.sma1):
            self.sell()



bt = Backtest(GOOG, SmaCross,
              cash=10000, commission=.002,
              exclusive_orders=True)

output = bt.run()
bt.plot()
