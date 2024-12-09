import requests
from bs4 import BeautifulSoup
import os
import pandas as pd
import numpy as np
import yfinance as yf
import json

class DbInitGoodInfo(object):
    __slots__ = ("ticker_list", "chromedriver_path")
    os.chdir("../db")
    def __init__(self):
        pass


    def _get_balance_sheet(self, ticker=None):
        if ticker is None:
            print("ticker happens to be None, recheck that...")
            return None
        else:
            return True
        
    def get_ticker_list(self):
        url_stock_list_goodinfo = "https://goodinfo.tw/tw/Lib.js/StockTW_ID_NM_List.js"
        res = requests.get(url_stock_list_goodinfo)
        soup = BeautifulSoup(res.text, 'lxml')
        list_ = soup.string.split("','")
        list_4 = [i.split(" ")[0] for i in list_[2:] if len(i.split(" ")[0]) == 4][:2179]
        ticker_dict = {}
        for ticker in list_4:
            df = yf.download(f"{ticker}.TW", start='2024-07-10', progress=False)
            if len(df) != 0:
                ticker_dict[ticker] = "TW"
            else:
                df = yf.download(f"{ticker}.TWO", start='2024-07-12', progress=False)
                if len(df) != 0:
                    ticker_dict[ticker] = "TWO"
                else:
                    ticker_dict[ticker] = "0"
        with open("tw/symbol/goodinfo_tw.json", "w") as f:
            json.dump({i:value for i, value in ticker_dict.items() if value == "TW"}, f, indent=4)

        with open("tw/symbol/goodinfo_two.json", "w") as f:
            json.dump({i:value for i, value in ticker_dict.items() if value == "TWO"}, f, indent=4)
        return None

if __name__ == "__main__":
    obj = DbInitGoodInfo()
    print(obj.__slots__)