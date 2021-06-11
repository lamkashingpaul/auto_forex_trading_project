import sys
import os
import django
# Connect to existing Django Datebase
sys.path.append('/home/paullam/fyp/fyp/')
os.environ['DJANGO_SETTINGS_MODULE'] = 'fyp.settings'
django.setup()

from bars.models import Bar, Symbol
from datetime import timezone
import pandas_datareader as dr


if __name__ == '__main__':
    start_date = '2021-01-01'
    end_date = '2021-06-13'

    df = dr.data.DataReader('EURUSD%3DX', data_source='yahoo', start=start_date, end=end_date)
    symbol = Symbol.objects.get(symbol='EURUSD')

    for date, row in df.iterrows():
        Bar.objects.create(symbol=symbol,
                           time=date.to_pydatetime().replace(tzinfo=timezone.utc),
                           open=row['Open'],
                           high=row['High'],
                           low=row['Low'],
                           close=row['Close'],
                           volume=row['Volume'])
