#!/home/paullam/fyp/venv/bin/python3
import sys
import os
import django
# Connect to existing Django Datebase
sys.path.append('/home/paullam/fyp/fyp/')
os.environ['DJANGO_SETTINGS_MODULE'] = 'fyp.settings.local'
django.setup()

from candlesticks.models import Candlestick

from datetime import date

if __name__ == '__main__':
    if input('Are you sure to remove all candlesticks? (y/n): ') == 'y':
        time_from = date(2021, 11, 29)
        time_before = date(2021, 12, 1)
        query_result = Candlestick.objects.filter(symbol__exact='EURCAD',
                                                  price_type__exact='BID',
                                                  period__exact=1440,
                                                  time__range=(time_from, time_before),
                                                  )
        print(query_result.count())
        # query_result.delete()
