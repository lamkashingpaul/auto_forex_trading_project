#!/home/paullam/fyp/venv/bin/python3
import sys
import os
import django
# Connect to existing Django Datebase
sys.path.append('/home/paullam/fyp/fyp/')
os.environ['DJANGO_SETTINGS_MODULE'] = 'fyp.settings'
django.setup()

from candlesticks.models import Candlestick


if __name__ == '__main__':
    if input('Are you sure to remove all candlesticks? (y/n): ') == 'y':
        query_result = Candlestick.objects.filter(symbol__exact='NZDUSD')
        print(query_result.count())
        query_result.delete()
