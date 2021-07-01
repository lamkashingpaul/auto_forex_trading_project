#!/home/paullam/fyp/fypenv/bin/python3
import django
import os
import sys

# Connect to existing Django Datebase
sys.path.append('/home/paullam/fyp/fyp/')
os.environ['DJANGO_SETTINGS_MODULE'] = 'fyp.settings'
django.setup()

from candlesticks.models import Candlestick
from datetime import datetime, date, timedelta
from pathlib import Path
from multiprocessing.dummy import Pool
import requests
import time
import lzma
import struct

DATA_ROOT = '/home/paullam/fyp/data'
SYMBOL = 'EURUSD'
PRICE_TYPE = 'BID'  # or 'ASK'
NUMBER_OF_WORKERS = 4
SOURCE = 'Dukascopy'

# default date range
START_DATE = date(2003, 5, 4)
END_DATE = (date.today() - timedelta(days=1))


def daterange(start_date, end_date):
    # date generator
    for n in range(int((end_date - start_date).days)):
        yield start_date + timedelta(n)


def add_minute_bar_to_django(path):
    period = 1  # by default bar timeframe is M1
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
    time.sleep(1)
    year, month, day = date.isoformat().split('-')

    save_dir = os.path.join(DATA_ROOT, SYMBOL, year, PRICE_TYPE)
    save_filename = f'{month}_{day}.bi5'
    Path(save_dir).mkdir(parents=True, exist_ok=True)

    month = f'{int(month) - 1:02d}'  # Month in Dukascopy starts from 00 to 11
    r = requests.get(f'https://datafeed.dukascopy.com/datafeed/{SYMBOL}/{year}/{month}/{day}/{PRICE_TYPE}_candles_min_1.bi5')

    if r.status_code == 200:
        save_path = os.path.join(save_dir, save_filename)
        if not os.path.isfile(save_path):
            with open(save_path, 'wb') as f:
                f.write(r.content)
        return save_path


if __name__ == '__main__':
    pathlist = []
    START_DATE = (date.today() - timedelta(days=8))
    END_DATE = (date.today() - timedelta(days=1))
    pool = Pool(NUMBER_OF_WORKERS)

    for i, save_path in enumerate(pool.imap_unordered(get_candlestick, daterange(START_DATE, END_DATE))):
        pathlist.append(Path(save_path))

    for i, minute_bars in enumerate(pool.imap_unordered(add_minute_bar_to_django, pathlist)):
        for minute_bar in minute_bars:
            symbol, time, open, close, low, high, volume, period, price_type = minute_bar
            Candlestick.objects.update_or_create(symbol=symbol,
                                                 time=time,
                                                 period=period,
                                                 price_type=price_type,
                                                 source=SOURCE,
                                                 defaults={'symbol': symbol,
                                                           'time': time,
                                                           'open': open / 10 ** 5,
                                                           'high': high / 10 ** 5,
                                                           'low': low / 10 ** 5,
                                                           'close': close / 10 ** 5,
                                                           'volume': volume,
                                                           'period': period,
                                                           'source': SOURCE,
                                                           }
                                                 )
