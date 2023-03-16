# crypto-bot
Crypto trading bot based on Freqtrade. 

Run bot:  
`docker-compose up -d`

Download data:  
`docker-compose run --rm freqtrade download-data --pairs <coin_pair> --exchange binance --days <days> -t <bars_time>`
  
Backtest:  
  (make sure to download data first). 
`docker-compose run --rm freqtrade backtesting --config user_data/config.json --strategy extreme_rsi_macd_cross --timerange <YYYYMMDD-YYYYMMDD> -i <bars_time>`
  
Save plot:  
  (make sure to use plotting image)  
`docker-compose run --rm freqtrade plot-dataframe --strategy <strategy> -p <coin_pair>`
