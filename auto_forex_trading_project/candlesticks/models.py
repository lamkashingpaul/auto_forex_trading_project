from django.db import models


class Candlestick(models.Model):
    # Symbols lookup variables
    EURUSD, EURGBP, EURAUD, EURCAD = 'EURUSD', 'EURGBP', 'EURAUD', 'EURCAD'
    EURCHF, EURJPY, EURNZD, AUDCAD = 'EURCHF', 'EURJPY', 'EURNZD', 'AUDCAD'
    AUDCHF, AUDJPY, AUDNZD, AUDUSD = 'AUDCHF', 'AUDJPY', 'AUDNZD', 'AUDUSD'
    CADCHF, CADJPY, CHFJPY, GBPAUD = 'CADCHF', 'CADJPY', 'CHFJPY', 'GBPAUD'
    GBPCAD, GBPCHF, GBPJPY, GBPNZD = 'GBPCAD', 'GBPCHF', 'GBPJPY', 'GBPNZD'
    GBPUSD, NZDCAD, NZDCHF, NZDJPY = 'GBPUSD', 'NZDCAD', 'NZDCHF', 'NZDJPY'
    NZDUSD, USDCAD, USDCHF, USDJPY = 'NZDUSD', 'USDCAD', 'USDCHF', 'USDJPY'

    # Periods lookup variables
    Tick, M1, M5, M15, M30 = 0, 1, 5, 15, 30
    H1, H4, D1, W1, MN = 60, 240, 1440, 10080, 43200

    # Sources lookup variables
    Pandas = 'Pandas'
    Dukascopy = 'Dukascopy'

    # Price type lookup variables
    BID = 'BID'
    ASK = 'ASK'

    # Symbols lookup table
    SYMBOLS = [
        (EURUSD, 'EURUSD'),
        (USDJPY, 'USDJPY'),
        (GBPUSD, 'GBPUSD'),
        (AUDUSD, 'AUDUSD'),
        (USDCAD, 'USDCAD'),
        (USDCHF, 'USDCHF'),
        (NZDUSD, 'NZDUSD'),
        (EURJPY, 'EURJPY'),
        (GBPJPY, 'GBPJPY'),
        (EURGBP, 'EURGBP'),
        (AUDJPY, 'AUDJPY'),
        (EURAUD, 'EURAUD'),
        (EURCHF, 'EURCHF'),
        (AUDNZD, 'AUDNZD'),
        (NZDJPY, 'NZDJPY'),
        (GBPAUD, 'GBPAUD'),
        (GBPCAD, 'GBPCAD'),
        (EURNZD, 'EURNZD'),
        (AUDCAD, 'AUDCAD'),
        (GBPCHF, 'GBPCHF'),
        (AUDCHF, 'AUDCHF'),
        (EURCAD, 'EURCAD'),
        (CADJPY, 'CADJPY'),
        (GBPNZD, 'GBPNZD'),
        (CADCHF, 'CADCHF'),
        (CHFJPY, 'CHFJPY'),
        (NZDCAD, 'NZDCAD'),
        (NZDCHF, 'NZDCHF'),
    ]

    # Periods lookup table
    PERIODS = (
        (Tick, 'Tick'), (M1, 'M1'), (M5, 'M5'), (M15, 'M15'), (M30, 'M30'),
        (H1, 'H1'), (H4, 'H4'), (D1, 'D1'), (W1, 'W1'), (MN, 'MN'),
    )

    # Sources lookup table
    SOURCES = (
        (Dukascopy, 'Dukascopy'),
        (Pandas, 'Pandas'),
    )

    # Price type lookup table
    PRICE_TYPES = (
        (BID, 'Bid'),
        (ASK, 'Ask'),
    )

    symbol = models.CharField('Symbol', max_length=6, choices=SYMBOLS, default=EURUSD)
    time = models.DateTimeField('Datetime')

    open = models.FloatField('Open', null=True, blank=True, default=None)
    high = models.FloatField('High', null=True, blank=True, default=None)
    low = models.FloatField('Low', null=True, blank=True, default=None)
    close = models.FloatField('Close', null=True, blank=True, default=None)
    volume = models.FloatField('Volume (M)', null=True, blank=True, default=None)

    period = models.IntegerField('Period', choices=PERIODS, default=Tick)
    source = models.CharField('Source', max_length=16, choices=SOURCES, default=Dukascopy)
    price_type = models.CharField('Price type', max_length=3, choices=PRICE_TYPES, default=BID)

    predicted_open = models.FloatField('Predicted Open', null=True, blank=True, default=None)
    predicted_high = models.FloatField('Predicted High', null=True, blank=True, default=None)
    predicted_low = models.FloatField('Predicted Low', null=True, blank=True, default=None)
    predicted_close = models.FloatField('Predicted Close', null=True, blank=True, default=None)
    predicted_volume = models.FloatField('Predicted Volume (M)', null=True, blank=True, default=None)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['symbol', 'time', 'period', 'price_type', 'source'], name='one_candlestick_per_timeframe_per_source')
        ]

    def __str__(self):
        return ''.join((self.symbol, ' ', str(self.time)))
