#!/home/paullam/auto_forex_trading_project/venv/bin/python3
import django
import os
import sys
# Connect to existing Django Datebase
sys.path.append('/home/paullam/auto_forex_trading_project/auto_forex_trading_project/')
os.environ['DJANGO_SETTINGS_MODULE'] = 'forex.settings.local'
django.setup()

from candlesticks.models import Candlestick
from datetime import date, datetime, timedelta
from calendar import monthrange
import pandas as pd

# PERIODS = [0, 1, 5, 15, 30, 60, 240, 1440]
PERIODS = [0, 1, 5, 15, 30, 60, 240, 1440, 10080, 43200]

SYMBOL = 'EURUSD'
PRICE_TYPE = 'BID'
SOURCE = 'Dukascopy'

# default date range
START_DATE = date(2003, 5, 4)
END_DATE = date.today()


def daterange(start_date, end_date):
    # date generator
    for n in range(int((end_date - start_date).days)):
        yield start_date + timedelta(n)


def get_start_and_end_time_of_date(date):
    # return start time and end time of given date
    # it is expected that they are 00:00:00 and 23:59:59.999999 of given date
    time_from = datetime.combine(date, datetime.min.time())
    time_before = time_from + timedelta(days=1, microseconds=-1)
    return time_from, time_before


def get_start_and_end_time_of_week(date):
    # given a date in a week, return starting and ending time of the week
    time_from = datetime.combine(date, datetime.min.time()) + timedelta(days=-(date.isoweekday() % 7))
    time_before = time_from + timedelta(days=7, microseconds=-1)
    return time_from, time_before


def get_start_and_end_time_of_month(date):
    # given a date in a month, return starting and ending time of the month
    time_from = datetime(date.year, date.month, 1)
    time_before = time_from + timedelta(days=monthrange(time_from.year, time_from.month)[1], microseconds=-1)
    return time_from, time_before


def one_minute_to_target_timeframe(date, target_period=5):
    if target_period < 5:
        return
    elif 5 <= target_period <= 1440:
        time_from, time_before = get_start_and_end_time_of_date(date)
    elif 1440 < target_period <= 10080:
        time_from, time_before = get_start_and_end_time_of_week(date)
    elif 10080 < target_period <= 43200:
        time_from, time_before = get_start_and_end_time_of_month(date)

    # find source period, which is previous period of target_period
    # it is expected bars with previous period already exist
    source_period = PERIODS[PERIODS.index(target_period) - 1]

    query_results = Candlestick.objects.filter(symbol__exact=SYMBOL,
                                               time__range=(time_from, time_before),
                                               period__exact=source_period,
                                               source__exact=SOURCE,
                                               price_type__exact=PRICE_TYPE,
                                               )

    # build pandas Dataframe from {query_results}
    if query_results:
        df = pd.DataFrame.from_records(data=query_results.values('high', 'low', 'open', 'close', 'volume'),
                                       index=query_results.values_list('time', flat=True),
                                       )
        # build candlestick with 5-minute timframe using resample
        df = df.resample(f'{target_period}T', closed='left', label='left').apply({'open': 'first',
                                                                                  'high': 'max',
                                                                                  'low': 'min',
                                                                                  'close': 'last',
                                                                                  'volume': 'sum'}
                                                                                 )

        # write to Django database
        for time, row in df.iterrows():
            time = time.to_pydatetime()
            Candlestick.objects.update_or_create(symbol=SYMBOL,
                                                 time=time,
                                                 period=target_period,
                                                 source=SOURCE,
                                                 price_type=PRICE_TYPE,
                                                 defaults={'symbol': SYMBOL,
                                                           'time': time,
                                                           'open': row['open'],
                                                           'high': row['high'],
                                                           'low': row['low'],
                                                           'close': row['close'],
                                                           'volume': row['volume'],
                                                           'period': target_period,
                                                           'source': SOURCE,
                                                           'price_type': PRICE_TYPE,
                                                           }
                                                 )


if __name__ == '__main__':
    for date in daterange(START_DATE, END_DATE):
        for period in PERIODS:
            one_minute_to_target_timeframe(date, target_period=period)
