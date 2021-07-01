#!/home/paullam/fyp/fypenv/bin/python3
import django
import os
import sys
# Connect to existing Django Datebase
sys.path.append('/home/paullam/fyp/fyp/')
os.environ['DJANGO_SETTINGS_MODULE'] = 'fyp.settings'
django.setup()

from candlesticks.models import Candlestick
from datetime import date, timedelta

symbol = 'EURUSD'
price_type = 'BID'
number_of_workers = 4

# default date range
start_date = date(2003, 5, 4)
end_date = (date.today() - timedelta(days=1))


def daterange(start_date, end_date):
    # date generator
    # end date is included
    for n in range(int((end_date - start_date).days) + 1):
        yield start_date + timedelta(n)


def get_start_and_end_time_of_date(date):
    # return start time and end time of given date
    # it is expected that they are 00:00:00 and 23:59:59
    time_from = date
    time_before = date + timedelta(microseconds=-1)
    return time_from, time_before


def get_sunday_by_date(date):
    # given a date in a week, return date of sunday in this week
    pass


def one_minute_to_five_minute(date):
    pass


if __name__ == '__main__':
    start_date = date(2003, 5, 4)
    end_date = date(2003, 5, 5)

    for n in range(int((end_date - start_date).days) + 1):  # include end date
        print(get_start_and_end_time_of_date(start_date + timedelta(n)))
