#!/home/paullam/auto_forex_trading_project/venv/bin/python3
import django
import os
import sys

# Connect to existing Django Datebase
sys.path.append('/home/paullam/auto_forex_trading_project/auto_forex_trading_project/')
os.environ['DJANGO_SETTINGS_MODULE'] = 'forex.settings.local'
django.setup()

from candlesticks.models import Candlestick

from datetime import datetime, date, timedelta
from tensorflow import keras
import joblib
import numpy as np
import pandas as pd


def add_prediction(d=0):
    # load model
    dirname = os.path.dirname(__file__)

    close_price_scaler = joblib.load(os.path.join(dirname, './models/day_bar_predict_5_close_bar_training_lr_0.005_scaler.bin'))
    close_price_model = keras.models.load_model(os.path.join(dirname, './models/day_bar_predict_5_close_bar_training_lr_0.005_trained_lstm_model.h5'))
    _, close_price_n_lookback, _ = close_price_model.input_shape
    _, close_price_n_forecast = close_price_model.output_shape

    open_price_scaler = joblib.load(os.path.join(dirname, './models/day_bar_predict_5_open_bar_training_lr_0.005_scaler.bin'))
    open_price_model = keras.models.load_model(os.path.join(dirname, './models/day_bar_predict_5_open_bar_training_lr_0.005_trained_lstm_model.h5'))
    _, open_price_n_lookback, _ = open_price_model.input_shape
    _, open_price_n_forecast = open_price_model.output_shape

    window_size = max(close_price_n_lookback, open_price_n_lookback)  # number of bars needed for prediction
    n = window_size + d  # total number of bars needed for d windows of prediction

    # implementation is based on daily bars of EURUSD market, modification is needed for other timeframe in order to align data
    symbol = 'EURUSD'
    period = 1440
    price_type = 'BID'
    source = 'Dukascopy'

    start_date = datetime.combine(date.today() - timedelta(days=2 * n), datetime.min.time())
    end_date = start_date + timedelta(days=2 * n, microseconds=-1)

    query_results = Candlestick.objects.filter(symbol__exact=symbol,
                                               period__exact=period,
                                               source__exact=source,
                                               price_type__exact=price_type,
                                               time__range=(start_date, end_date),
                                               volume__gt=0,
                                               ).order_by('time')

    if len(query_results) < n:
        return

    # convert latest n bars into dataframe
    # {start} is used for prediction starting from last d-th day, start=0 means prediction starting from today
    for start in reversed(range(d + 1)):
        query_results_slice = query_results.values_list('time', 'open', 'high', 'low', 'close', 'volume')[len(query_results) - window_size - start:len(query_results) - start]
        df = pd.DataFrame(query_results_slice, columns=['time', 'open', 'high', 'low', 'close', 'volume'])

        prediction_startsfrom = df['time'].iloc[-1].to_pydatetime() + timedelta(days=1)
        if prediction_startsfrom.isoweekday() == 6:  # forex market is not available on local Saturday time
            # prediction shall start from Sunday
            prediction_startsfrom += timedelta(days=1)

        # get prediction for close price
        y = df['close'].fillna(method='ffill')
        y = y.values.reshape(-1, 1)
        y = close_price_scaler.transform(y)

        X = [y[i - close_price_n_lookback:i].reshape(1, close_price_n_lookback, 1) for i in range(close_price_n_lookback, len(y) + 1)]
        Y = [close_price_scaler.inverse_transform(close_price_model.predict(x).reshape(-1, 1)) for x in X]

        y_predicted = np.array(Y).astype(np.float64).squeeze()
        predicted_close_prices = pd.Series(y_predicted)

        # get prediction for open price
        y = df['open'].fillna(method='ffill')
        y = y.values.reshape(-1, 1)
        y = open_price_scaler.transform(y)

        X = [y[i - open_price_n_lookback:i].reshape(1, open_price_n_lookback, 1) for i in range(open_price_n_lookback, len(y) + 1)]
        Y = [open_price_scaler.inverse_transform(open_price_model.predict(x).reshape(-1, 1)) for x in X]

        y_predicted = np.array(Y).astype(np.float64).squeeze()
        predicted_open_prices = pd.Series(y_predicted)

        # add prediction to database
        bar_time = prediction_startsfrom
        for predicted_close_price in predicted_close_prices:
            Candlestick.objects.update_or_create(symbol=symbol,
                                                 time=bar_time,
                                                 period=period,
                                                 source=source,
                                                 price_type=price_type,
                                                 defaults={'symbol': symbol,
                                                           'time': bar_time,
                                                           'predicted_close': predicted_close_price,
                                                           'predicted_volume': 1,
                                                           'period': period,
                                                           'source': source,
                                                           'price_type': price_type,
                                                           }
                                                 )
            bar_time += timedelta(days=1)
            if bar_time.isoweekday() == 6:
                bar_time += timedelta(days=1)

        bar_time = prediction_startsfrom
        for predicted_open_price in predicted_open_prices:
            Candlestick.objects.update_or_create(symbol=symbol,
                                                 time=bar_time,
                                                 period=period,
                                                 source=source,
                                                 price_type=price_type,
                                                 defaults={'symbol': symbol,
                                                           'time': bar_time,
                                                           'predicted_open': predicted_open_price,
                                                           'predicted_volume': 1,
                                                           'period': period,
                                                           'source': source,
                                                           'price_type': price_type,
                                                           }
                                                 )
            bar_time += timedelta(days=1)
            if bar_time.isoweekday() == 6:
                bar_time += timedelta(days=1)


def main():
    add_prediction(90)


if __name__ == '__main__':
    main()
