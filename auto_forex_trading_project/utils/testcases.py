from datetime import datetime, timedelta
import itertools
import math
import random


def slides_generator(datetime_from, datetime_before, durations, steps, **kwargs):
    input_datetime_from = datetime.combine(datetime_from, datetime.min.time())
    input_datetime_before = datetime.combine(datetime_before, datetime.min.time())

    durations = [timedelta(days=durations)]
    steps = [timedelta(days=steps)]

    for duration in durations:
        for step in steps:
            datetime_from, datetime_before = input_datetime_from, input_datetime_before
            while datetime_from < datetime_before:
                delta = datetime_before - datetime_from
                if duration > delta:
                    yield dict(datetime_from=datetime_from,
                               datetime_before=datetime_before,
                               **kwargs,)
                    break

                else:
                    yield dict(datetime_from=datetime_from,
                               datetime_before=datetime_from + duration,
                               **kwargs,)

                    datetime_from += step


def sma_testcase_generator(n=0, max_period=1):
    n = int(n)
    max_period = int(max_period) + 1

    if n == 0:
        testcases = itertools.product(range(1, max_period), range(1, max_period))
        for fast_ma_period, slow_ma_period in testcases:
            if fast_ma_period != slow_ma_period:
                yield dict(fast_ma_period=fast_ma_period,
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


def sma_strength_testcase_generator(n=0, max_period=1, max_strength=0.001, strength_step=0.0001):
    n = int(n)
    max_period = int(max_period) + 1

    if strength_step == 0.0:
        strength_step = 1

    if n == 0:
        testcases = itertools.product(range(1, max_period), range(1, max_period))
        for fast_ma_period, slow_ma_period in testcases:
            if fast_ma_period != slow_ma_period:
                for i in range(math.ceil(max_strength / strength_step)):
                    strength = i * strength_step
                    yield dict(use_strength=strength != 0,
                               strength=strength,
                               fast_ma_period=fast_ma_period,
                               slow_ma_period=slow_ma_period,
                               )
    else:
        for _ in range(n):
            fast_ma_period, slow_ma_period = random.sample(range(1, max_period), 2)
            strength = random.uniform(0, max_strength)
            yield dict(use_strength=strength != 0,
                       strength=strength,
                       fast_ma_period=fast_ma_period,
                       slow_ma_period=slow_ma_period,
                       )


def rsi_testcase_generator(n=0, max_period=1, lowerband_from=30.0, lowerband_to=40.0,
                           upperband_from=60.0, upperband_to=70.0, wind_step=1.0):
    n = int(n)
    max_period = int(max_period) + 1

    if n == 0:
        for period in range(1, max_period):
            for i in range(math.ceil((lowerband_to - lowerband_from) / wind_step)):
                for j in range(math.ceil((upperband_to - upperband_from) / wind_step)):
                    lowerband = lowerband_from + i * wind_step
                    upperband = upperband_from + j * wind_step

                    yield dict(use_strength=False,
                               period=period,
                               lowerband=lowerband,
                               upperband=upperband,
                               )

    else:
        i = math.ceil((lowerband_to - lowerband_from) / wind_step)
        j = math.ceil((upperband_to - upperband_from) / wind_step)

        for _ in range(n):
            period = random.randint(1, max_period)
            lowerband = lowerband_from + random.randrange(i) * wind_step
            upperband = upperband_from + random.randrange(j) * wind_step
            yield dict(use_strength=True,
                       period=period,
                       lowerband=lowerband,
                       upperband=upperband,
                       )


def rsi_sizing_testcase_generator(n=0, max_period=1, size_multiplier_from=0.0, size_multiplier_to=0.5, size_step=0.05,
                                  lowerband_from=30.0, lowerband_to=40.0, upperband_from=60.0, upperband_to=70.0, wind_step=5.0):

    n = int(n)
    max_period = int(max_period) + 1

    if n == 0:
        for period in range(1, max_period):
            for i in range(math.ceil((lowerband_to - lowerband_from) / wind_step)):
                for j in range(math.ceil((upperband_to - upperband_from) / wind_step)):
                    for k in range(math.ceil((size_multiplier_to - size_multiplier_from) / size_step)):
                        lowerband = lowerband_from + i * wind_step
                        upperband = upperband_from + j * wind_step
                        size_multiplier = size_multiplier_from + k * size_step

                        yield dict(use_strength=True,
                                   period=period,
                                   lowerband=lowerband,
                                   upperband=upperband,
                                   size_multiplier=size_multiplier,
                                   )

    else:
        i = math.ceil((lowerband_to - lowerband_from) / wind_step)
        j = math.ceil((upperband_to - upperband_from) / wind_step)
        k = math.ceil((size_multiplier_to - size_multiplier_from) / size_step)
        for _ in range(n):
            period = random.randint(1, max_period)
            lowerband = lowerband_from + i * wind_step
            upperband = upperband_from + j * wind_step
            size_multiplier = size_multiplier_from + k * size_step

            yield dict(use_strength=True,
                       period=period,
                       lowerband=lowerband,
                       upperband=upperband,
                       size_multiplier=size_multiplier,
                       )


if __name__ == '__main__':
    for i, slide in enumerate(slides_generator(datetime(2016, 1, 1),
                                               datetime(2021, 1, 1),
                                               [timedelta(days=30 * (i + 1)) for i in range(3)],
                                               [timedelta(days=1)],
                                               )):
        print(i, slide)
