#%%
from fubon_neo.sdk import FubonSDK, Order

sdk = FubonSDK()

response = sdk.login("H124181635", "j56137642", "C:/CAFubon/H124181635/H124181635.pfx", "j56137642")  # 需登入後，才能取得行情權限

sdk.init_realtime() # 建立行情連線

reststock = sdk.marketdata.rest_client.stock  
reststock.intraday.tickers(type='EQUITY', exchange="TPEx", isDisposition=True)
# %%
import requests as req
import pandas as pd

# bus_table = pd.read_html(r"https://goodinfo.tw/tw2/StockList.asp?MARKET_CAT=%E6%99%BA%E6%85%A7%E9%81%B8%E8%82%A1&INDUSTRY_CAT=%E5%85%A8%E9%A1%8D%E4%BA%A4%E5%89%B2%E8%82%A1")# %%
#%%

reststock.intraday.tickers(type='WARRANT', exchange="TWSE")
# %%