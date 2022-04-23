from utils.constants import *
from utils.indicators import *
from utils.observers import BuySellArrows

from datetime import datetime
from sortedcontainers import SortedDict

import math
import backtrader as bt


class BuyAndHold(bt.Strategy):

    params = (
        ('print_log', False),
        ('optimization_dict', dict()),

        ('one_lot_size', 100000),

        ('datetime_from', datetime.min),
        ('datetime_before', datetime.max),
    )

    def log(self, txt, dt=None, doprint=False):
        ''' Logging function fot this strategy'''
        if self.params.print_log or doprint:
            dt = dt or self.datas[0].datetime.date(0)
            print(f'{dt.isoformat()}, {txt}')

    def notify_order(self, order):
        if order.status in [order.Submitted, order.Accepted]:
            # Buy/Sell order submitted/accepted to/by broker - Nothing to do
            return

        # Check if an order has been completed
        # Attention: broker could reject order if not enough cash
        if order.status in [order.Completed]:
            if order.isbuy():
                self.log(f' BUY EXECUTED, '
                         f'Price: {order.executed.price:>9.5f}, '
                         f'Cost: {order.executed.value:>9.2f}, '
                         f'Comm: {order.executed.comm:>9.2f}',
                         dt=bt.num2date(order.executed.dt))
            else:  # Sell
                self.log(f'SELL EXECUTED, '
                         f'Price: {order.executed.price:>9.5f}, '
                         f'Cost: {order.executed.value:>9.2f}, '
                         f'Comm: {order.executed.comm:>9.2f}',
                         dt=bt.num2date(order.executed.dt))

        elif order.status in [order.Canceled, order.Margin, order.Rejected]:
            self.log('Order Canceled/Margin/Rejected')

    def notify_trade(self, trade):
        if not trade.isclosed:
            return

        self.log(f'({bt.num2date(trade.dtopen)}), {trade.data._name}, '
                 f'Gross: {trade.pnl:>9.2f}, '
                 f'Net : {trade.pnlcomm:>9.2f}, ',
                 dt=bt.num2date(trade.dtclose))

    def __init__(self):
        if self.p.optimization_dict:
            for key, value in self.p.optimization_dict.items():
                setattr(self.p, key, value)

    def next(self):
        if self.datas[0].datetime.datetime(0) < self.p.datetime_from:
            return

        elif self.datas[0].datetime.datetime(0) >= self.p.datetime_before:
            if self.position:
                self.close()
            else:
                self.env.runstop()
                return

        else:
            # buy and hold only at the beginning
            lots = int(self.broker.get_cash() / self.data / self.p.one_lot_size)
            self.buy(size=lots * self.p.one_lot_size)


class MovingAveragesCrossover(bt.Strategy):

    params = (
        ('print_log', False),
        ('optimization_dict', dict()),

        ('use_strength', False),
        ('strength', 0.0005),

        ('datetime_from', datetime.min),
        ('datetime_before', datetime.max),

        ('one_lot_size', 100000),

        ('fast_ma_period', 50),
        ('slow_ma_period', 200),

    )

    def log(self, txt, dt=None, doprint=False):
        ''' Logging function fot this strategy'''
        if self.params.print_log or doprint:
            dt = dt or self.datas[0].datetime.date(0)
            print(f'{dt.isoformat()}, {txt}')

    def notify_order(self, order):
        if order.status in [order.Submitted, order.Accepted]:
            # Buy/Sell order submitted/accepted to/by broker - Nothing to do
            return

        # Check if an order has been completed
        # Attention: broker could reject order if not enough cash
        if order.status in [order.Completed]:
            if order.isbuy():
                self.log(f' BUY EXECUTED, '
                         f'Price: {order.executed.price:>9.5f}, '
                         f'Cost: {order.executed.value:>9.2f}, '
                         f'Comm: {order.executed.comm:>9.2f}',
                         dt=bt.num2date(order.executed.dt))
            else:  # Sell
                self.log(f'SELL EXECUTED, '
                         f'Price: {order.executed.price:>9.5f}, '
                         f'Cost: {order.executed.value:>9.2f}, '
                         f'Comm: {order.executed.comm:>9.2f}',
                         dt=bt.num2date(order.executed.dt))

        elif order.status in [order.Canceled, order.Margin, order.Rejected]:
            self.log('Order Canceled/Margin/Rejected')

    def notify_trade(self, trade):
        if not trade.isclosed:
            return

        self.log(f'({bt.num2date(trade.dtopen)}), {trade.data._name}, '
                 f'Gross: {trade.pnl:>9.2f}, '
                 f'Net : {trade.pnlcomm:>9.2f}, ',
                 dt=bt.num2date(trade.dtclose))

    def __init__(self):
        if self.p.optimization_dict:
            for key, value in self.p.optimization_dict.items():
                setattr(self.p, key, value)

        if 'JPY' in self.datas[0]._name:
            self.p.one_lot_size /= 100

        self.fast_sma = fast_sma = bt.ind.SMA(period=self.p.fast_ma_period)  # fast moving average
        self.slow_sma = slow_sma = bt.ind.SMA(period=self.p.slow_ma_period)  # slow moving average
        self.crossover = bt.ind.CrossOver(fast_sma, slow_sma)  # crossover signal

        if self.p.use_strength:
            self.strength = bt.ind.SMA(abs(fast_sma - fast_sma(-1)), period=1, subplot=True)

    def next(self):
        if self.datas[0].datetime.datetime(0) < self.p.datetime_from:
            return

        elif self.datas[0].datetime.datetime(0) >= self.p.datetime_before:
            if self.position:
                self.close()
            else:
                self.env.runstop()
                return
        else:
            size = self.p.one_lot_size

            if not self.position:  # not in the market
                if self.crossover != 0:  # if there is signal
                    if self.crossover < 0:  # negate the size
                        size = -size

                    # only open position if signal is strong
                    if self.p.use_strength and self.strength.lines.sma[0] < self.p.strength:
                        return

                    # open position with target size
                    self.log(f'fast: {self.fast_sma.lines.sma[0]:.5f}, slow: {self.slow_sma.lines.sma[0]:.5f}'
                             f', diff: {self.strength.lines.sma[0]:.5f}' if self.p.use_strength else '')
                    self.order_target_size(target=size)

            else:  # in the market
                if self.position.size > 0 and self.crossover < 0:  # having buy position and sell signal
                    size = -size
                elif self.position.size < 0 and self.crossover > 0:  # having sell position and buy signal
                    pass
                else:
                    return

                # if this is retrived, one wants to reverse his position
                # if signal is not strong enough, close instead of reverse current position
                if self.p.use_strength and self.strength.lines.sma[0] < self.p.strength:
                    size = 0

                self.log(f'fast: {self.fast_sma.lines.sma[0]:.5f}, slow: {self.slow_sma.lines.sma[0]:.5f}'
                         f', diff: {self.strength.lines.sma[0]:.5f}' if self.p.use_strength else '')
                self.order_target_size(target=size)


class RSIPositionSizing(bt.Strategy):

    params = (
        ('print_log', False),
        ('optimization_dict', dict()),

        ('use_strength', False),

        ('one_lot_size', 100000),

        ('datetime_from', datetime.min),
        ('datetime_before', datetime.max),

        ('period', 14),
        ('upperband', 70.0),
        ('lowerband', 30.0),

        ('upper_unwind', 30.0),
        ('lower_unwind', 70.0),

        ('size_multiplier', 0.05),

    )

    def log(self, txt, dt=None, doprint=False):
        ''' Logging function fot this strategy'''
        if self.params.print_log or doprint:
            dt = dt or self.datas[0].datetime.date(0)
            print(f'{dt.isoformat()}, {txt}')

    def notify_order(self, order):
        if order.status in [order.Submitted, order.Accepted]:
            # Buy/Sell order submitted/accepted to/by broker - Nothing to do
            return

        # Check if an order has been completed
        # Attention: broker could reject order if not enough cash
        if order.status in [order.Completed]:
            if order.isbuy():
                self.log(f' BUY EXECUTED, '
                         f'Price: {order.executed.price:>9.5f}, '
                         f'Cost: {order.executed.value:>9.2f}, '
                         f'Comm: {order.executed.comm:>9.2f}',
                         dt=bt.num2date(order.executed.dt))
            else:  # Sell
                self.log(f'SELL EXECUTED, '
                         f'Price: {order.executed.price:>9.5f}, '
                         f'Cost: {order.executed.value:>9.2f}, '
                         f'Comm: {order.executed.comm:>9.2f}',
                         dt=bt.num2date(order.executed.dt))

        elif order.status in [order.Canceled, order.Margin, order.Rejected]:
            self.log('Order Canceled/Margin/Rejected')

    def notify_trade(self, trade):
        if not trade.isclosed:
            return

        self.log(f'({bt.num2date(trade.dtopen)}), {trade.data._name}, '
                 f'Gross: {trade.pnl:>9.2f}, '
                 f'Net : {trade.pnlcomm:>9.2f}, ',
                 dt=bt.num2date(trade.dtclose))

    def __init__(self):
        if self.p.optimization_dict:
            for key, value in self.p.optimization_dict.items():
                setattr(self.p, key, value)

        self.max_buy_position = self.p.one_lot_size
        self.max_sell_position = self.p.one_lot_size

        self.rsi = bt.ind.RSI(period=self.p.period, upperband=self.p.upperband, lowerband=self.p.lowerband, safediv=True)

        self.buy_signal = self.rsi <= self.p.lowerband
        self.sell_signal = self.rsi >= self.p.upperband

        self.stop_buy_signal = self.rsi >= self.p.lower_unwind
        self.stop_sell_signal = self.rsi <= self.p.upper_unwind

        self.normal_rsi_buy_signal = bt.ind.CrossOver(self.rsi, self.p.lowerband, plot=False)
        self.normal_rsi_sell_signal = bt.ind.CrossOver(self.rsi, self.p.upperband, plot=False)

    def next(self):
        if self.datas[0].datetime.datetime(0) < self.p.datetime_from:
            return

        elif self.datas[0].datetime.datetime(0) >= self.p.datetime_before:
            if self.position:
                self.close()
            else:
                self.env.runstop()
                return
        else:
            if self.p.use_strength:

                if self.position.size == 0:
                    self.max_buy_position = self.p.one_lot_size
                    self.max_sell_position = self.p.one_lot_size

                    if self.buy_signal:
                        size_multiplier = 1 + (self.p.lowerband - self.rsi) * self.p.size_multiplier
                        self.max_buy_position = max(self.max_buy_position, self.p.one_lot_size * size_multiplier)
                        self.order_target_size(target=self.max_buy_position)

                    elif self.sell_signal:
                        size_multiplier = 1 + (self.rsi - self.p.upperband) * self.p.size_multiplier
                        self.max_sell_position = max(self.max_sell_position, self.p.one_lot_size * size_multiplier)
                        self.order_target_size(target=-self.max_sell_position)

                elif self.position.size > 0:
                    if self.stop_buy_signal:
                        self.close()

                    elif self.buy_signal:
                        size_multiplier = 1 + (self.p.lowerband - self.rsi) * self.p.size_multiplier
                        self.max_buy_position = max(self.max_buy_position, self.p.one_lot_size * size_multiplier)
                        self.order_target_size(target=self.max_buy_position)

                elif self.position.size < 0:
                    if self.stop_sell_signal:
                        self.close()

                    elif self.sell_signal:
                        size_multiplier = 1 + (self.rsi - self.p.upperband) * self.p.size_multiplier
                        self.max_sell_position = max(self.max_sell_position, self.p.one_lot_size * size_multiplier)
                        self.order_target_size(target=-self.max_sell_position)

            else:

                if not self.position.size:
                    if self.normal_rsi_buy_signal > 0:
                        self.buy(size=self.p.one_lot_size)
                    elif self.normal_rsi_sell_signal < 0:
                        self.sell(size=self.p.one_lot_size)
                else:
                    if ((self.position.size > 0 and self.normal_rsi_sell_signal < 0) or
                            (self.position.size < 0 and self.normal_rsi_buy_signal > 0)):
                        self.order_target_size(target=-self.position.size)


class CurrencyStrength(bt.Strategy):
    '''
    Note that the strategy is based on EightCurrenciesIndicator
    Datafeeds of bid prices of 28 symbols are first added before ask prices
    There are total 56 datafeeds, and first 28 datafeeds, which are bid prices,
        are used for evaluation of indicator values
    '''

    # Default parameters for plotting and trading strategy
    params = (
        ('printlog', True),
        ('plot_ask_cs', False),

        ('period', 14),

        ('one_mini_lot_size', 10000),
        ('stoptype', bt.Order.StopTrail),
        ('trailamount', 0.00050),
        ('trailpercent', 0.00008),

        ('AUDCAD', 1.000), ('AUDCHF', 1.000), ('AUDJPY', 1.000), ('AUDNZD', 1.000),
        ('AUDUSD', 1.000), ('CADCHF', 1.000), ('CADJPY', 1.000), ('CHFJPY', 1.000),
        ('EURAUD', 1.000), ('EURCAD', 1.000), ('EURCHF', 1.000), ('EURGBP', 1.000),
        ('EURJPY', 1.000), ('EURNZD', 1.000), ('EURUSD', 1.000), ('GBPAUD', 1.000),
        ('GBPCAD', 1.000), ('GBPCHF', 1.000), ('GBPJPY', 1.000), ('GBPNZD', 1.000),
        ('GBPUSD', 1.000), ('NZDCAD', 1.000), ('NZDCHF', 1.000), ('NZDJPY', 1.000),
        ('NZDUSD', 1.000), ('USDCAD', 1.000), ('USDCHF', 1.000), ('USDJPY', 1.000),
    )

    def log(self, txt, dt=None, doprint=False):
        if self.params.printlog or doprint:
            dt = dt or self.datas[0].datetime.datetime()
            print(f'{dt.isoformat()}, {txt}')

    def notify_order(self, order):
        if order.status in [order.Submitted, order.Accepted]:
            # Buy/Sell order submitted/accepted to/by broker - Nothing to do
            return

        # Check if an order has been completed
        # Attention: broker could reject order if not enough cash
        if order.status in [order.Completed]:
            if order.isbuy():
                self.log(f'{order.info.symbol} ({order.info.type}), '
                         f' BUY EXECUTED, '
                         f'Price: {order.executed.price:>9.5f}, '
                         f'Cost: {order.executed.value:>9.2f}, '
                         f'Comm: {order.executed.comm:>9.2f}',
                         dt=bt.num2date(order.executed.dt))
            else:  # Sell
                self.log(f'{order.info.symbol} ({order.info.type}), '
                         f'SELL EXECUTED, '
                         f'Price: {order.executed.price:>9.5f}, '
                         f'Cost: {order.executed.value:>9.2f}, '
                         f'Comm: {order.executed.comm:>9.2f}',
                         dt=bt.num2date(order.executed.dt))

        elif order.status in [order.Canceled, order.Margin, order.Rejected]:
            self.log('Order Canceled/Margin/Rejected')

    def notify_trade(self, trade):
        if not trade.isclosed:
            return

        self.log(f'({bt.num2date(trade.dtopen)}), {trade.data._name}, '
                 f'Gross: {trade.pnl:>9.2f}, '
                 f'Net : {trade.pnlcomm:>9.2f}, ',
                 dt=bt.num2date(trade.dtclose))

    def __init__(self):
        # Add ACS28 indicator
        self.eight_currencies_bid = EightCurrenciesIndicator(*self.datas[:28],
                                                             period=self.p.period,
                                                             AUDCAD=self.p.AUDCAD, AUDCHF=self.p.AUDCHF, AUDJPY=self.p.AUDJPY, AUDNZD=self.p.AUDNZD,
                                                             AUDUSD=self.p.AUDUSD, CADCHF=self.p.CADCHF, CADJPY=self.p.CADJPY, CHFJPY=self.p.CHFJPY,
                                                             EURAUD=self.p.EURAUD, EURCAD=self.p.EURCAD, EURCHF=self.p.EURCHF, EURGBP=self.p.EURGBP,
                                                             EURJPY=self.p.EURJPY, EURNZD=self.p.EURNZD, EURUSD=self.p.EURUSD, GBPAUD=self.p.GBPAUD,
                                                             GBPCAD=self.p.GBPCAD, GBPCHF=self.p.GBPCHF, GBPJPY=self.p.GBPJPY, GBPNZD=self.p.GBPNZD,
                                                             GBPUSD=self.p.GBPUSD, NZDCAD=self.p.NZDCAD, NZDCHF=self.p.NZDCHF, NZDJPY=self.p.NZDJPY,
                                                             NZDUSD=self.p.NZDUSD, USDCAD=self.p.USDCAD, USDCHF=self.p.USDCHF, USDJPY=self.p.USDJPY,
                                                             )

        self.eight_currencies_ask = EightCurrenciesIndicator(*self.datas[-28:],
                                                             plot=self.p.plot_ask_cs,
                                                             period=self.p.period,
                                                             AUDCAD=self.p.AUDCAD, AUDCHF=self.p.AUDCHF, AUDJPY=self.p.AUDJPY, AUDNZD=self.p.AUDNZD,
                                                             AUDUSD=self.p.AUDUSD, CADCHF=self.p.CADCHF, CADJPY=self.p.CADJPY, CHFJPY=self.p.CHFJPY,
                                                             EURAUD=self.p.EURAUD, EURCAD=self.p.EURCAD, EURCHF=self.p.EURCHF, EURGBP=self.p.EURGBP,
                                                             EURJPY=self.p.EURJPY, EURNZD=self.p.EURNZD, EURUSD=self.p.EURUSD, GBPAUD=self.p.GBPAUD,
                                                             GBPCAD=self.p.GBPCAD, GBPCHF=self.p.GBPCHF, GBPJPY=self.p.GBPJPY, GBPNZD=self.p.GBPNZD,
                                                             GBPUSD=self.p.GBPUSD, NZDCAD=self.p.NZDCAD, NZDCHF=self.p.NZDCHF, NZDJPY=self.p.NZDJPY,
                                                             NZDUSD=self.p.NZDUSD, USDCAD=self.p.USDCAD, USDCHF=self.p.USDCHF, USDJPY=self.p.USDJPY,
                                                             )

        self.eight_currencies_bid.plotinfo.plotname = 'CS8_BID'
        self.eight_currencies_ask.plotinfo.plotname = 'CS8_ASK'

        # Set up buysell arrows
        for data in self.datas[:28]:
            bt.obs.BuySell(data, barplot=True, bardist=0.00001)
        for data in self.datas[-28:]:
            BuySellArrows(data, barplot=True, bardist=0.00001)

        # Dictionary to hold limit orders for Close
        self.o = dict()

        # Dictionary to hold last open position orders
        self.last_open_position = dict()

        # Dictionary to hold previous open positioning time
        self.last_open_position_time = dict()

    def next(self):
        if self.datas[0].datetime.datetime(0) < self.p.datetime_from:
            return

        elif self.datas[0].datetime.datetime(0) >= self.p.datetime_before:
            if self.position:
                self.close()
            else:
                self.env.runstop()
                return
        else:
            buy_symbol, sell_symbol = self.get_buy_sell_symbol()

            # Iterate first half of data
            for d in self.datas[:len(self.datas) // 2]:
                pair_name = d._name[0:6]

                dt = d.datetime.datetime()
                pos = self.getposition(d).size

                size = self.p.one_mini_lot_size
                trailamount = self.p.trailamount
                trailpercent = self.p.trailpercent

                # Modifications for JPY markets
                if 'JPY' in d._name:
                    size /= 100
                    trailamount *= 100
                    trailpercent *= 100

                # If no open position
                if not pos:
                    # Open a buy position if buy symbol is matched
                    if pair_name == buy_symbol:
                        # Prevent double ordering
                        if self.last_open_position_time.get(d, None) != dt:
                            # Open a buy position
                            self.log(f'{pair_name} Open Buy Created at {self.dnames[pair_name + "_ASK"].close[0]:.5f}')

                            self.last_open_position[d] = self.buy(data=self.dnames[pair_name + '_ASK'],  # use ask price data for buy
                                                                  size=size,)

                            self.last_open_position[d].addinfo(symbol=pair_name, type=' Open')

                            self.last_open_position_time[d] = dt

                            # Clear old limit orders for Close
                            self.o[d] = None

                    # Or open a sell position if sell symbol is matched
                    elif pair_name == sell_symbol:
                        # Prevent double ordering
                        if self.last_open_position_time.get(d, None) != dt:
                            self.log(f'{pair_name} Open Sell Created at {self.dnames[pair_name + "_BID"].close[0]:.5f}')

                            # Open a sell position
                            self.last_open_position[d] = self.sell(data=self.dnames[pair_name + '_BID'],  # use bid price data for sell
                                                                   size=size,)

                            self.last_open_position[d].addinfo(symbol=pair_name, type=' Open')

                            self.last_open_position_time[d] = dt

                            # Clear old limit orders for Close
                            self.o[d] = None

                # Else if there is open position
                elif pos and self.o.get(d, None) is None:
                    base_currency, quote_currency = pair_name[:3], pair_name[3:]
                    before = getattr(self.eight_currencies_bid.lines, base_currency)[-1] - getattr(self.eight_currencies_bid.lines, quote_currency)[-1]
                    after = getattr(self.eight_currencies_bid.lines, base_currency)[0] - getattr(self.eight_currencies_bid.lines, quote_currency)[0]
                    # currency crossover
                    if (before <= 0.0 and after > 0.0) or (before >= 0.0 and after < 0.0):
                        # If there is existing buy position, sell if there is crossover
                        if self.last_open_position.get(d, None) and self.last_open_position[d].isbuy():
                            self.log(f'{pair_name} Close Sell Created at {self.dnames[pair_name + "_BID"].close[0]:.5f}')

                            # Create a sell order
                            self.o[d] = self.sell(data=self.dnames[pair_name + '_BID'], size=size,
                                                  exectype=self.p.stoptype,
                                                  trailpercent=trailpercent,)
                            self.o[d].addinfo(symbol=pair_name, type='Close')

                        # Else if the existing position is sell, buy if there is crossover
                        elif self.last_open_position.get(d, None) and self.last_open_position[d].issell():
                            self.log(f'{pair_name} Close Buy Created at {self.dnames[pair_name + "_ASK"].close[0]:.5f}')

                            # Create a buy order
                            self.o[d] = self.buy(data=self.dnames[pair_name + '_ASK'], size=size,
                                                 exectype=self.p.stoptype,
                                                 trailpercent=trailpercent,)
                            self.o[d].addinfo(symbol=pair_name, type='Close')

    def stop(self):
        self.log(','.join(f'{getattr(self.p, symbol):.3f}' for symbol in SYMBOLS), doprint=True)
        self.log(f'End Value: {self.broker.getvalue()}', doprint=True)

    def get_buy_sell_symbol(self):
        rankings = SortedDict({getattr(self.eight_currencies_bid.lines, currency)[0]: currency for currency in CURRENCIES})
        max_rsi, max_currencies = rankings.peekitem(-1)
        min_rsi, min_currencies = rankings.peekitem(0)

        buy_symbol, sell_symbol = '', ''
        if min_rsi <= 35 and max_rsi >= 65:
            buy_symbol, sell_symbol = min_currencies + max_currencies, ''
            if buy_symbol not in SYMBOLS:
                buy_symbol, sell_symbol = sell_symbol, buy_symbol

        return buy_symbol, sell_symbol


class ACSTrailing(bt.Strategy):
    '''
    Note that the strategy is based on TwentyeightPairsIndicator
    Datafeeds of bid prices of 28 symbols are first added before ask prices
    There are total 56 datafeeds, and first 28 datafeeds, which are bid prices,
        are used for evaluation of indicator values
    '''

    # Default parameters for plotting and trading strategy
    params = (
        ('printlog', True),
        ('plot_ask_acs', False),

        ('fast_ma_period', 3),
        ('slow_ma_period', 20),

        ('one_mini_lot_size', 10000),
        ('stoptype', bt.Order.StopTrail),
        ('trailamount', 0.010),
        ('trailpercent', 0.0),

        ('AUDCAD', 0.650), ('AUDCHF', 0.550), ('AUDJPY', 0.700), ('AUDNZD', 0.440),
        ('AUDUSD', 0.650), ('CADCHF', 1.000), ('CADJPY', 1.000), ('CHFJPY', 1.000),
        ('EURAUD', 0.850), ('EURCAD', 0.800), ('EURCHF', 0.850), ('EURGBP', 0.600),
        ('EURJPY', 0.650), ('EURNZD', 0.800), ('EURUSD', 0.800), ('GBPAUD', 0.250),
        ('GBPCAD', 0.250), ('GBPCHF', 0.200), ('GBPJPY', 0.500), ('GBPNZD', 0.050),
        ('GBPUSD', 0.500), ('NZDCAD', 0.700), ('NZDCHF', 0.700), ('NZDJPY', 0.700),
        ('NZDUSD', 0.700), ('USDCAD', 1.000), ('USDCHF', 1.000), ('USDJPY', 1.000),
    )

    def log(self, txt, dt=None, doprint=False):
        if self.params.printlog or doprint:
            dt = dt or self.datas[0].datetime.datetime()
            print(f'{dt.isoformat()}, {txt}')

    def notify_order(self, order):
        if order.status in [order.Submitted, order.Accepted]:
            # Buy/Sell order submitted/accepted to/by broker - Nothing to do
            return

        # Check if an order has been completed
        # Attention: broker could reject order if not enough cash
        if order.status in [order.Completed]:
            if order.isbuy():
                self.log(f'{order.info.symbol} ({order.info.type}), '
                         f' BUY EXECUTED, '
                         f'Price: {order.executed.price:>9.5f}, '
                         f'Cost: {order.executed.value:>9.2f}, '
                         f'Comm: {order.executed.comm:>9.2f}',
                         dt=bt.num2date(order.executed.dt))
            else:  # Sell
                self.log(f'{order.info.symbol} ({order.info.type}), '
                         f'SELL EXECUTED, '
                         f'Price: {order.executed.price:>9.5f}, '
                         f'Cost: {order.executed.value:>9.2f}, '
                         f'Comm: {order.executed.comm:>9.2f}',
                         dt=bt.num2date(order.executed.dt))

        elif order.status in [order.Canceled, order.Margin, order.Rejected]:
            self.log('Order Canceled/Margin/Rejected')

    def notify_trade(self, trade):
        if not trade.isclosed:
            return

        self.log(f'({bt.num2date(trade.dtopen)}), {trade.data._name}, '
                 f'Gross: {trade.pnl:>9.2f}, '
                 f'Net : {trade.pnlcomm:>9.2f}, ',
                 dt=bt.num2date(trade.dtclose))

    def __init__(self):
        # Add ACS28 indicator
        self.twentyeight_pairs_bid = TwentyeightPairsIndicator(*self.datas[:28],
                                                               fast_ma_period=self.p.fast_ma_period,
                                                               slow_ma_period=self.p.slow_ma_period,
                                                               AUDCAD=self.p.AUDCAD, AUDCHF=self.p.AUDCHF, AUDJPY=self.p.AUDJPY, AUDNZD=self.p.AUDNZD,
                                                               AUDUSD=self.p.AUDUSD, CADCHF=self.p.CADCHF, CADJPY=self.p.CADJPY, CHFJPY=self.p.CHFJPY,
                                                               EURAUD=self.p.EURAUD, EURCAD=self.p.EURCAD, EURCHF=self.p.EURCHF, EURGBP=self.p.EURGBP,
                                                               EURJPY=self.p.EURJPY, EURNZD=self.p.EURNZD, EURUSD=self.p.EURUSD, GBPAUD=self.p.GBPAUD,
                                                               GBPCAD=self.p.GBPCAD, GBPCHF=self.p.GBPCHF, GBPJPY=self.p.GBPJPY, GBPNZD=self.p.GBPNZD,
                                                               GBPUSD=self.p.GBPUSD, NZDCAD=self.p.NZDCAD, NZDCHF=self.p.NZDCHF, NZDJPY=self.p.NZDJPY,
                                                               NZDUSD=self.p.NZDUSD, USDCAD=self.p.USDCAD, USDCHF=self.p.USDCHF, USDJPY=self.p.USDJPY,)

        self.twentyeight_pairs_ask = TwentyeightPairsIndicator(*self.datas[-28:],
                                                               plot=self.p.plot_ask_acs,
                                                               fast_ma_period=self.p.fast_ma_period,
                                                               slow_ma_period=self.p.slow_ma_period,
                                                               AUDCAD=self.p.AUDCAD, AUDCHF=self.p.AUDCHF, AUDJPY=self.p.AUDJPY, AUDNZD=self.p.AUDNZD,
                                                               AUDUSD=self.p.AUDUSD, CADCHF=self.p.CADCHF, CADJPY=self.p.CADJPY, CHFJPY=self.p.CHFJPY,
                                                               EURAUD=self.p.EURAUD, EURCAD=self.p.EURCAD, EURCHF=self.p.EURCHF, EURGBP=self.p.EURGBP,
                                                               EURJPY=self.p.EURJPY, EURNZD=self.p.EURNZD, EURUSD=self.p.EURUSD, GBPAUD=self.p.GBPAUD,
                                                               GBPCAD=self.p.GBPCAD, GBPCHF=self.p.GBPCHF, GBPJPY=self.p.GBPJPY, GBPNZD=self.p.GBPNZD,
                                                               GBPUSD=self.p.GBPUSD, NZDCAD=self.p.NZDCAD, NZDCHF=self.p.NZDCHF, NZDJPY=self.p.NZDJPY,
                                                               NZDUSD=self.p.NZDUSD, USDCAD=self.p.USDCAD, USDCHF=self.p.USDCHF, USDJPY=self.p.USDJPY,)

        self.twentyeight_pairs_bid.plotinfo.plotname = 'ACS28_BID'
        self.twentyeight_pairs_ask.plotinfo.plotname = 'ACS28_ASK'

        # Set up buysell arrows
        for data in self.datas[:28]:
            bt.obs.BuySell(data, barplot=True, bardist=0.00001)
        for data in self.datas[-28:]:
            BuySellArrows(data, barplot=True, bardist=0.00001)

        # Dictionary to hold limit orders for Close
        self.o = dict()

        # Dictionary to hold last open position orders
        self.last_open_position = dict()

        # Dictionary to hold previous open positioning time
        self.last_open_position_time = dict()

    def next(self):
        if self.datas[0].datetime.datetime(0) < self.p.datetime_from:
            return

        elif self.datas[0].datetime.datetime(0) >= self.p.datetime_before:
            if self.position:
                self.close()
            else:
                self.env.runstop()
                return
        else:
            buy_symbol, sell_symbol = self.get_buy_sell_symbol()

            # Iterate first half of data
            for d in self.datas[:len(self.datas) // 2]:
                pair_name = d._name[0:6]

                dt = d.datetime.datetime()
                pos = self.getposition(d).size

                size = self.p.one_mini_lot_size
                trailamount = self.p.trailamount

                # Modifications for JPY markets
                if 'JPY' in d._name:
                    size /= 100
                    trailamount *= 100

                # If no open position
                if not pos:
                    # Open a buy position if buy symbol is matched
                    if pair_name == buy_symbol:
                        # Prevent double ordering
                        if self.last_open_position_time.get(d, None) != dt:
                            # Open a buy position
                            self.log(f'{pair_name} Open Buy Created at {self.dnames[pair_name + "_ASK"].close[0]:.5f}')

                            self.last_open_position[d] = self.buy(data=self.dnames[pair_name + '_ASK'],  # use ask price data for buy
                                                                  size=size,)

                            self.last_open_position[d].addinfo(symbol=pair_name, type=' Open')

                            self.last_open_position_time[d] = dt

                            # Clear old limit orders for Close
                            self.o[d] = None

                    # Or open a sell position if sell symbol is matched
                    elif pair_name == sell_symbol:
                        # Prevent double ordering
                        if self.last_open_position_time.get(d, None) != dt:
                            self.log(f'{pair_name} Open Sell Created at {self.dnames[pair_name + "_BID"].close[0]:.5f}')

                            # Open a sell position
                            self.last_open_position[d] = self.sell(data=self.dnames[pair_name + '_BID'],  # use bid price data for sell
                                                                   size=size,)

                            self.last_open_position[d].addinfo(symbol=pair_name, type=' Open')

                            self.last_open_position_time[d] = dt

                            # Clear old limit orders for Close
                            self.o[d] = None

                # Else if there is open position
                elif pos and self.o.get(d, None) is None:
                    # If there is existing buy position, sell if there is acs < 0
                    if self.last_open_position.get(d, None) and self.last_open_position[d].isbuy() and pair_name == sell_symbol:
                        self.log(f'{pair_name} Close Sell Created at {self.dnames[pair_name + "_BID"].close[0]:.5f}')

                        # Create a trailing stop limit sell order
                        self.o[d] = self.sell(data=self.dnames[pair_name + '_BID'],
                                              size=size,)

                        self.o[d].addinfo(symbol=pair_name, type='Close')

                    # Else if the existing position is sell, buy if acs > 0
                    elif self.last_open_position.get(d, None) and self.last_open_position[d].issell() and pair_name == buy_symbol:
                        self.log(f'{pair_name} Close Buy Created at {self.dnames[pair_name + "_ASK"].close[0]:.5f}')

                        # Create a trailing stop limit buy order
                        self.o[d] = self.buy(data=self.dnames[pair_name + '_ASK'],
                                             size=size,)

                        self.o[d].addinfo(symbol=pair_name, type='Close')

    def stop(self):
        # if self.p.trailamount != 0:
        #     self.log(f'(Trailing pips: {self.p.trailamount:.5f}) End Value: {self.broker.getvalue()}', doprint=True)
        # if self.p.trailpercent != 0:
        #     self.log(f'(Trailing pips: {self.p.trailamount * 100:.2f}%) End Value: {self.broker.getvalue()}', doprint=True)
        self.log(','.join(f'{getattr(self.p, symbol):.3f}' for symbol in SYMBOLS), doprint=True)
        self.log(f'End Value: {self.broker.getvalue()}', doprint=True)

    def get_buy_sell_symbol(self):

        # Sorted dicionary for finding maximum or minimum ACS values
        ask_acs = {}
        bid_acs = {}

        # Ask ACS28
        for symbol in SYMBOLS:
            # Find ACS value
            acs_value = getattr(self.twentyeight_pairs_ask.lines, symbol)[0]

            # Hash value into dict if it is available
            if not math.isnan(acs_value) and acs_value != 0.0:
                ask_acs[symbol] = getattr(self.twentyeight_pairs_ask.lines, symbol)[0]
            else:
                # Terminate if not all acs value
                return '', ''

        # Sort ask ACS28 values
        ask_acs = dict(sorted(ask_acs.items(), key=lambda item: item[1], reverse=True))

        # Bid ACS28
        for symbol in SYMBOLS:
            # Find ACS value
            acs_value = getattr(self.twentyeight_pairs_bid.lines, symbol)[0]

            # Hash value into dict if it is available
            if not math.isnan(acs_value) and acs_value != 0.0:
                bid_acs[symbol] = getattr(self.twentyeight_pairs_bid.lines, symbol)[0]
            else:
                # Terminate if not all acs value
                return '', ''

        # Sort bid ACS28 values
        bid_acs = dict(sorted(bid_acs.items(), key=lambda item: item[1], reverse=True))

        # Return buy and sell symobls for ordering
        buy_symbol = list(ask_acs.keys())[0]
        sell_symbol = list(bid_acs.keys())[-1]

        return buy_symbol, sell_symbol
