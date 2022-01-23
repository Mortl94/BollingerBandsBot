import pandas as pd
from binance.client import Client
from binance import AsyncClient, BinanceSocketManager
import datetime
import datetime as dt

from sqlalchemy import create_engine
import sqlalchemy
import time

engine = create_engine('sqlite://///home/martinfendl/bollinger2/CryptoDB48.db')


client = Client()


coins = ['BTC','ETH','LTC']


def sma(data, window):
    return(data.rolling(window = window).mean())

def bollinger_band(data, sma, window, nstd):
    std = data.rolling(window = window).std()
    upper_band = sma + std * nstd
    lower_band = sma - std * nstd
    
    return upper_band, lower_band

def gather_data(symbols,start_n_hours_ago):
    merge = False
    for symbol in symbols:
        binance_time = dt.datetime.now() + dt.timedelta(hours=1)
        klines = client.get_historical_klines(symbol=f'{symbol}USDT', 
                                              interval=client.KLINE_INTERVAL_1HOUR, 
                                              start_str=str(binance_time-dt.timedelta(hours=start_n_hours_ago)))
        cols = ['OpenTime',
                f'{symbol}-USD_Open',
                f'{symbol}-USD_High',
                f'{symbol}-USD_Low',
                f'{symbol}-USD_Close',
                f'{symbol}-USD_volume',
                'CloseTime',
                f'{symbol}-QuoteAssetVolume',
                f'{symbol}-NumberOfTrades',
                f'{symbol}-TBBAV',
                f'{symbol}-TBQAV',
                f'{symbol}-ignore']

        df = pd.DataFrame(klines,columns=cols)

        if merge == True:
            dfs = pd.merge(df,dfs,how='inner',on=['OpenTime','CloseTime'])
        else:
            dfs = df
            merge = True

    dfs['OpenTime'] = [dt.datetime.fromtimestamp(ts / 1000) for ts in dfs['OpenTime']]
    dfs['CloseTime'] = [dt.datetime.fromtimestamp(ts / 1000) for ts in dfs['CloseTime']]

    for col in dfs.columns:
        if not 'Time' in col:
            dfs[col] = dfs[col].astype(float)

    for symbol in symbols:
        dfs[f'{symbol}_sma'] = sma(dfs[f'{symbol}-USD_Close'],window=20)
        dfs[f'{symbol}_upper_band'], dfs[f'{symbol}_lower_band'] = bollinger_band(data=dfs[f'{symbol}-USD_Close'],
                                                                                  sma=dfs[f'{symbol}_sma'],
                                                                                  window=20,
                                                                                  nstd=3)

    dfs.dropna(inplace=True)
    
    return dfs


data = gather_data(coins,48)


data.to_sql('48hourData', engine, if_exists='replace', index=False)


print(f'Data was stored {dt.datetime.now()}')


