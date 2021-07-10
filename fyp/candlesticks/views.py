from django.http import HttpResponse
from django.shortcuts import redirect
from django.shortcuts import render
from django.template import loader

from .forms import HistoryForm, MACDForm
from .models import Candlestick

import base64
import json
import os
import pandas as pd
import backtrader as bt
import tempfile

from backtrader_plotting import Bokeh
from backtrader_plotting.schemes import Tradimo
from bs4 import BeautifulSoup
from datetime import date, timedelta


# Create your views here.
limit_of_result = 87600


def index(request):
    # view for index page
    template = loader.get_template('candlesticks/index.html')
    context = {'history_form': HistoryForm(initial={'symbol': 'EURUSD',
                                                    'date_from': (date.today() + timedelta(days=-365)).strftime('%d/%m/%Y'),
                                                    'date_before': date.today().strftime('%d/%m/%Y'),
                                                    'period': 1440,
                                                    'source': 'Dukascopy',
                                                    }
                                           )
               }

    if request.method == 'POST':
        history_form = HistoryForm(request.POST)
        if history_form.is_valid():
            request.session['saved_history_form'] = json.dumps(history_form.cleaned_data, default=str)

            symbol = history_form.cleaned_data['symbol']
            date_from = history_form.cleaned_data['date_from']
            date_before = history_form.cleaned_data['date_before']
            period = history_form.cleaned_data['period']
            source = history_form.cleaned_data['source']

            # slice of query results which has at most {limit_of_result} rows
            query_results = Candlestick.objects.filter(symbol__exact=symbol,
                                                       period__exact=period,
                                                       source__exact=source,
                                                       time__range=(date_from, date_before),
                                                       volume__gt=0,
                                                       )[:limit_of_result]

            if query_results:
                expected_last_query_results = Candlestick.objects.filter(symbol__exact=symbol,
                                                                         period__exact=period,
                                                                         source__exact=source,
                                                                         time__range=(date_from, date_before),
                                                                         volume__gt=0,
                                                                         ).order_by('-id')[:1].first()

                context['query_results'] = query_results
                context['number_of_bars'] = query_results.count()

                # check if {query_results} is sliced
                if query_results[query_results.count() - 1] != expected_last_query_results:
                    context['limit_of_result'] = limit_of_result

                # determine maximum decimal place for one pipette
                if 'JPY' in symbol:
                    decimal_place = 3
                else:
                    decimal_place = 5
                context['decimal_place'] = decimal_place

        context['history_form'] = HistoryForm(initial={'symbol': request.POST['symbol'],
                                                       'date_from': request.POST['date_from'],
                                                       'date_before': request.POST['date_before'],
                                                       'period': request.POST['period'],
                                                       'source': request.POST['source'],
                                                       }
                                              )

    return HttpResponse(template.render(context, request))


def backtest(request):
    template = loader.get_template('backtest/index.html')
    context = {}

    if request.method == 'POST':
        if 'macd' in request.POST:
            macd_form = MACDForm(request.POST)
            if macd_form.is_valid():
                request.session['saved_macd_form'] = json.dumps(macd_form.cleaned_data, default=str)
                macd_fast_ma_period = macd_form.cleaned_data['macd_fast_ma_period']
                macd_slow_ma_period = macd_form.cleaned_data['macd_slow_ma_period']
                context['macd_fast_ma_period'] = macd_fast_ma_period
                context['macd_slow_ma_period'] = macd_slow_ma_period

                saved_history_form = HistoryForm(json.loads(request.session['saved_history_form']))
                if saved_history_form.is_valid():

                    symbol = saved_history_form.cleaned_data['symbol']
                    date_from = saved_history_form.cleaned_data['date_from']
                    date_before = saved_history_form.cleaned_data['date_before']
                    period = saved_history_form.cleaned_data['period']
                    source = saved_history_form.cleaned_data['source']

                    query_results = Candlestick.objects.filter(symbol__exact=symbol,
                                                               period__exact=period,
                                                               source__exact=source,
                                                               time__range=(date_from, date_before),
                                                               volume__gt=0,
                                                               )[:limit_of_result]
                    if query_results:
                        context['query_results'] = query_results
                        df = pd.DataFrame.from_records(data=query_results.values('high', 'low', 'open', 'close', 'volume'),
                                                       index=query_results.values_list('time', flat=True)
                                                       )

                        # define Strategy
                        class TestStrategy(bt.Strategy):
                            params = (
                                ('exitbars', 5),
                            )

                            def log(self, txt, dt=None):
                                ''' Logging function fot this strategy'''
                                dt = dt or self.datas[0].datetime.date(0)
                                print('%s, %s' % (dt.isoformat(), txt))

                            def __init__(self):
                                # Keep a reference to the "close" line in the data[0] dataseries
                                self.dataclose = self.datas[0].close

                                # To keep track of pending orders and buy price/commission
                                self.order = None
                                self.buyprice = None
                                self.buycomm = None

                            def notify_order(self, order):
                                if order.status in [order.Submitted, order.Accepted]:
                                    # Buy/Sell order submitted/accepted to/by broker - Nothing to do
                                    return
                                # Check if an order has been completed
                                # Attention: broker could reject order if not enough cash
                                if order.status in [order.Completed]:
                                    if order.isbuy():
                                        self.log(
                                            'BUY EXECUTED, Price: %.5f, Cost: %.5f, Comm %.5f' %
                                            (order.executed.price,
                                             order.executed.value,
                                             order.executed.comm))

                                        self.buyprice = order.executed.price
                                        self.buycomm = order.executed.comm
                                    else:  # Sell
                                        self.log('SELL EXECUTED, Price: %.5f, Cost: %.5f, Comm %.5f' %
                                                 (order.executed.price,
                                                  order.executed.value,
                                                  order.executed.comm))
                                    self.bar_executed = len(self)
                                elif order.status in [order.Canceled, order.Margin, order.Rejected]:
                                    self.log('Order Canceled/Margin/Rejected')
                                self.order = None

                            def notify_trade(self, trade):
                                if not trade.isclosed:
                                    return
                                self.log('OPERATION PROFIT, GROSS %.5f, NET %.5f' %
                                         (trade.pnl, trade.pnlcomm))

                            def next(self):
                                # Simply log the closing price of the series from the reference
                                self.log('Close, %.5f' % self.dataclose[0])
                                # Check if an order is pending ... if yes, we cannot send a 2nd one
                                if self.order:
                                    return
                                # Check if we are in the market
                                if not self.position:
                                    # Not yet ... we MIGHT BUY if ...
                                    if self.dataclose[0] < self.dataclose[-1]:
                                        # current close less than previous close
                                        if self.dataclose[-1] < self.dataclose[-2]:
                                            # previous close less than the previous close

                                            # BUY, BUY, BUY!!! (with default parameters)
                                            self.log('BUY CREATE, %.5f' % self.dataclose[0])

                                            # Keep track of the created order to avoid a 2nd order
                                            self.order = self.buy()
                                else:
                                    # Already in the market ... we might sell
                                    if len(self) >= (self.bar_executed + self.params.exitbars):
                                        # SELL, SELL, SELL!!! (with all possible default parameters)
                                        self.log('SELL CREATE, %.5f' % self.dataclose[0])

                                        # Keep track of the created order to avoid a 2nd order
                                        self.order = self.sell()

                        # backtest
                        cerebro = bt.Cerebro()
                        cerebro.addstrategy(TestStrategy)
                        data = bt.feeds.PandasData(dataname=df)
                        cerebro.adddata(data, name='test')
                        cerebro.broker.setcash(100000.0)
                        cerebro.broker.setcommission(commission=0.001)
                        print('Starting Portfolio Value: %.5f' % cerebro.broker.getvalue())
                        cerebro.run()
                        print('Final Portfolio Value: %.5f' % cerebro.broker.getvalue())

                        temp_dir = tempfile.gettempdir()
                        temp_name = f'{next(tempfile._get_candidate_names())}.html'
                        html_path = os.path.join(temp_dir, temp_name)
                        b = Bokeh(filename=html_path, style='bar', scheme=Tradimo(), output_mode='save', legend_text_color='#ff0000')
                        cerebro.plot(b)

                        with open(html_path) as f:
                            soup = BeautifulSoup(f, 'html.parser')
                            style = soup.find('style')
                            html_style = ''.join(['%s' % x for x in style.contents])

                            body = soup.find('body')
                            html_body = ''.join(['%s' % x for x in body.contents])

                            context['html_style'] = html_style
                            context['html_body'] = html_body

        return HttpResponse(template.render(context, request))

    else:
        return redirect('/')
