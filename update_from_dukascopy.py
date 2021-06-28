#!/home/paullam/fyp/fypenv/bin/python3
import os
import requests
import time
from datetime import date, timedelta
from pathlib import Path
from multiprocessing.dummy import Pool


DATA_ROOT = '/home/paullam/fyp/data'
SYMBOL = 'EURUSD'
PRICE_TYPE = 'BID'  # or 'ASK'
NUMBER_OF_WORKERS = 4


def daterange(start_date, end_date):
    # date generator
    for n in range(int((end_date - start_date).days)):
        yield start_date + timedelta(n)


def get_candlestick(date):
    time.sleep(1)
    year, month, day = date.isoformat().split('-')

    save_dir = os.path.join(DATA_ROOT, SYMBOL, year)
    save_filename = f'{month}_{day}.bi5'
    Path(save_dir).mkdir(parents=True, exist_ok=True)

    month = f'{int(month) - 1:02d}'  # Month in Dukascopy starts from 0 to 11
    r = requests.get(f'https://datafeed.dukascopy.com/datafeed/{SYMBOL}/{year}/{month}/{day}/{PRICE_TYPE}_candles_min_1.bi5')

    if r.status_code == 200:
        save_path = os.path.join(save_dir, save_filename)
        if not os.path.isfile(save_path):
            with open(save_path, 'wb') as f:
                f.write(r.content)


if __name__ == '__main__':
    start_date = date(2021, 1, 1)
    end_date = (date.today() - timedelta(days=1))
    pool = Pool(NUMBER_OF_WORKERS)

    for i in enumerate(pool.imap_unordered(get_candlestick, daterange(start_date, end_date))):
        pass
