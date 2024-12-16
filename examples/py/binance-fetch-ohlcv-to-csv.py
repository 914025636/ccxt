# -*- coding: utf-8 -*-

import os
import sys
import csv

# -----------------------------------------------------------------------------

root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.append(root + '/python')

import ccxt  # noqa: E402


# -----------------------------------------------------------------------------
class MyBinance(ccxt.binance):
    def parse_ohlcv(self, ohlcv, market=None):
        #Date,Time,Open,High,Low,Close,Volume,OpenInterest
        #2006-01-02,09:05:00,3578.73,3587.88,3578.73,3582.99,0,0
        #
        #     [
        #         1591478520000,
        #         "0.02501300",
        #         "0.02501800",
        #         "0.02500000",
        #         "0.02500000",
        #         "22.19000000",
        #         1591478579999,
        #         "0.55490906",
        #         40,
        #         "10.92900000",
        #         "0.27336462",
        #         "0"
        #     ]
        #
        return [
            self.safe_integer(ohlcv, 0),
            self.iso8601(self.safe_integer(ohlcv, 0))[:10],
            self.iso8601(self.safe_integer(ohlcv, 0))[11:19],
            self.safe_number(ohlcv, 1),
            self.safe_number(ohlcv, 2),
            self.safe_number(ohlcv, 3),
            self.safe_number(ohlcv, 4),
            self.safe_number(ohlcv, 5),
            0,
        ]

def retry_fetch_ohlcv(exchange, max_retries, symbol, timeframe, since, limit):
    num_retries = 0
    try:
        num_retries += 1
        ohlcv = exchange.fetch_ohlcv(symbol, timeframe, since, limit)
        # print('Fetched', len(ohlcv), symbol, 'candles from', exchange.iso8601 (ohlcv[0][0]), 'to', exchange.iso8601 (ohlcv[-1][0]))
        return ohlcv
    except Exception:
        if num_retries > max_retries:
            raise  # Exception('Failed to fetch', timeframe, symbol, 'OHLCV in', max_retries, 'attempts')


def scrape_ohlcv(exchange, max_retries, symbol, timeframe, since, limit):
    timeframe_duration_in_seconds = exchange.parse_timeframe(timeframe)
    timeframe_duration_in_ms = timeframe_duration_in_seconds * 1000
    timedelta = limit * timeframe_duration_in_ms
    now = exchange.milliseconds()
    all_ohlcv = []
    fetch_since = since
    while fetch_since < now:
        ohlcv = retry_fetch_ohlcv(exchange, max_retries, symbol, timeframe, fetch_since, limit)
        fetch_since = (ohlcv[-1][0] + 1) if len(ohlcv) else (fetch_since + timedelta)
        all_ohlcv = all_ohlcv + ohlcv
        if len(all_ohlcv):
            print(len(all_ohlcv), 'candles in total from', exchange.iso8601(all_ohlcv[0][0]), 'to', exchange.iso8601(all_ohlcv[-1][0]))
        else:
            print(len(all_ohlcv), 'candles in total from', exchange.iso8601(fetch_since))
    return exchange.filter_by_since_limit(all_ohlcv, since, None, key=0)


def write_to_csv(filename, data):
    with open(filename, mode='w',newline='') as output_file:

        csv_writer = csv.writer(output_file, delimiter=',', quotechar='"', quoting=csv.QUOTE_MINIMAL)
        #遍历data,删除第一列
        for i in range(len(data)):
            del data[i][0]
        #添加一行Date,Time,Open,High,Low,Close,Volume,OpenInterest
        data.insert(0, ['Date', 'Time', 'Open', 'High', 'Low', 'Close', 'Volume', 'OpenInterest'])
        csv_writer.writerows(data)


def scrape_candles_to_csv(filename, exchange_id, max_retries, symbol, timeframe, since, limit):
    # instantiate the exchange by id
    exchange = MyBinance()
    # convert since from string to milliseconds integer if needed
    if isinstance(since, str):
        since = exchange.parse8601(since)
    # preload all markets from the exchange
    exchange.load_markets()
    # fetch all candles
    ohlcv = scrape_ohlcv(exchange, max_retries, symbol, timeframe, since, limit)
    # save them to csv file
    print('Saved', len(ohlcv), 'candles from', exchange.iso8601(ohlcv[0][0]), 'to', exchange.iso8601(ohlcv[-1][0]), 'to', filename)
    write_to_csv(filename, ohlcv)


# -----------------------------------------------------------------------------
# Binance's BTC/USDT candles start on 2017-08-17
scrape_candles_to_csv('binance.csv', 'binance', 3, 'BTC/USDT', '5m', '2024-12-15T00:00:00Z', 100)
