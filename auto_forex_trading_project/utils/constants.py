import backtrader as bt

MY_TABLE_NAME = 'candlesticks_candlestick'

'''
structure of tuple value (value for PSQL query, bt.TimeFrame, compression)
'''
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

CURRENCIES = [
    'AUD', 'CAD', 'CHF', 'EUR', 'GBP', 'JPY', 'NZD', 'USD',
]

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
