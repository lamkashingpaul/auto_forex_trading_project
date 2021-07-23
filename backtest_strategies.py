#!/home/paullam/fyp/fypenv/bin/python3
from backtrader.indicators import percentchange
from backtrader_plotting import Bokeh
from backtrader_plotting.schemes import Tradimo
import argparse
import backtrader as bt
import datetime
import os
import sys


class DukascopyCSVData(bt.feeds.GenericCSVData):

    params = (
        ('nullvalue', 0.0),
        ('dtformat', ('%d.%m.%Y %H:%M:%S.%f')),
        ('tmformat', '%H:%M:%S.%f'),
        ('timeframe', bt.TimeFrame.Days),

        ('datetime', 0),
        ('time', -1),
        ('open', 1),
        ('high', 2),
        ('low', 3),
        ('close', 4),
        ('volume', 5),
        ('openinterest', -1),
    )


class QuickstartStrategy(bt.Strategy):

    params = (
        ('maperiod', 15),
        ('printlog', False),
    )

    def log(self, txt, dt=None, doprint=False):
        ''' Logging function fot this strategy'''
        if self.params.printlog or doprint:
            dt = dt or self.datas[0].datetime.date(0)
            print('%s, %s' % (dt.isoformat(), txt))

    def __init__(self):
        # Keep a reference to the "close" line in the data[0] dataseries
        self.dataclose = self.datas[0].close

        # To keep track of pending orders and buy price/commission
        self.order = None
        self.buyprice = None
        self.buycomm = None

        # Add a MovingAverageSimple indicator
        self.sma = bt.indicators.SimpleMovingAverage(
            self.datas[0], period=self.params.maperiod)

    def notify_order(self, order):
        if order.status in [order.Submitted, order.Accepted]:
            # Buy/Sell order submitted/accepted to/by broker - Nothing to do
            return

        # Check if an order has been completed
        # Attention: broker could reject order if not enough cash
        if order.status in [order.Completed]:
            if order.isbuy():
                self.log(
                    'BUY EXECUTED, Price: %.2f, Cost: %.2f, Comm %.2f' %
                    (order.executed.price,
                     order.executed.value,
                     order.executed.comm))

                self.buyprice = order.executed.price
                self.buycomm = order.executed.comm
            else:  # Sell
                self.log('SELL EXECUTED, Price: %.2f, Cost: %.2f, Comm %.2f' %
                         (order.executed.price,
                          order.executed.value,
                          order.executed.comm))

            self.bar_executed = len(self)

        elif order.status in [order.Canceled, order.Margin, order.Rejected]:
            self.log('Order Canceled/Margin/Rejected')

        # Write down: no pending order
        self.order = None

    def notify_trade(self, trade):
        if not trade.isclosed:
            return

        self.log('OPERATION PROFIT, GROSS %.2f, NET %.2f' %
                 (trade.pnl, trade.pnlcomm))

    def next(self):
        # Simply log the closing price of the series from the reference
        self.log('Close, %.2f' % self.dataclose[0])

        # Check if an order is pending ... if yes, we cannot send a 2nd one
        if self.order:
            return

        # Check if we are in the market
        if not self.position:

            # Not yet ... we MIGHT BUY if ...
            if self.dataclose[0] > self.sma[0]:

                # BUY, BUY, BUY!!! (with all possible default parameters)
                self.log('BUY CREATE, %.2f' % self.dataclose[0])

                # Keep track of the created order to avoid a 2nd order
                self.order = self.buy()

        else:

            if self.dataclose[0] < self.sma[0]:
                # SELL, SELL, SELL!!! (with all possible default parameters)
                self.log('SELL CREATE, %.2f' % self.dataclose[0])

                # Keep track of the created order to avoid a 2nd order
                self.order = self.sell()

    def stop(self):
        self.log('(MA Period %2d) Ending Value %.2f' % (self.params.maperiod, self.broker.getvalue()), doprint=True)


class BuyAndHold(bt.Strategy):

    params = (
        ('one_lot_size', 100000),
    )

    def log(self, txt, dt=None, doprint=True):
        ''' Logging function fot this strategy'''
        if self.params.printlog or doprint:
            dt = dt or self.datas[0].datetime.date(0)
            print('%s, %s' % (dt.isoformat(), txt))

    def start(self):
        self.val_start = self.broker.get_cash()  # keep the starting cash

    def nextstart(self):
        # Buy all the available cash
        lots = int(self.broker.get_cash() / self.data / self.p.one_lot_size)
        self.buy(size=lots * self.p.one_lot_size)

    def stop(self):
        # calculate the actual returns
        self.roi = (self.broker.get_value() / self.val_start) - 1.0
        print(f'B&H ROI: {100.0 * self.roi:.2f}%')


class MovingAveragesCrossover(bt.Strategy):

    params = (
        ('one_lot_size', 100000),
        ('fast_ma_period', 50),
        ('slow_ma_period', 200)
    )

    def log(self, txt, dt=None, doprint=True):
        ''' Logging function fot this strategy'''
        if self.params.printlog or doprint:
            dt = dt or self.datas[0].datetime.date(0)
            print('%s, %s' % (dt.isoformat(), txt))

    def __init__(self):
        fast_sma = bt.ind.SMA(period=self.p.fast_ma_period)  # fast moving average
        slow_sma = bt.ind.SMA(period=self.p.slow_ma_period)  # slow moving average
        self.crossover = bt.ind.CrossOver(fast_sma, slow_sma)  # crossover signal

    def start(self):
        self.val_start = self.broker.get_cash()  # keep the starting cash

    def next(self):

        if not self.position:  # not in the market
            if self.crossover > 0:  # if fast crosses slow to the upside
                lots = int(self.broker.get_cash() / self.data / self.p.one_lot_size)
                self.buy(size=lots * self.p.one_lot_size)  # enter long

        elif self.crossover < 0:  # in the market & cross to the downside
            self.close()  # close long position

    def stop(self):
        # calculate the actual returns
        self.roi = (self.broker.get_value() / self.val_start) - 1.0
        print(f'MAs({self.p.fast_ma_period},{self.p.slow_ma_period}) ROI: {100.0 * self.roi:.2f}%')


class RSI(bt.Strategy):

    params = (
        ('one_lot_size', 100000),
        ('period', 14),
        ('upperband', 70.0),
        ('lowerband', 30.0)
    )

    def log(self, txt, dt=None, doprint=True):
        ''' Logging function fot this strategy'''
        if self.params.printlog or doprint:
            dt = dt or self.datas[0].datetime.date(0)
            print('%s, %s' % (dt.isoformat(), txt))

    def start(self):
        self.val_start = self.broker.get_cash()  # keep the starting cash

    def __init__(self):
        self.rsi = bt.ind.RSI(period=self.p.period, upperband=self.p.upperband, lowerband=self.p.lowerband)

    def next(self):

        if not self.position:  # not in the market
            if self.rsi < self.rsi.p.lowerband:  # if fast crosses slow to the upside
                lots = int(self.broker.get_cash() / self.data / self.p.one_lot_size)
                self.buy(size=lots * self.p.one_lot_size)  # enter long

        elif self.rsi > self.rsi.p.upperband:  # in the market & cross to the downside
            self.close()  # close long position

    def stop(self):
        # calculate the actual returns
        self.roi = (self.broker.get_value() / self.val_start) - 1.0
        print(f'RSI({self.p.period},{self.p.upperband},{self.p.lowerband}) ROI: {100.0 * self.roi:.2f}%')


class MACD(bt.Strategy):
    params = (
        ('one_lot_size', 100000),
        ('period_me1', 12),
        ('period_me2', 26),
        ('period_signal', 9),
    )

    def log(self, txt, dt=None, doprint=True):
        ''' Logging function fot this strategy'''
        if self.params.printlog or doprint:
            dt = dt or self.datas[0].datetime.date(0)
            print('%s, %s' % (dt.isoformat(), txt))

    def start(self):
        self.val_start = self.broker.get_cash()  # keep the starting cash

    def __init__(self):
        macd = bt.ind.MACD(period_me1=self.p.period_me1, period_me2=self.p.period_me2, period_signal=self.p.period_signal)
        self.crossover = bt.ind.CrossOver(macd.macd, macd.signal)

    def next(self):

        if not self.position:  # not in the market
            if self.crossover > 0:  # if fast crosses slow to the upside
                lots = int(self.broker.get_cash() / self.data / self.p.one_lot_size)
                self.buy(size=lots * self.p.one_lot_size)  # enter long

        elif self.crossover < 0:  # in the market & cross to the downside
            self.close()  # close long position

    def stop(self):
        # calculate the actual returns
        self.roi = (self.broker.get_value() / self.val_start) - 1.0
        print(f'MACD({self.p.period_me1},{self.p.period_me2},{self.p.period_signal}) ROI: {100.0 * self.roi: .2f} %')


class Stochastic(bt.Strategy):
    params = (
        ('one_lot_size', 100000),
        ('period', 14),
        ('period_dfast', 3),
        ('period_dslow', 3),
        ('upperband', 80.0),
        ('lowerband', 20.0),
    )

    def log(self, txt, dt=None, doprint=True):
        ''' Logging function fot this strategy'''
        if self.params.printlog or doprint:
            dt = dt or self.datas[0].datetime.date(0)
            print('%s, %s' % (dt.isoformat(), txt))

    def __init__(self):
        sto = bt.ind.Stochastic(period=self.p.period,
                                period_dfast=self.p.period_dfast,
                                period_dslow=self.p.period_dslow,
                                upperband=self.p.upperband,
                                lowerband=self.p.lowerband,)

        crossover = bt.ind.CrossOver(sto.percK, sto.percD)

        self.buy_signal = bt.And(crossover > 0, sto.percK < sto.p.lowerband, sto.percD < sto.p.lowerband)
        self.sell_signal = bt.And(crossover < 0, sto.percK > sto.p.upperband, sto.percD > sto.p.upperband)

    def next(self):
        if not self.position:  # not in the market
            if self.buy_signal:  # if fast crosses slow to the upside
                lots = int(self.broker.get_cash() / self.data / self.p.one_lot_size)
                self.buy(size=lots * self.p.one_lot_size)  # enter long

        elif self.sell_signal:  # in the market & cross to the downside
            self.close()  # close long position

    def start(self):
        self.val_start = self.broker.get_cash()  # keep the starting cash

    def stop(self):
        # calculate the actual returns
        self.roi = (self.broker.get_value() / self.val_start) - 1.0
        print(f'Sto({self.p.period},{self.p.period_dfast},{self.p.period_dslow}) ROI: {100.0 * self.roi: .2f} %')


def backtest_strategy(strategy, optimization, plot, m1_low, m1_high, m2_low, m2_high, m3_low, m3_high):
    # Create a cerebro entity
    cerebro = bt.Cerebro()

    # Add a strategy
    if optimization:
        opt_args = {}

        if strategy == MovingAveragesCrossover:
            opt_args['fast_ma_period'] = range(m1_low, m1_high)
            opt_args['slow_ma_period'] = range(m2_low, m2_high)
        elif strategy == RSI:
            opt_args['period'] = range(m1_low, m1_high)
        elif strategy == MACD:
            opt_args['period_me1'] = range(m1_low, m1_high)
            opt_args['period_me2'] = range(m2_low, m2_high)
            opt_args['period_signal'] = range(m3_low, m3_high)
        elif strategy == Stochastic:
            opt_args['period'] = range(m1_low, m1_high)
            opt_args['period_dfast'] = range(m2_low, m2_high)
            opt_args['period_dslow'] = range(m3_low, m3_high)

        cerebro.optstrategy(strategy, **opt_args)

    else:
        cerebro.addstrategy(strategy)

    # Datas are in a subfolder of the samples. Need to find where the script is
    # because it could have been called from anywhere
    modpath = os.path.dirname(os.path.abspath(sys.argv[0]))
    datapath = os.path.join(modpath, './datas/EURUSD_Candlestick_1_D_BID_01.01.2011-23.07.2021.csv')

    # Create a Data Feed
    data = DukascopyCSVData(
        dataname=datapath,
        # Do not pass values before this date
        fromdate=datetime.datetime(2016, 1, 1),
        # Do not pass values after this date
        todate=datetime.datetime(2020, 12, 31),)

    # Add the Data Feed to Cerebro
    cerebro.adddata(data)

    # Set our desired cash start
    cerebro.broker.setcash(1000000)

    # Set the commission
    cerebro.broker.setcommission(commission=0.0)

    # Run over everything
    cerebro.run()

    if plot:
        cerebro.plot(style='candlestick', barup='green', bardown='red')


CLASSES_MAP = {
    'BuyAndHold': BuyAndHold,
    'MovingAveragesCrossover': MovingAveragesCrossover,
    'RSI': RSI,
    'MACD': MACD,
    'Stochastic': Stochastic,
}


def parse_args():
    parser = argparse.ArgumentParser(description='Common Strategies Sample')

    parser.add_argument('--strategy', '-s', choices=list(CLASSES_MAP),
                        default='', required=False,
                        help='strategy to be used during backtesting')

    parser.add_argument('--plot', required=False, default='',
                        nargs='?', const='{}',
                        metavar='kwargs', help='kwargs in key=value format')

    parser.add_argument('--optimization', '-o',
                        required=False, default='', nargs='?', const='{}',
                        metavar='kwargs', help='kwargs in key=value format')

    parser.add_argument('--m1_low', type=int,
                        default=12, required=False,
                        help='MACD Fast MA range low to optimize')

    parser.add_argument('--m1_high', type=int,
                        default=20, required=False,
                        help='MACD Fast MA range high to optimize')

    parser.add_argument('--m2_low', type=int,
                        default=26, required=False,
                        help='MACD Slow MA range low to optimize')

    parser.add_argument('--m2_high', type=int,
                        default=30, required=False,
                        help='MACD Slow MA range high to optimize')

    parser.add_argument('--m3_low', type=int,
                        default=2, required=False,
                        help='MACD Slow MA range low to optimize')

    parser.add_argument('--m3_high', type=int,
                        default=10, required=False,
                        help='MACD Slow MA range high to optimize')

    return parser.parse_args()


if __name__ == '__main__':
    args = parse_args()
    if args.strategy:
        backtest_strategy(args.strategy, args.optimization, args.plot,
                          args.m1_low, args.m1_high,
                          args.m2_low, args.m2_high,
                          args.m3_low, args.m3_high)
    else:
        for strategy in CLASSES_MAP.values():
            backtest_strategy(strategy, args.optimization, args.plot,
                              args.m1_low, args.m1_high,
                              args.m2_low, args.m2_high,
                              args.m3_low, args.m3_high)
