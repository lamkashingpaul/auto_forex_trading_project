from django.shortcuts import render
from django.http import HttpResponse
from django.template import loader
from django.shortcuts import redirect

from .models import Candlestick
from .forms import HistoryForm, MACDForm

from datetime import datetime
import json
import pandas as pd

from backtesting import Backtest, Strategy
from backtesting.lib import crossover

from backtesting.test import SMA, GOOG
from bs4 import BeautifulSoup


import tempfile

# Create your views here.
def index(request):
    template = loader.get_template('candlesticks/index.html')
    context = {'history_form': HistoryForm()}

    if request.method == 'POST':
        history_form = HistoryForm(request.POST)
        if history_form.is_valid():
            request.session['saved_history_form'] = json.dumps(history_form.cleaned_data, default=str)
            symbol = history_form.cleaned_data['symbol']
            start_time = history_form.cleaned_data['start_time']
            end_time = history_form.cleaned_data['end_time']
            query_results = Candlestick.objects.filter(symbol__contains=symbol, time__range=(start_time, end_time))
            context['history_form'] = HistoryForm(initial={'symbol': request.POST['symbol'], 'start_time': request.POST['start_time'], 'end_time': request.POST['end_time']})
            if query_results:
                context['query_results'] = query_results
                context['number_of_bars'] = len(query_results)

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
                    start_time = saved_history_form.cleaned_data['start_time']
                    end_time = saved_history_form.cleaned_data['end_time']
                    query_results = Candlestick.objects.filter(symbol__contains=symbol, time__range=(start_time, end_time))
                    if query_results:
                        context['query_results'] = query_results
                        times = query_results.values_list('time', flat=True)
                        index = [pd.to_datetime(time, origin='unix') for time in times]
                        df = pd.DataFrame.from_records(query_results.values('high', 'low', 'open', 'close'), index=index)
                        # df['time'].timestamp()
                        df.columns = ['High', 'Low', 'Open', 'Close']
                        class SmaCross(Strategy):
                            n1 = macd_fast_ma_period
                            n2 = macd_slow_ma_period

                            def init(self):
                                close = self.data.Close
                                self.sma1 = self.I(SMA, close, self.n1)
                                self.sma2 = self.I(SMA, close, self.n2)

                            def next(self):
                                if crossover(self.sma1, self.sma2):
                                    self.buy()
                                elif crossover(self.sma2, self.sma1):
                                    self.sell()

                        bt = Backtest(df, SmaCross,
                                      cash=10000, commission=.002,
                                      exclusive_orders=True)

                        temp_name = tempfile.mkstemp()[1]
                        output = bt.run()
                        context['output'] = str(output)
                        bt.plot(filename=f'{temp_name}_backtesttemp', open_browser=False)

                        with open(f'{temp_name}_backtesttemp.html') as f:
                            soup = BeautifulSoup(f, 'html.parser')
                            body = soup.find('body')
                            plot = ''.join(['%s' % x for x in body.contents])
                            context['plot'] = plot

        return HttpResponse(template.render(context, request))

    else:
        return redirect('/')
