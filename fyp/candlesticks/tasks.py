from utils.commissions import ForexCommission
from utils.constants import *
from utils.psql import PSQLData
from utils.strategies import MovingAveragesCrossover
from utils.optimizations import Optimizer, CeleryCerebro
from utils.testcases import sma_testcase_generator

from utils.plotter import BacktraderPlottly

from celery import shared_task
from celery_progress.backend import ProgressRecorder

from datetime import datetime, date, timedelta
import plotly.io


@shared_task(bind=True)
def celery_backtest(self, symbol, fromdate, todate, period, strategy, optimization=False, **parameters):

    fromdate = datetime.strptime(fromdate, '%Y-%m-%dT%H:%M:%S')
    todate = datetime.strptime(todate, '%Y-%m-%dT%H:%M:%S.%f')

    period, timeframe, compression, = next(((key, value[1], value[2]) for key, value in PERIODS.items() if value[0] == period), PERIODS['H1'])

    cerebro = CeleryCerebro()

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

    # progress_recorder = ProgressRecorder(self)
    # progress_recorder.set_progress(0, len(data))

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

    if not optimization:
        cerebro.addstrategy(MovingAveragesCrossover, **parameters)
        cerebro.run(runonce=False, stdstats=False)

        figs = cerebro.plot(BacktraderPlottly())
        figs = [x for fig in figs for x in fig]  # flatten 2d list
        html_boby = ''.join(plotly.io.to_html(figs[i], full_html=False) for i in range(len(figs)))
        return html_boby

    else:
        optimizer = Optimizer(celery=self,
                              cerebro=cerebro,
                              strategy=MovingAveragesCrossover,
                              generator=sma_testcase_generator,
                              **parameters,
                              )
        optimizer.start()

        df = optimizer.strats_df
        return df.to_json()
