#!/home/paullam/auto_forex_trading_project/venv/bin/python3
from backtrader import TimeFrame
from datetime import date
from psycopg2 import sql

import argparse
import csv
import psycopg2


PERIODS = {
    'M1': (1, TimeFrame.Minutes, 1),
    'M5': (5, TimeFrame.Minutes, 5),
    'M15': (15, TimeFrame.Minutes, 15),
    'M30': (30, TimeFrame.Minutes, 30),
    'H1': (60, TimeFrame.Minutes, 60),
    'H4': (240, TimeFrame.Minutes, 240),
    'D1': (1440, TimeFrame.Days, 1),
    'W1': (10080, TimeFrame.Days, 7),
    'MN': (43200, TimeFrame.Months, 1),
}

READABLE_PERIODS = {
    1: 'M1',
    5: 'M5',
    15: 'M15',
    30: 'M30',
    60: 'H1',
    240: 'H4',
    1440: 'D1',
    10080: 'W1',
    43200: 'MN',
}

SYMBOLS = [
    'AUDCAD', 'AUDCHF', 'AUDJPY', 'AUDNZD', 'AUDUSD', 'CADCHF',
    'CADJPY', 'CHFJPY', 'EURAUD', 'EURCAD', 'EURCHF', 'EURGBP',
    'EURJPY', 'EURNZD', 'EURUSD', 'GBPAUD', 'GBPCAD', 'GBPCHF',
    'GBPJPY', 'GBPNZD', 'GBPUSD', 'NZDCAD', 'NZDCHF', 'NZDJPY',
    'NZDUSD', 'USDCAD', 'USDCHF', 'USDJPY',
]

PRICE_TYPES = [
    'ASK',
    'BID',
]


def parse_args():
    parser = argparse.ArgumentParser(description='Generate CSV from Database')

    parser.add_argument('--symbol', '-s', choices=SYMBOLS,
                        default='EURUSD', required=False,
                        help='symbols to be traded.')

    parser.add_argument('--period', '-p', choices=PERIODS.keys(),
                        default='D1', required=False,
                        help='timeframe period to be traded.')

    parser.add_argument('--fromdate', '-from', type=date.fromisoformat,
                        default=(date(2021, 1, 1)),
                        required=False, help='date starting the trade.')

    parser.add_argument('--todate', '-to', type=date.fromisoformat,
                        default=date(2022, 1, 1),
                        required=False, help='date ending the trade.')

    parser.add_argument('--price_type', '-pt', choices=PRICE_TYPES,
                        default='BID', required=False,
                        help='price_types to be traded.')

    return parser.parse_args()


def generate_csv(symbol, period, fromdate, todate, price_type):
    # connect to database
    conn = psycopg2.connect(database='forex')
    with conn:
        with conn.cursor() as curs:
            # define query
            query = sql.SQL('SELECT {time}, {open}, {high}, {low}, {close}, {volume} '
                            'FROM {table} '
                            'WHERE ({period} = %s AND '
                            '{price_type} = %s AND '
                            '{symbol} = %s AND '
                            '{volume} > 0 AND '
                            '{time} BETWEEN %s AND %s)'
                            'ORDER BY {time}').format(table=sql.Identifier('candlesticks_candlestick'),
                                                      symbol=sql.Identifier('symbol'),
                                                      price_type=sql.Identifier('price_type'),
                                                      time=sql.Identifier('time'),
                                                      open=sql.Identifier('open'),
                                                      high=sql.Identifier('high'),
                                                      low=sql.Identifier('low'),
                                                      close=sql.Identifier('close'),
                                                      volume=sql.Identifier('volume'),
                                                      period=sql.Identifier('period'),)

            # get query results
            curs.execute('SET TIME ZONE \'Hongkong\'')  # Convert to UTC timezone
            curs.execute(query, (period, price_type, symbol, fromdate, todate))
            rows = curs.fetchall()

            if rows:
                # define csv file name
                readable_period = READABLE_PERIODS[period]
                filename = f'{symbol}_from_{fromdate.strftime("%Y%m%d")}_to_{todate.strftime("%Y%m%d")}_{readable_period}_{price_type}.csv'

                # write rows to csv file
                with open(filename, 'w', newline='', encoding='utf-8') as w:
                    writer = csv.writer(w)

                    # add header row
                    writer.writerow(['Datetime', 'Open', 'High', 'Low', 'Close', 'Volume(Millions)'])
                    for row in rows:
                        # remove timezone info from datetime
                        writer.writerow((row[0].strftime('%Y-%m-%d %H:%M:%S'), ) + row[1:])

    conn.close()


def main():
    # get command *args
    args = parse_args()

    # get query paremeters
    symbol = args.symbol
    price_type = args.price_type
    period, _, _ = PERIODS[args.period]
    fromdate = args.fromdate
    todate = args.todate

    # generate csv file
    generate_csv(symbol, period, fromdate, todate, price_type)


if __name__ == '__main__':
    main()
