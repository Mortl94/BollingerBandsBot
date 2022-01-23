# BollingerBandsBot

!Important!This is no investing advice!

This Bot downloads 48h crypto data every hour and looks if a buy or sell signal appears. If so, it sends a buy/sell request to the binance api. So you need to create a Binance API key.

To run the scripts you have to shedule them (i used Conjobs). LiveTrading.py every 30 seconds (or even less) and Collect48.py every first minute of the hour.

* * * * * LiveTrading.py
* * * * * sleep 30; LiveTrading.py
1 * * * * Collect48.py

Buy Signal:
Current price < lower band

Sell Signal:
Current price > upper band

Bollinger Bands strategy:
https://www.babypips.com/learn/forex/bollinger-bands

I also implemented a Telegram Bot, which sends me a message everytime a order has been placed:
https://medium.com/@ManHay_Hong/how-to-create-a-telegram-bot-anda-send-messages-with-python-4cf314d9fa3e

!This is no investing advice!

Have fun getting messages of your own trading bot :D 
