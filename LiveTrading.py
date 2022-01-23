#!/usr/bin/env python3
# coding: utf-8


from datetime import datetime, timedelta
import pandas as pd
from binance.client import Client
import time
from binance.exceptions import *
from sqlalchemy import create_engine
import math


# place your Binance API key and secret here
api_key = ""
secret_key = ""


client = Client(api_key, secret_key)


# replace with the path to directory
engine = create_engine("sqlite://///pathtodirectory/CryptoDB48.db")


def sma(data, window):
    return data.rolling(window=window).mean()


def bollinger_band(data, sma, window, nstd):
    std = data.rolling(window=window).std()
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

    # place chat id and bot token here
    bot_token = ""
    bot_chatID = ""
    send_text = f"https://api.telegram.org/bot{bot_token}/sendMessage?chat_id={bot_chatID}&parse_mode=Markdown&text={bot_message}"
    response = requests.get(send_text)

    return response.json()


symbols = ["BTC", "ETH", "LTC"]

# we need the precision to send the right amount of deciamals to the binance api
precision = {}

for symbol in symbols:
    # get filters
    sym_info = client.get_symbol_info(f"{symbol}USDT")
    filters = sym_info["filters"]
    # loop through filters to get LOT_SIZE
    for f in filters:
        if f["filterType"] == "LOT_SIZE":
            lot_size = f["stepSize"]
            # convert LOT-Size into decimals by cutting the first 2 indexes and cut again after the index of '1'
            precision[symbol] = len(lot_size[1 : lot_size.index("1")])
            break


def get_states(df, symbols):
    states = {}

    for symbol in symbols:
        if df[f"{symbol}-USD_Close"].iloc[-1] < df[f"{symbol}_lower_band"].iloc[-1]:
            states[symbol] = "below"
        elif df[f"{symbol}-USD_Close"].iloc[-1] > df[f"{symbol}_upper_band"].iloc[-1]:
            states[symbol] = "above"
        else:
            states[symbol] = "inside"

    return states


account = client.get_account()


account["balances"]
balances = [bal for bal in account["balances"] if float(bal["free"]) > 0]


highest_free = 0
highest_index = 0
for i, balance in enumerate(balances):
    asset_name = balance["asset"]
    if asset_name != "USDT":
        prize = float(
            client.get_orderbook_ticker(symbol=f"{asset_name}USDT")["askPrice"]
        )
        value_in_usdt = prize * float(balance["free"])
    else:
        value_in_usdt = float(balance["free"])
    if value_in_usdt > highest_free:
        highest_free = value_in_usdt
        highest_index = i

balance_unit = balances[highest_index]["asset"]
buy_amount = float(balances[highest_index]["free"])

# Alle 30 Sekunden aktualisieren
df_from_sql = pd.read_sql('select * from "48hourData"', engine)
states = get_states(df_from_sql, symbols)
try:
    # Looking to Buy
    if balance_unit == "USDT":
        for symbol in symbols:
            ask_price = float(
                client.get_orderbook_ticker(symbol=f"{symbol}USDT")["askPrice"]
            )
            lower_band = df_from_sql[f"{symbol}_lower_band"].iloc[-1]
            if ask_price < lower_band and states[symbol] == "inside":  # buy signal
                print(f"Buy order placed:")
                buy_order = client.order_limit_buy(
                    symbol=f"{symbol}USDT",
                    quantity=truncate(buy_amount / ask_price, precision[symbol]),
                    price=ask_price,
                )
                print(buy_order)
                try:
                    telegram_bot_sendtext(f"Buy order placed: {buy_order}")
                except:
                    print("Telegram Bot versenden hat nicht funktioniert")

    # Looking to sell
    if balance_unit != "USDT":
        bid_price = float(
            client.get_orderbook_ticker(symbol=f"{balance_unit}USDT")["bidPrice"]
        )
        upper_band = df_from_sql[f"{balance_unit}_upper_band"].iloc[-1]
        if bid_price > upper_band and states[balance_unit] == "inside":  # sell signal
            sell_order = client.order_market_sell(
                symbol=f"{balance_unit}USDT",
                quantity=truncate(float(buy_amount), precision[balance_unit]),
            )
            print(sell_order)
            try:
                telegram_bot_sendtext(f"Sell order placed: {sell_order}")
            except:
                print("Telegram Bot versenden hat nicht funktioniert")

except BinanceAPIException as e:
    print(e.status_code)
    print(e.message)
