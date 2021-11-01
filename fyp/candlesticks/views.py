from django.db.models import F, Func, Value, CharField
from django.http import HttpResponse, Http404, StreamingHttpResponse
from django.shortcuts import redirect
from django.template import loader
from django.urls import get_script_prefix
from rest_framework import viewsets


from .forms import HistoryForm, SMACrossoverForm
from .models import Candlestick
from .serializers import CandlestickSerializer

from utils.commissions import ForexCommission
from utils.constants import *
from utils.psql import PSQLData
from utils.strategies import BuyAndHold, MovingAveragesCrossover

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
                                                    'price_type': 'BID',
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
                price_type = history_form.cleaned_data['price_type']
                source = history_form.cleaned_data['source']

                # estimate maximum of allowed date_before
                maximum_date_before = bar_number_limiter(date_from, date_before, period)

                # save submitted form into session
                request.session['saved_history_form'] = json.dumps(history_form.cleaned_data, default=str)

                # filter result based on limited date_before
                query_results = Candlestick.objects.filter(symbol__exact=symbol,
                                                           period__exact=period,
                                                           source__exact=source,
                                                           price_type__exact=price_type,
                                                           time__range=(date_from, maximum_date_before),
                                                           volume__gt=0,
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
                                                           'source': request.POST['source'],
                                                           'price_type': request.POST['price_type'],
                                                           }
                                                  )

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
                    price_type = saved_history_form.cleaned_data['price_type']
                    source = saved_history_form.cleaned_data['source']

                    query_results = Candlestick.objects.filter(symbol__exact=symbol,
                                                               period__exact=period,
                                                               source__exact=source,
                                                               price_type__exact=price_type,
                                                               time__range=(date_from, date_before),
                                                               volume__gt=0,
                                                               )

                    # if there is result, generate the csv file from streaming
                    if query_results:

                        readable_period = query_results[0].get_period_display()
                        filename = f'{symbol}_from_{date_from.strftime("%Y%m%d")}_to_{date_before.strftime("%Y%m%d")}_{readable_period}_{price_type}'

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
                    price_type = saved_history_form.cleaned_data['price_type']

                    query_results = Candlestick.objects.filter(time__range=(date_from, date_before),
                                                               symbol__exact=symbol,
                                                               period__exact=period,
                                                               source__exact=source,
                                                               price_type__exact=price_type,
                                                               volume__gt=0,
                                                               ).order_by()
                    if query_results:
                        context['query_results'] = query_results
                        # backtest
                        period, timeframe, compression, = next(((key, value[1], value[2]) for key, value in PERIODS.items() if value[0] == period), PERIODS['H1'])

                        cerebro = bt.Cerebro()
                        # cerebro.addstrategy(BuyAndHold)
                        cerebro.addstrategy(MovingAveragesCrossover, print_log=True, fast_ma_period=sma_crossover_fast_ma_period, slow_ma_period=sma_crossover_slow_ma_period)
                        data = PSQLData(symbol=symbol,
                                        period=period,
                                        timeframe=timeframe,
                                        compression=compression,
                                        fromdate=date_from,
                                        todate=date_before)
                        cerebro.adddata(data, name='test')
                        cash = 200000.0
                        cerebro.broker.setcash(cash)
                        leverage = 1
                        margin = cash / leverage
                        cerebro.broker.addcommissioninfo(ForexCommission(leverage=leverage, margin=margin))
                        print('Starting Portfolio Value: %.5f' % cerebro.broker.getvalue())
                        cerebro.run(runonce=False)
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
