from utils.commissions import ForexCommission
from utils.constants import *
from utils.psql import PSQLData
from utils.strategies import MovingAveragesCrossover

from utils.plotter import BacktraderPlottly

from celery import shared_task
from celery_progress.backend import ProgressRecorder

from datetime import datetime, date, timedelta
import os
import plotly.io
import tempfile
import time


@shared_task(bind=True)
def long_test(self, seconds):
    progress_recorder = ProgressRecorder(self)
    result = 0
    for i in range(seconds):
        time.sleep(1)
        result += i
        progress_recorder.set_progress(i + 1, seconds)
    return result


@shared_task(bind=True)
def celery_backtest(self, symbol, fromdate, todate, period, strategy, **parameters):

    fromdate = datetime.strptime(fromdate, '%Y-%m-%dT%H:%M:%S')
    todate = datetime.strptime(todate, '%Y-%m-%dT%H:%M:%S.%f')

    period, timeframe, compression, = next(((key, value[1], value[2]) for key, value in PERIODS.items() if value[0] == period), PERIODS['H1'])

    cerebro = bt.Cerebro()

    cash = 200000
    leverage = 1
    margin = cash / leverage
    # strategy = getattr(self, strategy)

    data = PSQLData(symbol=symbol,
                    period=period,
                    timeframe=timeframe,
                    compression=compression,
                    fromdate=fromdate,
                    todate=todate)

    progress_recorder = ProgressRecorder(self)
    progress_recorder.set_progress(0, len(data))

    cerebro.broker.setcash(cash)
    cerebro.broker.addcommissioninfo(ForexCommission(leverage=leverage, margin=margin))
    cerebro.adddata(data, name=symbol)

    cerebro.addanalyzer(bt.analyzers.DrawDown)
    cerebro.addanalyzer(bt.analyzers.Returns)
    cerebro.addanalyzer(bt.analyzers.SharpeRatio)
    cerebro.addanalyzer(bt.analyzers.TradeAnalyzer)
    cerebro.addanalyzer(bt.analyzers.Transactions, headers=True)

    cerebro.addobserver(bt.observers.Broker)
    cerebro.addobserver(bt.observers.BuySell, barplot=True, bardist=0.0020)
    cerebro.addobserver(bt.observers.Trades, pnlcomm=True)

    cerebro.addstrategy(MovingAveragesCrossover, **parameters)
    print('Starting Portfolio Value: %.5f' % cerebro.broker.getvalue())
    res = cerebro.run(runonce=False, stdstats=False)
    print('Final Portfolio Value: %.5f' % cerebro.broker.getvalue())

    temp_dir = tempfile.gettempdir()
    temp_name = f'{next(tempfile._get_candidate_names())}.html'
    html_path = os.path.join(temp_dir, temp_name)
    figs = cerebro.plot(BacktraderPlottly())
    figs = [x for fig in figs for x in fig]  # flatten output
    html_boby = ''.join(plotly.io.to_html(figs[i], full_html=False) for i in range(len(figs)))
    return html_boby
