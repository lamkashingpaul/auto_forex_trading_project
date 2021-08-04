from django.db.models import F, Func, Value, CharField
from django.http import HttpResponse, Http404, StreamingHttpResponse
from django.shortcuts import redirect
from django.template import loader
from django.urls import get_script_prefix
from rest_framework import viewsets


from .forms import HistoryForm, SMACrossoverForm
from .models import Candlestick
from .serializers import CandlestickSerializer

from backtrader_plotting import Bokeh
from backtrader_plotting.schemes import Tradimo
from bs4 import BeautifulSoup
from datetime import date, timedelta

import backtrader as bt
import csv
import json
import os
import pandas as pd
import tempfile


# Create your views here.
limit_of_result = 10080  # number of M1 bars in a week


# file-like interface for large CSV file streaming
class Echo:
    """An object that implements just the write method of the file-like
    interface.
    """

    def write(self, value):
        """Write the value by returning it, instead of storing in a buffer."""
        return value


# ModelViewSet object for table pagination
class CandlestickViewSet(viewsets.ModelViewSet):
    queryset = Candlestick.objects.none()
    serializer_class = CandlestickSerializer


# estimate and limit number of query results by adjusting {date_before}
def bar_number_limiter(date_from, date_before, period):
    maximum_date_before = date_from + timedelta(minutes=period) * (limit_of_result - 1)

    if date_before > maximum_date_before:
        return maximum_date_before
    else:
        return date_before


# view for index
def index(request):
    script_prefix = get_script_prefix().rstrip('/')

    # view for index page
    template = loader.get_template('candlesticks/index.html')
    context = {'history_form': HistoryForm(initial={'symbol': 'EURUSD',
                                                    'date_from': (date.today() + timedelta(days=-1) + timedelta(days=-365)).strftime('%d/%m/%Y'),
                                                    'date_before': (date.today() + timedelta(days=-1)).strftime('%d/%m/%Y'),
                                                    'period': 1440,
                                                    'source': 'Dukascopy',
                                                    }
                                           ),
               'script_prefix': script_prefix,
               }

    if request.method == 'POST':
        # if user hits search button
        if 'search' in request.POST:
            history_form = HistoryForm(request.POST)
            if history_form.is_valid():
                # parse input parameters from submitted form
                symbol = history_form.cleaned_data['symbol']
                date_from = history_form.cleaned_data['date_from']
                date_before = history_form.cleaned_data['date_before']
                period = history_form.cleaned_data['period']
                source = history_form.cleaned_data['source']

                # estimate maximum of allowed date_before
                maximum_date_before = bar_number_limiter(date_from, date_before, period)

                # save submitted form into session
                request.session['saved_history_form'] = json.dumps(history_form.cleaned_data, default=str)

                # filter result based on limited date_before
                query_results = Candlestick.objects.filter(symbol__exact=symbol,
                                                           period__exact=period,
                                                           source__exact=source,
                                                           time__range=(date_from, maximum_date_before),
                                                           )

                if query_results:
                    # save query result into ModelViewSet for html rendering
                    CandlestickViewSet.queryset = query_results

                    context['number_of_bars'] = query_results.count()

                    # check if {query_results} is limited
                    if maximum_date_before < date_before:
                        context['limit_of_result'] = query_results.count()

                    # determine maximum decimal place for one pipette
                    if 'JPY' in symbol:
                        decimal_place = 3
                    else:
                        decimal_place = 5
                    context['decimal_place'] = decimal_place
                else:
                    CandlestickViewSet.queryset = Candlestick.objects.none()

            # update default form inputs in any case
            context['history_form'] = HistoryForm(initial={'symbol': request.POST['symbol'],
                                                           'date_from': request.POST['date_from'],
                                                           'date_before': request.POST['date_before'],
                                                           'period': request.POST['period'],
                                                           'source': request.POST['source'], })

            # return html page which contains datetable
            return HttpResponse(template.render(context, request))

        # else if user hits download button
        elif 'download_csv' in request.POST:

            # there must be a {saved_history_form} in session, o/w return 404 page
            if not request.session['saved_history_form'] or 'download_csv_token_value' not in request.POST:
                raise Http404('Session expired. Do the search again.')

            else:
                # parse {saved_history_form} from session
                saved_history_form = HistoryForm(json.loads(request.session['saved_history_form']))

                # verify parameters in case
                if saved_history_form.is_valid():
                    symbol = saved_history_form.cleaned_data['symbol']
                    date_from = saved_history_form.cleaned_data['date_from']
                    date_before = saved_history_form.cleaned_data['date_before']
                    period = saved_history_form.cleaned_data['period']
                    source = saved_history_form.cleaned_data['source']

                    query_results = Candlestick.objects.filter(time__range=(date_from, date_before),
                                                               symbol__exact=symbol,
                                                               period__exact=period,
                                                               source__exact=source,
                                                               )

                    # if there is result, generate the csv file from streaming
                    if query_results:

                        readable_period = query_results[0].get_period_display()
                        filename = f'{symbol}_from_{date_from.strftime("%Y%m%d")}_to_{date_before.strftime("%Y%m%d")}_{readable_period}'

                        # construst csv file
                        rows = [('Datetime', 'Open', 'High', 'Low', 'Close', 'Volume(Millions)')]  # header row

                        # add datetime string by annotating
                        query_results = query_results.annotate(formatted_time=Func(F('time'),
                                                                                   Value('YYYY-MM-DD HH24:MI:SS'),
                                                                                   function='to_char',
                                                                                   output_field=CharField()
                                                                                   )
                                                               )

                        rows += list(query_results.values_list('formatted_time', 'open', 'high', 'low', 'close', 'volume'))

                        pseudo_buffer = Echo()
                        writer = csv.writer(pseudo_buffer)

                        streaming_response = StreamingHttpResponse((writer.writerow(row) for row in rows),
                                                                   content_type='text/csv',
                                                                   headers={'Content-Disposition': f'attachment; filename="{filename}.csv"'}
                                                                   )

                        # add cookies to response
                        streaming_response.set_cookie('download_csv_token_value', request.POST['download_csv_token_value'])
                        return streaming_response

    # return default home page for any get request
    return HttpResponse(template.render(context, request))


# view for backtest
def backtest(request):
    template = loader.get_template('backtest/index.html')
    context = {}

    if request.method == 'POST':
        if 'sma_crossover' in request.POST:
            sma_crossover_form = SMACrossoverForm(request.POST)
            if sma_crossover_form.is_valid():
                request.session['saved_sma_crossover_form'] = json.dumps(sma_crossover_form.cleaned_data, default=str)
                sma_crossover_fast_ma_period = sma_crossover_form.cleaned_data['sma_crossover_fast_ma_period']
                sma_crossover_slow_ma_period = sma_crossover_form.cleaned_data['sma_crossover_slow_ma_period']
                context['sma_crossover_fast_ma_period'] = sma_crossover_fast_ma_period
                context['sma_crossover_slow_ma_period'] = sma_crossover_slow_ma_period

                saved_history_form = HistoryForm(json.loads(request.session['saved_history_form']))
                if saved_history_form.is_valid():

                    symbol = saved_history_form.cleaned_data['symbol']
                    date_from = saved_history_form.cleaned_data['date_from']
                    date_before = saved_history_form.cleaned_data['date_before']
                    period = saved_history_form.cleaned_data['period']
                    source = saved_history_form.cleaned_data['source']

                    query_results = Candlestick.objects.filter(time__range=(date_from, date_before),
                                                               symbol__exact=symbol,
                                                               period__exact=period,
                                                               source__exact=source,
                                                               volume__gt=0,
                                                               ).order_by()
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
