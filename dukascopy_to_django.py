#!/home/paullam/fyp/fypenv/bin/python3
import requests
import struct
from lzma import LZMADecompressor, FORMAT_AUTO

res = requests.get('https://datafeed.dukascopy.com/datafeed/EURUSD/2021/05/01/BID_candles_min_1.bi5', stream=True)
print(res.headers.get('content-type'))

rawdata = res.content

decomp = LZMADecompressor(FORMAT_AUTO, None, None)
decompresseddata = decomp.decompress(rawdata)

temp_bar = {}
shift = 1
for i in range(shift * 60, (shift + 1) * 60):
    time, open, high, low, close, volumn = struct.unpack('!5If', decompresseddata[i * 24: (i + 1) * 24])
    print(time, open, high, low, close, volumn, sep=', ')
    if i == shift * 60:
        temp_bar['time'] = time
        temp_bar['open'] = open
        temp_bar['high'] = high
        temp_bar['low'] = low
        temp_bar['close'] = close
    elif i == (shift + 1) * 60 - 1:
        temp_bar['close'] = close
    else:
        if high > temp_bar['high']:
            temp_bar['high'] = high
        if low < temp_bar['low']:
            temp_bar['low'] = low
    temp_bar['volumn'] = temp_bar.get('volumn', 0) + volumn

print(temp_bar.values())
