import itertools
import random


def sma_testcase_generator(max_period, n=0):
    max_period += 1

    if n == 0:
        testcases = itertools.product(range(1, max_period), range(1, max_period), (0.0001, 0.0005, 0.0010))
        for fast_ma_period, slow_ma_period, strength in testcases:
            if fast_ma_period != slow_ma_period:
                for use_strength in (True, False):
                    yield dict(use_strength=use_strength,
                               strength=strength,
                               fast_ma_period=fast_ma_period,
                               slow_ma_period=slow_ma_period,
                               )
    else:
        for _ in range(n):
            fast_ma_period, slow_ma_period = random.sample(range(1, max_period), 2)
            for use_strength in (True, False):
                for strength in (0.0001, 0.0005, 0.0010):
                    yield dict(use_strength=use_strength,
                               strength=strength,
                               fast_ma_period=fast_ma_period,
                               slow_ma_period=slow_ma_period,
                               )


def rsi_testcase_generator(max_period, n=0, upper_unwind=30.0, lower_unwind=70.0):
    max_period += 1

    if n == 0:
        for period in range(1, max_period):
            yield dict(use_strength=True,
                       period=period,
                       upper_unwind=upper_unwind,
                       lower_unwind=lower_unwind,
                       )

    else:
        for _ in range(n):
            period = random.randint(1, max_period)
            yield dict(use_strength=True,
                       period=period,
                       upper_unwind=upper_unwind,
                       lower_unwind=lower_unwind,
                       )


def strengthmeter_testcase_generator(max_fast_ma_period, max_slow_ma_period, n=0):
    max_slow_ma_period += 1
    max_fast_ma_period += 1

    if n == 0:
        for slow_ma_period in range(3, max_slow_ma_period):
            for fast_ma_period in range(2, max_fast_ma_period):
                yield dict(fast_ma_period=fast_ma_period,
                           slow_ma_period=slow_ma_period,
                           )

    else:
        for _ in range(n):
            fast_ma_period = random.randint(1, max_fast_ma_period)
            slow_ma_period = random.randint(1, max_slow_ma_period)
            yield dict(fast_ma_period=fast_ma_period,
                       slow_ma_period=slow_ma_period,
                       )
