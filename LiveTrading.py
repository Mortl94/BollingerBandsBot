#!/usr/bin/env python3
# coding: utf-8

# In[57]:


from datetime import datetime, timedelta
import pandas as pd
from binance.client import Client
import time
from binance.exceptions import *
from sqlalchemy import create_engine
import math


# In[38]:


api_key = 'lH4RkgxlXw0cPUts7Ma0HgXJ0Qy1zUZWjuMnga0piGwm55DgHcy3RVelMriIcbyj'
secret_key = '2QhlWDGgyjGkS0XiuLEiE5xb5sQHR212PYpB1gD7gl8hMElghN4X046Iua7Lpc7q'


# In[39]:


client = Client(api_key, secret_key)


# In[40]:


engine = create_engine('sqlite://///home/martinfendl/bollinger2/CryptoDB48.db')


# In[41]:


def sma(data, window):
    return(data.rolling(window = window).mean())

def bollinger_band(data, sma, window, nstd):
    std = data.rolling(window = window).std()
    upper_band = sma + std * nstd
    lower_band = sma - std * nstd
    
    return upper_band, lower_band

def truncate(number, decimals=0):
    """
    Returns a value truncated to a specific number of decimal places.
    https://stackoverflow.com/questions/783897/how-to-truncate-float-values
    credit: nullstellensatz
    """
    if not isinstance(decimals, int):
        raise TypeError("decimal places must be an integer.")
    elif decimals < 0:
        raise ValueError("decimal places has to be 0 or more.")
    elif decimals == 0:
        return math.trunc(number)

    factor = 10.0 ** decimals
    return math.trunc(number * factor) / factor

def telegram_bot_sendtext(bot_message):
    import requests
    bot_token = '5069745599:AAHUSR3TUKlY9WV2leeKcLrseGfPbPDsgTs'
    bot_chatID = '1012337950'
    send_text = f"https://api.telegram.org/bot{bot_token}/sendMessage?chat_id={bot_chatID}&parse_mode=Markdown&text={bot_message}"
    response = requests.get(send_text)

    return response.json()

# In[42]:
symbols = ['BTC', 'ETH', 'LTC']

precision = {}


for symbol in symbols:
    #get filters
    sym_info = client.get_symbol_info(f'{symbol}USDT')
    filters = sym_info['filters']
    #loop through filters to get LOT_SIZE
    for f in filters:
        if f['filterType'] == 'LOT_SIZE':
            lot_size = (f['stepSize'])
            #convert LOT-Size into decimals by cutting the first 2 indexes and cut again after the index of '1' 
            precision[symbol] = len(lot_size[1:lot_size.index('1')])
            break

def get_states(df,symbols):
    states = {}

    for symbol in symbols:
        if df[f'{symbol}-USD_Close'].iloc[-1] < df[f'{symbol}_lower_band'].iloc[-1]:
            states[symbol] = 'below'
        elif df[f'{symbol}-USD_Close'].iloc[-1] > df[f'{symbol}_upper_band'].iloc[-1]:
            states[symbol] = 'above'
        else:
            states[symbol] = 'inside'
    
    return states


# In[43]:


account = client.get_account()


# In[44]:


account['balances']
balances = [bal for bal in account['balances'] if float(bal['free']) > 0]


# In[46]:


highest_free = 0
highest_index = 0
for i,balance in enumerate(balances):
    asset_name = balance['asset']
    if asset_name != "USDT":
        prize = float(client.get_orderbook_ticker(symbol = f'{asset_name}USDT')['askPrice'])
        value_in_usdt = prize * float(balance['free'])
    else:
        value_in_usdt = float(balance['free'])
    if value_in_usdt > highest_free:
        highest_free = value_in_usdt
        highest_index = i

# In[48]:


balance_unit = balances[highest_index]['asset']
buy_amount = float(balances[highest_index]['free'])

# In[54]:


#Alle 30 Sekunden aktualisieren
df_from_sql = pd.read_sql('select * from "48hourData"', engine)
states = get_states(df_from_sql,symbols)
try:
    if balance_unit == 'USDT': # looking to buy
        for symbol in symbols:
            ask_price = float(client.get_orderbook_ticker(symbol = f'{symbol}USDT')['askPrice'])
            lower_band = df_from_sql[f'{symbol}_lower_band'].iloc[-1]
            if ask_price < lower_band and states[symbol] == 'inside': #buy signal
                print(f'Buy order placed:')
                buy_order = client.order_limit_buy(symbol=f'{symbol}USDT',
                                                  quantity=truncate(buy_amount / ask_price, precision[symbol]),
                                                  price = ask_price)
                print(buy_order)
                try:
                    telegram_bot_sendtext(f'Buy order placed: {buy_order}')
                except:
                    print('Telegram Bot versenden hat nicht funktioniert')

                # start = datetime.now()
                # while True:
                #     time.sleep(1)
                #     buy_order = client.get_order(symbol=buy_order['symbol'], orderId=buy_order['orderId'])

                #     seconds_since_buy = (datetime.now() - start).seconds

                #     # resolve buy order
                #     if float(buy_order['executedQty']) == 0 and seconds_since_buy > 60*60:
                #         # no fill
                #         client.cancel_order(symbol=buy_order['symbol'], orderId=buy_order['orderId'])
                #         print('Order not filled after 1 hour, cancelled.')
                #         print('\n')
                #         break

                #     if float(buy_order['executedQty']) != 0 and float(buy_order['executedQty']) != float(buy_order['origQty']) and seconds_since_buy > 60*60:
                #         # partial fill
                #         client.cancel_order(symbol=buy_order['symbol'], orderId=buy_order['orderId'])
                #         balance_unit = symbol
                #         print('Order partially filled after 1 hour, cancelled the rest and awaiting sell signal.')
                #         print('\n')
                #         break

                #     if float(buy_order['executedQty']) ==  float(buy_order['origQty']):
                #         # completely filled
                #         balance_unit = symbol
                #         print('Order filled:')
                #         print(buy_order)
                #         print('\n')
                #         break
                #break

    if balance_unit != 'USDT': # looking to sell
        bid_price = float(client.get_orderbook_ticker(symbol = f'{balance_unit}USDT')['bidPrice'])
        upper_band = df_from_sql[f'{balance_unit}_upper_band'].iloc[-1]
        if bid_price > upper_band and states[balance_unit] == 'inside': #sell signal
            sell_order = client.order_market_sell(symbol=f'{balance_unit}USDT',
                                    quantity=truncate(float(buy_amount), precision[balance_unit]))
            print(sell_order)
            try:
                telegram_bot_sendtext(f'Sell order placed: {sell_order}')
            except:
                print('Telegram Bot versenden hat nicht funktioniert')

except BinanceAPIException as e:
    print(e.status_code)
    print(e.message)


# In[ ]:





