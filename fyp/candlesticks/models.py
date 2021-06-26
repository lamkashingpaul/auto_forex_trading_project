from typing import ClassVar
from django.db import models
from django.db.models import constraints

# Create your models here.
class Candlestick(models.Model):
    EURUSD, EURGBP, EURAUD, EURCAD = 'EURUSD', 'EURGBP', 'EURAUD', 'EURCAD'
    EURCHF, EURJPY, EURNZD, AUDCAD = 'EURCHF', 'EURJPY', 'EURNZD', 'AUDCAD'
    AUDCHF, AUDJPY, AUDNZD, AUDUSD = 'AUDCHF', 'AUDJPY', 'AUDNZD', 'AUDUSD'
    CADCHF, CADJPY, CHFJPY, GBPAUD = 'CADCHF', 'CADJPY', 'CHFJPY', 'GBPAUD'
    GBPCAD, GBPCHF, GBPJPY, GBPNZD = 'GBPCAD', 'GBPCHF', 'GBPJPY', 'GBPNZD'
    GBPUSD, NZDCAD, NZDCHF, NZDJPY = 'GBPUSD', 'NZDCAD', 'NZDCHF', 'NZDJPY'
    NZDUSD, USDCAD, USDCHF, USDJPY = 'NZDUSD', 'USDCAD', 'USDCHF', 'USDJPY'

    Tick, M1, M5, M15, M30 = 0, 1, 5, 15, 30
    H1, H4, D1, W1, MN = 60, 240, 1440, 10080, 43200

    SYMBOLS = [
        (EURUSD, 'EURUSD'), (EURGBP, 'EURGBP'), (EURAUD, 'EURAUD'), (EURCAD, 'EURCAD'),
        (EURCHF, 'EURCHF'), (EURJPY, 'EURJPY'), (EURNZD, 'EURNZD'), (AUDCAD, 'AUDCAD'),
        (AUDCHF, 'AUDCHF'), (AUDJPY, 'AUDJPY'), (AUDNZD, 'AUDNZD'), (AUDUSD, 'AUDUSD'),
        (CADCHF, 'CADCHF'), (CADJPY, 'CADJPY'), (CHFJPY, 'CHFJPY'), (GBPAUD, 'GBPAUD'),
        (GBPCAD, 'GBPCAD'), (GBPCHF, 'GBPCHF'), (GBPJPY, 'GBPJPY'), (GBPNZD, 'GBPNZD'),
        (GBPUSD, 'GBPUSD'), (NZDCAD, 'NZDCAD'), (NZDCHF, 'NZDCHF'), (NZDJPY, 'NZDJPY'),
        (NZDUSD, 'NZDUSD'), (USDCAD, 'USDCAD'), (USDCHF, 'USDCHF'), (USDJPY, 'USDJPY')
    ]

    PERIODS_OF_CANDLESTICKS = [
        (Tick, 'Tick'), (M1, 'M1'), (M5, 'M5'), (M15,  'M15'), (M30,  'M30'),
        (H1, 'H1'), (H4, 'H4'), (D1, 'D1'), (W1, 'W1'), (MN, 'MN')
    ]

    symbol = models.CharField('Symbol', max_length=6, choices=SYMBOLS, default=EURUSD)
    time = models.DateTimeField('Datetime', unique=True)
    open = models.FloatField('Open')
    high = models.FloatField('High')
    low = models.FloatField('Low')
    close = models.FloatField('Close')
    volume = models.FloatField('Volume')
    period = models.IntegerField('Period', choices=PERIODS_OF_CANDLESTICKS, default=Tick)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['symbol', 'time', 'period'], name='one_candlestick_per_timeframe')
        ]

    def __str__(self):
        return ''.join((self.symbol, ' ', str(self.time)))
