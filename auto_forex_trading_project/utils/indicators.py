import backtrader as bt


class VolumeWeightedAveragePrice(bt.Indicator):
    plotinfo = dict(subplot=False)

    params = (('period', 30), )

    alias = ('VWAP', 'VolumeWeightedAveragePrice',)
    lines = ('VWAP',)
    plotlines = dict(VWAP=dict(alpha=0.50, linestyle='-.', linewidth=2.0))

    def __init__(self):
        # Before super to ensure mixins (right-hand side in subclassing)
        # can see the assignment operation and operate on the line
        cumvol = bt.ind.SumN(self.data.volume, period=self.p.period)
        typprice = ((self.data.close + self.data.high + self.data.low) / 3) * self.data.volume
        cumtypprice = bt.ind.SumN(typprice, period=self.p.period)
        self.lines[0] = cumtypprice / cumvol

        super(VolumeWeightedAveragePrice, self).__init__()


class EightCurrenciesIndicator(bt.Indicator):
    # Declare indicator lines
    lines = (
        'AUD', 'CAD', 'CHF', 'EUR', 'GBP', 'JPY', 'NZD', 'USD',
        'AUDCAD', 'AUDCHF', 'AUDJPY', 'AUDNZD', 'AUDUSD', 'CADCHF',
        'CADJPY', 'CHFJPY', 'EURAUD', 'EURCAD', 'EURCHF', 'EURGBP',
        'EURJPY', 'EURNZD', 'EURUSD', 'GBPAUD', 'GBPCAD', 'GBPCHF',
        'GBPJPY', 'GBPNZD', 'GBPUSD', 'NZDCAD', 'NZDCHF', 'NZDJPY',
        'NZDUSD', 'USDCAD', 'USDCHF', 'USDJPY',
    )

    # Default indicator parameters
    params = (
        ('period', 14),
        ('AUDCAD', 1.000), ('AUDCHF', 1.000), ('AUDJPY', 1.000), ('AUDNZD', 1.000),
        ('AUDUSD', 1.000), ('CADCHF', 1.000), ('CADJPY', 1.000), ('CHFJPY', 1.000),
        ('EURAUD', 1.000), ('EURCAD', 1.000), ('EURCHF', 1.000), ('EURGBP', 1.000),
        ('EURJPY', 1.000), ('EURNZD', 1.000), ('EURUSD', 1.000), ('GBPAUD', 1.000),
        ('GBPCAD', 1.000), ('GBPCHF', 1.000), ('GBPJPY', 1.000), ('GBPNZD', 1.000),
        ('GBPUSD', 1.000), ('NZDCAD', 1.000), ('NZDCHF', 1.000), ('NZDJPY', 1.000),
        ('NZDUSD', 1.000), ('USDCAD', 1.000), ('USDCHF', 1.000), ('USDJPY', 1.000),
    )

    # Default indicator plotinfo parameters
    plotinfo = (
        ('plot', True),
        ('subplot', True),
    )
    # Indicator lines specific plotting styles
    plotlines = dict(
        AUD=dict(_plotskip=False),
        CAD=dict(_plotskip=False),
        CHF=dict(_plotskip=False),
        EUR=dict(_plotskip=False),
        GBP=dict(_plotskip=False),
        JPY=dict(_plotskip=False),
        NZD=dict(_plotskip=False),
        USD=dict(_plotskip=False),
        AUDCAD=dict(_plotskip=True),
        AUDCHF=dict(_plotskip=True),
        AUDJPY=dict(_plotskip=True),
        AUDNZD=dict(_plotskip=True),
        AUDUSD=dict(_plotskip=True),
        CADCHF=dict(_plotskip=True),
        CADJPY=dict(_plotskip=True),
        CHFJPY=dict(_plotskip=True),
        EURAUD=dict(_plotskip=True),
        EURCAD=dict(_plotskip=True),
        EURCHF=dict(_plotskip=True),
        EURGBP=dict(_plotskip=True),
        EURJPY=dict(_plotskip=True),
        EURNZD=dict(_plotskip=True),
        EURUSD=dict(_plotskip=True),
        GBPAUD=dict(_plotskip=True),
        GBPCAD=dict(_plotskip=True),
        GBPCHF=dict(_plotskip=True),
        GBPJPY=dict(_plotskip=True),
        GBPNZD=dict(_plotskip=True),
        GBPUSD=dict(_plotskip=True),
        NZDCAD=dict(_plotskip=True),
        NZDCHF=dict(_plotskip=True),
        NZDJPY=dict(_plotskip=True),
        NZDUSD=dict(_plotskip=True),
        USDCAD=dict(_plotskip=True),
        USDCHF=dict(_plotskip=True),
        USDJPY=dict(_plotskip=True),
    )

    def __init__(self):
        # Lookup values
        self.total_number_of_currencies = 8
        self.total_number_of_pairs = 28

        # Two EMAs used for ACS evaluations
        self.rsi = {}

        for i in range(self.total_number_of_pairs):
            pair_name = self.datas[i]._name[0:6]
            self.rsi[pair_name] = bt.indicators.RSI(self.datas[i].lines.close, period=self.p.period).rsi()

    def next(self):
        # Initialize each line value for today
        for line in self.lines:
            line[0] = 0

        # Calculate values for each currency line
        for symbol in self.datas:
            pair_name = symbol._name[0:6]
            base_currency = symbol._name[0:3]
            quot_currency = symbol._name[3:6]

            getattr(self.lines, base_currency)[0] += self.rsi[pair_name] * getattr(self.p, pair_name) / (self.total_number_of_currencies - 1)
            getattr(self.lines, quot_currency)[0] += (100 - self.rsi[pair_name]) * getattr(self.p, pair_name) / (self.total_number_of_currencies - 1)


class TwentyeightPairsIndicator(bt.Indicator):

    # Declare indicator lines
    lines = (
        'AUD', 'CAD', 'CHF', 'EUR', 'GBP', 'JPY', 'NZD', 'USD',
        'AUDCAD', 'AUDCHF', 'AUDJPY', 'AUDNZD', 'AUDUSD', 'CADCHF',
        'CADJPY', 'CHFJPY', 'EURAUD', 'EURCAD', 'EURCHF', 'EURGBP',
        'EURJPY', 'EURNZD', 'EURUSD', 'GBPAUD', 'GBPCAD', 'GBPCHF',
        'GBPJPY', 'GBPNZD', 'GBPUSD', 'NZDCAD', 'NZDCHF', 'NZDJPY',
        'NZDUSD', 'USDCAD', 'USDCHF', 'USDJPY',
    )

    # Default indicator parameters
    params = (
        ('fast_ma_period', 3),
        ('slow_ma_period', 20),

        ('AUDCAD', 0.650), ('AUDCHF', 0.550), ('AUDJPY', 0.700), ('AUDNZD', 0.440),
        ('AUDUSD', 0.650), ('CADCHF', 1.000), ('CADJPY', 1.000), ('CHFJPY', 1.000),
        ('EURAUD', 0.850), ('EURCAD', 0.800), ('EURCHF', 0.850), ('EURGBP', 0.600),
        ('EURJPY', 0.650), ('EURNZD', 0.800), ('EURUSD', 0.800), ('GBPAUD', 0.250),
        ('GBPCAD', 0.250), ('GBPCHF', 0.200), ('GBPJPY', 0.500), ('GBPNZD', 0.050),
        ('GBPUSD', 0.500), ('NZDCAD', 0.700), ('NZDCHF', 0.700), ('NZDJPY', 0.700),
        ('NZDUSD', 0.700), ('USDCAD', 1.000), ('USDCHF', 1.000), ('USDJPY', 1.000),
    )

    # Default indicator plotinfo parameters
    plotinfo = (
        ('plot', True),
        ('subplot', True),
    )

    # Indicator lines specific plotting styles
    plotlines = dict(
        AUD=dict(_plotskip=True),
        CAD=dict(_plotskip=True),
        CHF=dict(_plotskip=True),
        EUR=dict(_plotskip=True),
        GBP=dict(_plotskip=True),
        JPY=dict(_plotskip=True),
        NZD=dict(_plotskip=True),
        USD=dict(_plotskip=True),
        AUDCAD=dict(_plotskip=False),
        AUDCHF=dict(_plotskip=False),
        AUDJPY=dict(_plotskip=False),
        AUDNZD=dict(_plotskip=False),
        AUDUSD=dict(_plotskip=False),
        CADCHF=dict(_plotskip=False),
        CADJPY=dict(_plotskip=False),
        CHFJPY=dict(_plotskip=False),
        EURAUD=dict(_plotskip=False),
        EURCAD=dict(_plotskip=False),
        EURCHF=dict(_plotskip=False),
        EURGBP=dict(_plotskip=False),
        EURJPY=dict(_plotskip=False),
        EURNZD=dict(_plotskip=False),
        EURUSD=dict(_plotskip=False),
        GBPAUD=dict(_plotskip=False),
        GBPCAD=dict(_plotskip=False),
        GBPCHF=dict(_plotskip=False),
        GBPJPY=dict(_plotskip=False),
        GBPNZD=dict(_plotskip=False),
        GBPUSD=dict(_plotskip=False),
        NZDCAD=dict(_plotskip=False),
        NZDCHF=dict(_plotskip=False),
        NZDJPY=dict(_plotskip=False),
        NZDUSD=dict(_plotskip=False),
        USDCAD=dict(_plotskip=False),
        USDCHF=dict(_plotskip=False),
        USDJPY=dict(_plotskip=False),
    )

    def __init__(self):
        # Lookup values
        self.total_number_of_currencies = 8
        self.total_number_of_pairs = 28

        # Two EMAs used for ACS evaluations
        self.fast_ema = {}
        self.slow_ema = {}

        for i in range(self.total_number_of_pairs):
            pair_name = self.datas[i]._name[0:6]
            self.fast_ema[pair_name] = bt.indicators.EMA(self.datas[i].lines.close, period=self.p.fast_ma_period).ema()
            self.slow_ema[pair_name] = bt.indicators.EMA(self.datas[i].lines.close, period=self.p.slow_ma_period).ema()

    def next(self):
        # Initialize each line value for today
        for line in self.lines:
            line[0] = 0

        # Calculate values for each currency line
        for symbol in self.datas:
            pair_name = symbol._name[0:6]
            base_currency = symbol._name[0:3]
            quot_currency = symbol._name[3:6]
            if(self.slow_ema[pair_name][0] != 0):
                ma_percentage = (self.fast_ema[pair_name][0] - self.slow_ema[pair_name][0]) / self.slow_ema[pair_name][0] * getattr(self.p, pair_name)
            else:
                ma_percentage = 0

            getattr(self.lines, base_currency)[0] += ma_percentage
            getattr(self.lines, quot_currency)[0] -= ma_percentage

        # Calculate 28 symbols values
        for symbol in self.datas:
            pair_name = symbol._name[0:6]
            base_currency = symbol._name[0:3]
            quot_currency = symbol._name[3:6]
            getattr(self.lines, pair_name)[0] = getattr(self.lines, base_currency)[0] - getattr(self.lines, quot_currency)[0]
