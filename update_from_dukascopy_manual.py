#!/home/paullam/fyp/fypenv/bin/python3
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
from multiprocessing.dummy import Pool
import lzma
import pandas as pd
import requests
import struct
import time

# lookup variables
PERIODS = [0, 1, 5, 15, 30, 60, 240, 1440, 10080, 43200]

# default parameters for data source
DATA_ROOT = '/home/paullam/fyp/data'
SYMBOLS = ['USDJPY']
PRICE_TYPES = ['BID']  # or 'ASK'
NUMBER_OF_WORKERS = 4
SOURCE = 'Dukascopy'

# default date range
START_DATE = date(2003, 5, 1)
END_DATE = date(2003, 6, 1)


def daterange(start_date, end_date):
    # date generator
    for n in range(int((end_date - start_date).days)):
        yield start_date + timedelta(n)


def add_minute_bar_to_django(path):
    '''
    Each bi5 file from Dukascopy provides 1440 1-minute bars
    Binary file is decompressed and all bars' details are extracted and returned
    '''
    period = 1
    minute_bars = []
    symbol, year, price_type, date = path.parts[-4:]
    month, day = os.path.splitext(date)[0].split('_')
    start_datetime = datetime(int(year), int(month), int(day), 0, 0, 0, 0)
    with lzma.open(path, format=lzma.FORMAT_AUTO, filters=None) as f:
        decompresseddata = f.read()

    for i in range(0, int(len(decompresseddata) / 24)):
        time_shift, open, close, low, high, volume = struct.unpack('!5if', decompresseddata[i * 24: (i + 1) * 24])
        time = start_datetime + timedelta(seconds=time_shift)
        minute_bars.append((symbol, time, open, close, low, high, volume, period, price_type))

    return minute_bars


def get_candlestick(date):
    save_paths = []

    for symbol in SYMBOLS:
        for price_type in PRICE_TYPES:
            time.sleep(1)
            year, month, day = date.isoformat().split('-')

            save_dir = os.path.join(DATA_ROOT, symbol, year, price_type)
            save_filename = f'{month}_{day}.bi5'
            Path(save_dir).mkdir(parents=True, exist_ok=True)

            month = f'{int(month) - 1:02d}'  # Month in Dukascopy starts from 00 to 11
            r = requests.get(f'https://datafeed.dukascopy.com/datafeed/{symbol}/{year}/{month}/{day}/{price_type}_candles_min_1.bi5')

            if r.status_code == 200:
                save_path = os.path.join(save_dir, save_filename)
                if not os.path.isfile(save_path):
                    with open(save_path, 'wb') as f:
                        f.write(r.content)
                save_paths.append(Path(save_path))

    return save_paths


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


def one_minute_to_target_timeframe(symbol, date, price_type, target_period=5):
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
        resample_rate = 44640  # at least 44640 minutes which to equal to 31 days

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
        for time, row in df.iterrows():
            time = time.to_pydatetime()
            Candlestick.objects.update_or_create(symbol=symbol,
                                                 time=time,
                                                 period=target_period,
                                                 source=SOURCE,
                                                 price_type=price_type,
                                                 defaults={'symbol': symbol,
                                                           'time': time,
                                                           'open': row['open'],
                                                           'high': row['high'],
                                                           'low': row['low'],
                                                           'close': row['close'],
                                                           'volume': row['volume'],
                                                           'period': target_period,
                                                           'source': SOURCE,
                                                           'price_type': price_type,
                                                           }
                                                 )


if __name__ == '__main__':
    pathlist = []
    pool = Pool(NUMBER_OF_WORKERS)

    # retrieve bi5 files from Dukascopy
    for i, save_paths in enumerate(pool.imap_unordered(get_candlestick, daterange(START_DATE, END_DATE))):
        pathlist.extend(save_paths)

    # decompress and read bi5 files, then write data into Django database
    for i, minute_bars in enumerate(pool.imap_unordered(add_minute_bar_to_django, pathlist)):
        for minute_bar in minute_bars:
            symbol, time, open, close, low, high, volume, period, price_type = minute_bar
            if 'JPY' in symbol:
                pipette_to_price_ratio = 10 ** 3
            else:
                pipette_to_price_ratio = 10 ** 5

            # write bar data into Django database
            Candlestick.objects.update_or_create(symbol=symbol,
                                                 time=time,
                                                 period=period,
                                                 source=SOURCE,
                                                 price_type=price_type,
                                                 defaults={'symbol': symbol,
                                                           'time': time,
                                                           'open': open / pipette_to_price_ratio,
                                                           'high': high / pipette_to_price_ratio,
                                                           'low': low / pipette_to_price_ratio,
                                                           'close': close / pipette_to_price_ratio,
                                                           'volume': volume,
                                                           'period': period,
                                                           'source': SOURCE,
                                                           'price_type': price_type,
                                                           }
                                                 )

    # given 1-minute bars, other bars with longer timeframes can be resampled
    for period in (5, 15, 30, 60, 240, 1440, 10080, 43200):
        for symbol in SYMBOLS:
            for price_type in PRICE_TYPES:
                for date in daterange(START_DATE, END_DATE):
                    one_minute_to_target_timeframe(symbol, date, price_type, target_period=period)
