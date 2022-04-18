from datetime import datetime
from psycopg2 import sql
from utils.constants import *
import backtrader as bt
import psycopg2


class PSQLData(bt.feeds.DataBase):
    params = (
        ('dataname', None),
        ('name', None),
        ('symbol', 'EURUSD'),
        ('period', 'H1'),
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

        # specific params
        ('price_type', 'BID'),
    )

    def start(self):
        self.p.period, self.p.timeframe, self.p.compression, = PERIODS[self.p.period]

        if not self.p.name:
            self.p.name = self.p.symbol

        # connect to PSQL
        conn = self._connect_db()
        cursor = conn.cursor()

        # define query
        query = sql.SQL('SELECT {time}, {open}, {high}, {low}, {close}, {volume}, {price_type} '
                        'FROM {table} '
                        'WHERE ({period} = %s AND '
                        '{price_type} = %s AND '
                        '{symbol} = %s AND '
                        '{volume} > 0 AND '
                        '{time} BETWEEN %s AND %s)').format(table=sql.Identifier('candlesticks_candlestick'),
                                                            symbol=sql.Identifier('symbol'),
                                                            price_type=sql.Identifier('price_type'),
                                                            time=sql.Identifier('time'),
                                                            open=sql.Identifier('open'),
                                                            high=sql.Identifier('high'),
                                                            low=sql.Identifier('low'),
                                                            close=sql.Identifier('close'),
                                                            volume=sql.Identifier('volume'),
                                                            period=sql.Identifier('period'),)

        # execute query template with input parameters
        cursor.execute(query, (self.p.period, self.p.price_type, self.p.symbol, self.p.fromdate, self.p.todate))

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
        conn = psycopg2.connect(database='forex')
        return conn

    def preload(self):
        super(PSQLData, self).preload()
        self.rows = None
