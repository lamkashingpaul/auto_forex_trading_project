from datetime import datetime, timedelta
from psycopg2 import sql
import argparse
import backtrader as bt
import collections
import concurrent.futures
import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import os
import pandas as pd
import psycopg2
import random

# lookup dictionaries and list
NUMBER_OF_WORKERS = 16

MY_TABLE_NAME = 'candlesticks_candlestick'

'''
structure of tuple value (value for PSQL query, bt.TimeFrame, compression)
'''
PERIODS = {
    'M1': (1, bt.TimeFrame.Minutes, 1),
    'M5': (5, bt.TimeFrame.Minutes, 5),
    'M15': (15, bt.TimeFrame.Minutes, 15),
    'M30': (30, bt.TimeFrame.Minutes, 30),
    'H1': (60, bt.TimeFrame.Minutes, 60),
    'H4': (240, bt.TimeFrame.Minutes, 240),
    'D1': (1440, bt.TimeFrame.Days, 1),
    'W1': (10080, bt.TimeFrame.Days, 7),
    'MN': (43200, bt.TimeFrame.Months, 1),
}

SYMBOLS = [
    'AUDCAD', 'AUDCHF', 'AUDJPY', 'AUDNZD', 'AUDUSD', 'CADCHF',
    'CADJPY', 'CHFJPY', 'EURAUD', 'EURCAD', 'EURCHF', 'EURGBP',
    'EURJPY', 'EURNZD', 'EURUSD', 'GBPAUD', 'GBPCAD', 'GBPCHF',
    'GBPJPY', 'GBPNZD', 'GBPUSD', 'NZDCAD', 'NZDCHF', 'NZDJPY',
    'NZDUSD', 'USDCAD', 'USDCHF', 'USDJPY',
]


class PSQLData(bt.feeds.DataBase):
    params = (
        ('dataname', None),
        ('name', None),
        ('symbol', 'AUDCAD'),
        ('period', 'D1'),
        ('timeframe', bt.TimeFrame.Days),
        ('compression', 1),
        ('fromdate', datetime.min),
        ('todate', datetime.max),

        # parameterized column indices for overwriting
        ('datetime', 0),
        ('open', 1),
        ('high', 2),
        ('low', 3),
        ('close', 4),
        ('volume', 5),
        ('openinterest', -1),
    )

    def start(self):
        period_in_minute, self.p.timeframe, self.p.compression, = PERIODS[self.p.period]

        if not self.p.name:
            self.p.name = self.p.symbol

        # connect to PSQL
        conn = self._connect_db()
        cursor = conn.cursor()

        # define query
        query = sql.SQL('SELECT {time}, {open}, {high}, {low}, {close}, {volume} '
                        'FROM {table} '
                        'WHERE ({period} = %s AND '
                        '{symbol} = %s AND '
                        '{volume} > 0 AND '
                        '{time} BETWEEN %s AND %s)').format(table=sql.Identifier('candlesticks_candlestick'),
                                                            symbol=sql.Identifier('symbol'),
                                                            time=sql.Identifier('time'),
                                                            open=sql.Identifier('open'),
                                                            high=sql.Identifier('high'),
                                                            low=sql.Identifier('low'),
                                                            close=sql.Identifier('close'),
                                                            volume=sql.Identifier('volume'),
                                                            period=sql.Identifier('period'),)

        # execute query template with input parameters
        cursor.execute(query, (period_in_minute, self.p.symbol, self.p.fromdate, self.p.todate))

        self.rows = cursor.fetchall()

        conn.close()

        self.rows_i = 0
        super(PSQLData, self).start()

    def _load(self):
        if self.rows is None or self.rows_i >= len(self.rows):
            return False

        row = self.rows[self.rows_i]

        for datafield in self.getlinealiases():

            if datafield == 'datetime':
                self.lines.datetime[0] = bt.date2num(row[self.p.datetime])

            else:
                # get column index
                col_idx = getattr(self.p, datafield)

                # skip if line is not used
                if col_idx < 0:
                    continue
                else:
                    getattr(self.lines, datafield)[0] = row[col_idx]

        self.rows_i += 1
        return True

    def _connect_db(self):
        conn = psycopg2.connect(database='fyp',
                                # info below is not needed while using unix socket
                                # host='192.168.1.72',
                                # port='5432',
                                # user=os.environ.get('PG_USER', ''),
                                # password=os.environ.get('PG_PASSWORD', '')
                                )

        return conn

    def preload(self):
        super(PSQLData, self).preload()
        self.rows = None


class BuyAndHold(bt.Strategy):

    params = (
        ('name', 'BuyAndHold'),
        ('one_lot_size', 100000),
    )

    def log(self, txt, dt=None, doprint=True):
        ''' Logging function fot this strategy'''
        if self.params.printlog or doprint:
            dt = dt or self.datas[0].datetime.date(0)
            print('%s, %s' % (dt.isoformat(), txt))

    def __init__(self):
        if self.p.name is None:
            self.p.name = 'B&H'

    def start(self):
        # keep the starting cash
        self.val_start = self.broker.get_cash()

    def nextstart(self):
        # buy all with the available cash
        lots = int(self.broker.get_cash() / self.data / self.p.one_lot_size)
        self.buy(size=lots * self.p.one_lot_size)


class MACD(bt.Strategy):
    params = (
        ('name', 'MACD'),
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
        fast_ema = bt.ind.EMA(period=self.p.period_me1)
        slow_ema = bt.ind.EMA(period=self.p.period_me2)

        macd = bt.ind.MACDHisto(period_me1=self.p.period_me1, period_me2=self.p.period_me2, period_signal=self.p.period_signal)
        self.crossover = bt.ind.CrossOver(macd.macd, macd.signal, plot=False)

    def next(self):

        lots = int(self.broker.get_cash() / self.data / self.p.one_lot_size)

        if not self.position:  # not in the market
            if self.crossover > 0:  # if MACD crosses signal to the upside
                self.buy(size=lots * self.p.one_lot_size)  # enter long
            elif self.crossover < 0:
                self.sell(size=lots * self.p.one_lot_size)  # enter short

        else:  # in the market
            if self.crossover > 0 or self.crossover < 0:  # if MACD crosses signal
                self.order_target_size(target=-self.position.size)  # reverse current position


class Stochastic(bt.Strategy):
    params = (
        ('name', 'Stochastic'),
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
        if self.p.name is None:
            self.p.name = f'Stc({self.p.period})'

        sto = bt.ind.Stochastic(period=self.p.period,
                                period_dfast=self.p.period_dfast,
                                period_dslow=self.p.period_dslow,
                                upperband=self.p.upperband,
                                lowerband=self.p.lowerband,)

        crossover = bt.ind.CrossOver(sto.percK, sto.percD, plot=False)

        self.buy_signal = bt.And(crossover > 0, sto.percD < sto.p.lowerband)
        self.sell_signal = bt.And(crossover < 0, sto.percD > sto.p.upperband)

    def next(self):
        if not self.position:  # not in the market
            if self.buy_signal:  # if percK crosses percD to the upside and it happens below lowerband
                lots = int(self.broker.get_cash() / self.data / self.p.one_lot_size)
                self.buy(size=lots * self.p.one_lot_size)  # enter long

        elif self.sell_signal:  # in the market & cross to the downside and it happens above upperband
            self.close()  # close long position


def random_small_datetime_interval(datetime_from, datetime_before, duration):
    delta = datetime_before - datetime_from

    if duration > delta:
        return datetime_from, datetime_before
    else:
        delta -= duration
        random_second = random.randrange(int(delta.total_seconds()))
        return (datetime_from + timedelta(seconds=random_second), datetime_from + timedelta(seconds=random_second) + duration)


def small_interval_generator(datetime_from, datetime_before, duration, n):
    for _ in range(n):
        yield random_small_datetime_interval(datetime_from, datetime_before, duration)


def backtest_strategies(strategies, symbol, period, fromdate, todate):
    rois = []

    data = PSQLData(symbol=symbol, period=period, fromdate=fromdate, todate=todate)

    for (strategy, params) in strategies:

        cerebro = bt.Cerebro()

        cerebro.addobserver(bt.observers.Broker)
        cerebro.addobserver(bt.observers.BuySell, barplot=True, bardist=0.0001)
        cerebro.addobserver(bt.observers.Trades, pnlcomm=True)

        cerebro.addstrategy(strategy, **params)

        cerebro.adddata(data)

        cerebro.broker.setcash(1000000)

        starting_cash = cerebro.broker.getvalue()

        cerebro.run(stdstats=False)

        roi = (cerebro.broker.getvalue() / starting_cash) - 1

        # cerebro.plot(style='candlestick', barup='green', bardown='red')

        rois.append(roi)

    return rois


def main():
    duration = timedelta(days=30)
    total_datetime_interval = (datetime(2019, 1, 1), datetime(2020, 1, 1))
    rng_interval_generator = small_interval_generator(*total_datetime_interval, duration, 32)

    strategies = [
        (BuyAndHold, dict()),
        (MACD, dict(period_me1=12, period_me2=26, period_signal=9)),
        # (Stochastic, dict(period=14)),
    ]

    results = collections.defaultdict(list)

    with concurrent.futures.ThreadPoolExecutor(max_workers=NUMBER_OF_WORKERS) as executor:

        future_to_rois = {executor.submit(backtest_strategies, strategies, 'EURUSD', 'H1', *interval): interval
                          for interval in rng_interval_generator
                          }

        for future in concurrent.futures.as_completed(future_to_rois):
            start_time, end_time = future_to_rois[future]
            rois = future.result()
            for (strategy, _), roi in zip(strategies, rois):
                print(f'{strategy.params.name} ROI (from {start_time} to {end_time}): {roi * 100:.2f} %.')

                results[strategy.params.name].append((start_time, roi))

    fig, ax = plt.subplots(len(strategies))

    for i, (strategy_name, result) in enumerate(results.items()):
        df = pd.DataFrame(result, columns=['date', 'roi'])
        df.set_index('date', inplace=True)

        df = df.groupby(pd.Grouper(freq='MS')).mean().fillna(0)

        mpl_date = mdates.date2num(df.index)
        roi = df['roi']

        bar_color = ['green' if value >= 0 else 'red' for value in roi]

        ax[i].bar(mpl_date, roi, alpha=0.5, color=bar_color, width=28)
        ax[i].plot(mpl_date, roi)

        ax[i].xaxis.set_major_locator(mdates.YearLocator())
        ax[i].xaxis.set_major_formatter(mdates.DateFormatter('%Y'))

        ax[i].xaxis.set_tick_params(rotation=0)

        ax[i].set_ylabel('ROI')
        ax[i].set_xlabel('Year')

        ax[i].set_title(f'Radom Trade using {strategy_name} (from {total_datetime_interval[0].date()} to {total_datetime_interval[1].date()}, period: {duration.days})')

    plt.show()


def parse_args():
    parser = argparse.ArgumentParser(description='Random Trading')

    parser.add_argument('--symbol', '-s', choices=SYMBOLS,
                        default='EURUSD', required=False,
                        help='symbols to be traded.')

    parser.add_argument('--period', '-p', choices=PERIODS.keys(),
                        default='D1', required=False,
                        help='timeframe period to be traded.')

    return parser.parse_args()


if __name__ == '__main__':
    args = parse_args()
    main()
