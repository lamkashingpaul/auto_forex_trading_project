#!/home/paullam/fyp/venv/bin/python3
import django
import os
import sys

# Connect to existing Django Datebase
sys.path.append('/home/paullam/fyp/fyp/')
os.environ['DJANGO_SETTINGS_MODULE'] = 'fyp.settings'
django.setup()

from calendar import monthrange
from candlesticks.models import Candlestick
from datetime import datetime, date, timedelta
from pathlib import Path
import concurrent.futures
import lzma
import pandas as pd
import random
import requests
import struct
import time

# lookup variables
PERIODS = [0, 1, 5, 15, 30, 60, 240, 1440, 10080, 43200]

# default parameters for data source
DATA_ROOT = '/home/paullam/fyp/data'
SYMBOLS = [
    'EURUSD', 'USDJPY', 'GBPUSD', 'AUDUSD', 'USDCAD', 'USDCHF', 'NZDUSD',
    'EURJPY', 'GBPJPY', 'EURGBP', 'AUDJPY', 'EURAUD', 'EURCHF', 'AUDNZD',
    'NZDJPY', 'GBPAUD', 'GBPCAD', 'EURNZD', 'AUDCAD', 'GBPCHF', 'AUDCHF',
    'EURCAD', 'CADJPY', 'GBPNZD', 'CADCHF', 'CHFJPY', 'NZDCAD', 'NZDCHF',
]
PRICE_TYPES = ['BID']  # or 'ASK'
NUMBER_OF_WORKERS = 16
SOURCE = 'Dukascopy'

# default date range
START_DATE = date.today() - timedelta(days=7)
END_DATE = date.today()


def date_xrange(start_date, end_date):
    # date generator
    for n in range(int((end_date - start_date).days)):
        yield start_date + timedelta(n)


def get_start_and_end_time_of_date(date):
    # return starting and ending time of given date
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


def get_minute_bars_from_bi5_candlestick(date):
    for price_type in PRICE_TYPES:
        for symbol in SYMBOLS:
            year, month, day = date.isoformat().split('-')

            save_dir = os.path.join(DATA_ROOT, symbol, year, price_type)
            save_filename = f'{month}_{day}.bi5'
            Path(save_dir).mkdir(parents=True, exist_ok=True)
            save_path = os.path.join(save_dir, save_filename)

            # try to get bi5 file from source
            if not os.path.isfile(save_path):
                dukascopy_month = f'{int(month) - 1:02d}'  # Month in Dukascopy starts from 00 to 11
                time.sleep(random.uniform(1, 3))
                r = requests.get(f'https://datafeed.dukascopy.com/datafeed/{symbol}/{year}/{dukascopy_month}/{day}/{price_type}_candles_min_1.bi5')

                if r.status_code == 200:
                    with open(save_path, 'wb') as f:
                        f.write(r.content)

            if os.path.isfile(save_path):
                period = 1  # minute bars are expected
                if 'JPY' in symbol:
                    pipette_to_price_ratio = 10 ** 3
                else:
                    pipette_to_price_ratio = 10 ** 5

                start_datetime = datetime(int(year), int(month), int(day), 0, 0, 0, 0)
                with lzma.open(save_path, format=lzma.FORMAT_AUTO, filters=None) as f:
                    decompresseddata = f.read()

                for i in range(int(len(decompresseddata) / 24)):
                    time_shift, open_price, close, low, high, volume = struct.unpack('!5if', decompresseddata[i * 24: (i + 1) * 24])
                    bar_time = start_datetime + timedelta(seconds=time_shift)

                    write_to_psql(symbol, bar_time, period, SOURCE, price_type,
                                  open_price / pipette_to_price_ratio,
                                  close / pipette_to_price_ratio,
                                  low / pipette_to_price_ratio,
                                  high / pipette_to_price_ratio,
                                  volume)


def one_minute_to_target_timeframe(price_type, symbol, target_period, date):
    # find source period, which is previous period of target_period
    # it is expected bars with previous period already exist
    source_period = PERIODS[PERIODS.index(target_period) - 1]
    resample_rate = target_period

    if target_period < 5:
        return
    elif 5 <= target_period <= 1440:
        time_from, time_before = get_start_and_end_time_of_date(date)
    elif 1440 < target_period <= 10080:
        time_from, time_before = get_start_and_end_time_of_week(date)
    elif 10080 < target_period <= 43200:
        time_from, time_before = get_start_and_end_time_of_month(date)
        source_period = 1440  # use D1 bars
        resample_rate = 44640  # at least 44640 minutes which is equal to 31 days

    query_results = Candlestick.objects.filter(symbol__exact=symbol,
                                               period__exact=source_period,
                                               price_type__exact=price_type,
                                               source__exact=SOURCE,
                                               time__range=(time_from, time_before),
                                               )

    # build pandas Dataframe from {query_results}
    if query_results:
        df = pd.DataFrame.from_records(data=query_results.values('high', 'low', 'open', 'close', 'volume'),
                                       index=query_results.values_list('time', flat=True),
                                       )
        # build candlestick with 5-minute timframe using resample
        df = df.resample(f'{resample_rate}T', closed='left', label='left').apply({'open': 'first',
                                                                                  'high': 'max',
                                                                                  'low': 'min',
                                                                                  'close': 'last',
                                                                                  'volume': 'sum'}
                                                                                 )
        # write to Django database
        for bar_time, row in df.iterrows():
            bar_time = bar_time.to_pydatetime()
            write_to_psql(symbol, bar_time, target_period, SOURCE, price_type,
                          row['open'],
                          row['high'],
                          row['low'],
                          row['close'],
                          row['volume'])


def write_to_psql(symbol, bar_time, period, source, price_type, open_price, high, low, close, volume):
    Candlestick.objects.update_or_create(symbol=symbol,
                                         time=bar_time,
                                         period=period,
                                         source=source,
                                         price_type=price_type,
                                         defaults={'symbol': symbol,
                                                   'time': bar_time,
                                                   'open': open_price,
                                                   'high': high,
                                                   'low': low,
                                                   'close': close,
                                                   'volume': volume,
                                                   'period': period,
                                                   'source': SOURCE,
                                                   'price_type': price_type,
                                                   }
                                         )


if __name__ == '__main__':
    # collect all paths of bi5 files
    with concurrent.futures.ThreadPoolExecutor(max_workers=NUMBER_OF_WORKERS) as executor:
        future_to_path = {executor.submit(get_minute_bars_from_bi5_candlestick, date): date for date in date_xrange(START_DATE, END_DATE)}
        for future in concurrent.futures.as_completed(future_to_path):
            pass

    for price_type in PRICE_TYPES:
        for symbol in SYMBOLS:
            for period in (5, 15, 30, 60, 240, 1440, 10080, 43200):
                with concurrent.futures.ThreadPoolExecutor(max_workers=NUMBER_OF_WORKERS) as executor:
                    future_to_long_bars = {executor.submit(one_minute_to_target_timeframe, price_type, symbol, period, date): date for date in date_xrange(START_DATE, END_DATE)}
                    for future in concurrent.futures.as_completed(future_to_long_bars):
                        pass
