#!/home/paullam/fyp/fypenv/bin/python3
import sys
import os
import django

# Connect to existing Django Datebase
sys.path.append('/home/paullam/fyp/fyp/')
os.environ['DJANGO_SETTINGS_MODULE'] = 'fyp.settings'
django.setup()

from candlesticks.models import Candlestick
from datetime import datetime, timedelta, timezone
import pandas_datareader as dr

if __name__ == '__main__':
    start_date = (datetime.now() - timedelta(days=7)).strftime('%Y-%m-%d')
    end_date = datetime.now().strftime('%Y-%m-%d')

    df = dr.data.DataReader('EURUSD%3DX', data_source='yahoo', start=start_date, end=end_date)

    symbol = 'EURUSD'
    period = 1440  # Minutes in a day, D1 timeframe expected
    source = 'Pandas'

    # Write bar data to Django bar table
    for date, row in df.iterrows():
        time = date.to_pydatetime().replace(tzinfo=timezone.utc)
        Candlestick.objects.update_or_create(symbol=symbol,
                                             time=time,
                                             period=period,
                                             source=source,
                                             defaults={'symbol': symbol,
                                                       'time': time,
                                                       'open': row['Open'],
                                                       'high': row['High'],
                                                       'low': row['Low'],
                                                       'close': row['Close'],
                                                       'volume': row['Volume'],
                                                       'period': period,
                                                       'source': source,
                                                       }
                                             )
