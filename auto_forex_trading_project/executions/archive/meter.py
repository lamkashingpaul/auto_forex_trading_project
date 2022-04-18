from datetime import datetime, timedelta
from psycopg2 import sql
import argparse
import backtrader as bt
import collections
import concurrent.futures
import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import os
import pandas as pd
import psycopg2
import random

PERIODS = {
    'M1': (1, bt.TimeFrame.Minutes, 1),
    'M5': (5, bt.TimeFrame.Minutes, 5),
    'M15': (15, bt.TimeFrame.Minutes, 15),
    'M30': (30, bt.TimeFrame.Minutes, 30),
    'H1': (60, bt.TimeFrame.Minutes, 60),
    'H4': (240, bt.TimeFrame.Minutes, 240),
    'D1': (1440, bt.TimeFrame.Days, 1),
    'W1': (10080, bt.TimeFrame.Days, 7),
    'MN': (43200, bt.TimeFrame.Months, 1),
}


class PSQLData(bt.feeds.DataBase):
    params = (
        ('dataname', None),
        ('name', None),
        ('symbol', 'AUDCAD'),
        ('period', 'D1'),
        ('price_type', 'BID'),
        ('timeframe', bt.TimeFrame.Days),
        ('compression', 1),
        ('fromdate', datetime.min),
        ('todate', datetime.max),

        # parameterized column indices for overwriting
        ('datetime', 0),
        ('open', 1),
        ('high', 2),
        ('low', 3),
        ('close', 4),
        ('volume', 5),
        ('openinterest', -1),
    )

    def start(self):
        period_in_minute, self.p.timeframe, self.p.compression, = PERIODS[self.p.period]

        if not self.p.name:
            self.p.name = self.p.symbol

        # connect to PSQL
        conn = self._connect_db()
        cursor = conn.cursor()

        # define query
        query = sql.SQL('SELECT {time}, {open}, {high}, {low}, {close}, {volume} '
                        'FROM {table} '
                        'WHERE ({price_type} = %s AND '
                        '{period} = %s AND '
                        '{symbol} = %s AND '
                        '{volume} > 0 AND '
                        '{time} BETWEEN %s AND %s)').format(table=sql.Identifier('candlesticks_candlestick'),
                                                            symbol=sql.Identifier('symbol'),
                                                            time=sql.Identifier('time'),
                                                            open=sql.Identifier('open'),
                                                            high=sql.Identifier('high'),
                                                            low=sql.Identifier('low'),
                                                            close=sql.Identifier('close'),
                                                            volume=sql.Identifier('volume'),
                                                            price_type=sql.Identifier('price_type'),
                                                            period=sql.Identifier('period'),)

        # execute query template with input parameters
        cursor.execute(query, (self.p.price_type, period_in_minute, self.p.symbol, self.p.fromdate, self.p.todate))

        self.rows = cursor.fetchall()

        conn.close()

        self.rows_i = 0
        super(PSQLData, self).start()

    def _load(self):
        if self.rows is None or self.rows_i >= len(self.rows):
            return False

        row = self.rows[self.rows_i]

        for datafield in self.getlinealiases():

            if datafield == 'datetime':
                self.lines.datetime[0] = bt.date2num(row[self.p.datetime])

            else:
                # get column index
                col_idx = getattr(self.p, datafield)

                # skip if line is not used
                if col_idx < 0:
                    continue
                else:
                    getattr(self.lines, datafield)[0] = row[col_idx]

        self.rows_i += 1
        return True

    def _connect_db(self):
        conn = psycopg2.connect(database='forex',
                                # info below is not needed while using unix socket
                                # host='192.168.1.72',
                                # port='5432',
                                # user=os.environ.get('PG_USER', ''),
                                # password=os.environ.get('PG_PASSWORD', '')
                                )

        return conn

    def preload(self):
        super(PSQLData, self).preload()
        self.rows = None


class CurrenciesMeter(bt.Indicator):
    pass


class DivergeStrategy(bt.Strategy):
    pass


def parse_args():
    parser = argparse.ArgumentParser(description='My first strategy')

    return parser.parse_args()


def main():
    pass


if __name__ == '__main__':
    args = parse_args()

    main()
