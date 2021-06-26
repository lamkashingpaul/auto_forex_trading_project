#!/home/paullam/fyp/fypenv/bin/python3
import sys
import os
import django
# Connect to existing Django Datebase
sys.path.append('/home/paullam/fyp/fyp/')
os.environ['DJANGO_SETTINGS_MODULE'] = 'fyp.settings'
django.setup()

from datetime import datetime
import pandas_datareader as dr
import pandas as pd
from candlesticks.models import Candlestick


if __name__ == '__main__':
    Candlestick.objects.all().delete()
