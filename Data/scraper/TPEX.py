

import os
import pandas as pd
import requests
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
import os
from tqdm import tqdm
import time

class TPEX(object):
    os.chdir('../db')
    __slots__ = ("year", "da_now")

    def __init__(self):
        self.da_now = datetime.now()
        self.year = self.da_now.year - 1911

    def get_two_stocks(self):
        '''
        example url:
        https://www.tpex.org.tw/web/stock/aftertrading/trading_volume/vol_rank.php?l=zh-tw
        '''
        pass

    def get_gretai50(self):
        '''
        https://www.tpex.org.tw/web/stock/iNdex_info/gretai50/inxhis/rihisqry_result.php?l=zh-tw&d=113/06/01&_=1720688879318
        '''
        ticker = "gretai50"
        list_list = []
        for year in range(self.year, 102, -1):
            limit_month = self.da_now.month+1 if year == self.year else 13
            for month in range(1, limit_month):
                month = f"0{month}" if month < 10 else month
                url_gretai50 = f"https://www.tpex.org.tw/web/stock/iNdex_info/{ticker}/inxhis/rihisqry_result.php?l=zh-tw&d={year}/{month}/01&_=1720688879318"
                response = requests.get(url_gretai50)
               
                data = response.json()['aaData']
                list_list.append(data)
        list_ = sum(list_list, [])
        df = pd.DataFrame(list_)
        df.to_parquet('tw/ind/gretai50.parquet')
        return None
    
    def get_TWOTCI_TPEX(self=None):
        '''
        url     : https://www.tpex.org.tw/web/stock/iNdex_info/inxh/Inx.php?l=zh-tw
        url_json: https://www.tpex.org.tw/web/stock/iNdex_info/inxh/Inx_result.php?l=zh-tw&d=113/06/01
        '''
        list_  = []
        for year in tqdm(range(113, 102, -1), desc='TWOTCI from 113 to 103'):
            limit_month = datetime.now().month+1 if year == datetime.now().year-1911 else 13
            for month in range(1, limit_month):
                try:
                    mo = f"0{month}" if month < 10 else month
                    url_twotci = f'https://www.tpex.org.tw/web/stock/iNdex_info/inxh/Inx_result.php?l=zh-tw&d={year}/{mo}/01'
                    res = requests.get(url_twotci)
                    js = res.json()
                    list_.append(js['aaData'])
                except KeyError:
                    time.sleep(2)
                    print("again for ", year , month)
                    mo = f"0{month}" if month < 10 else month
                    url_twotci = f'https://www.tpex.org.tw/web/stock/iNdex_info/inxh/Inx_result.php?l=zh-tw&d={year}/{mo}/01'
                    res = requests.get(url_twotci)
                    js = res.json()
                    list_.append(js['aaData'])

        list_list = sum(list_, [])
        df = pd.DataFrame(list_list, columns=['da', 'open', 'high', 'low', 'close', 'percentage'])

        def convert_to_2024(da):
            year, month, day = da.split("/")
            return f"{int(year)}-{month}-{day}"
        df['da'] = df['da'].apply(convert_to_2024)

        for i in range(1, len(df.columns)):
            df.iloc[:, i] = df.iloc[:, i].apply(lambda x: float(x.replace(",", "")))
        df.set_index("da", inplace=True)
        df.sort_index(ascending=True, inplace=True)
        df.to_parquet("tw/ind/TWOTCI.parquet")
        return None
    
if __name__ == "__main__":
    obj = TPEX()
    obj.get_TWOTCI_TPEX()