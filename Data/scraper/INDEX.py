
import requests # type: ignore
from bs4 import BeautifulSoup # type: ignore
import pandas as pd # type: ignore
import psycopg2 # type: ignore
from psycopg2 import sql # type: ignore
from tqdm import tqdm # type: ignore
import time
from datetime import datetime
from config import DB_HOST, DB_NAME, DB_PASS, DB_USER

class INDEX(object):
    def __init__(self):
        self.conn = None
        self.cursor = None    
        self.db_init_year_index = 2015
        self.year = datetime.now().year
        self.month = datetime.now().month
        self._connection()
    def _connection(self):
        if self.conn == None:
            print(f"Connecting to database {DB_NAME}...")
            conn = psycopg2.connect(host=DB_HOST, dbname=DB_NAME, user=DB_USER, password=DB_PASS)
            self.conn = conn
            self.cursor = self.conn.cursor()
        print("Connection already existed")
        return None
    def twse_init(self):
        '''
        url     : https://www.twse.com.tw/zh/indices/taiex/mi-5min-hist.html
        url_json: https://www.twse.com.tw/rwd/zh/TAIEX/MI_5MINS_HIST?date=20240701&response=json
        '''
        start = 2015
        list_  = []
        for year in tqdm(range(2024, 2015, -1), desc='TWSE from 2024 to 2015'):
            limit_month = self.month if year == self.year else 12
            for month in range(limit_month, 0, -1):
                try:
                    mo = f"0{month}" if month < 10 else month
                    url_twse = f"https://www.twse.com.tw/rwd/zh/TAIEX/MI_5MINS_HIST?date={year}{mo}01&response=json"
                    res = requests.get(url_twse)
                    js = res.json()
                    list_.append(js['data'])
                except KeyError:
                    time.sleep(2)
                    print("again for ", year , month)
                    mo = f"0{month}" if month < 10 else month
                    url_twse = f"https://www.twse.com.tw/rwd/zh/TAIEX/MI_5MINS_HIST?date={year}{mo}01&response=json"
                    res = requests.get(url_twse)
                    js = res.json()
                    list_.append(js['data'])
        list_list = sum(list_, [])
        df = pd.DataFrame(list_list, columns=['da', 'op', 'hi', 'lo', 'cl'])

        def convert_to_2024(da):
            year, month, day = da.split("/")
            return f"{int(year)+1911}-{month}-{day}"
        df['da'] = df['da'].apply(convert_to_2024)
        for i in range(1, len(df.columns)):
            df.iloc[:, i] = df.iloc[:, i].apply(lambda x: float(x.replace(",", "")))
        df.insert(loc=1, column='vol_share', value=[0]*len(df))
        df.insert(loc=2, column='vol', value=[0]*len(df))
        df['code'] = "TWSE Index"
        self.insert_df_into_db(df, table='public.price')

    def twotci_init(self=None):
        '''
        url     : https://www.tpex.org.tw/web/stock/iNdex_info/inxh/Inx.php?l=zh-tw
        url_json: https://www.tpex.org.tw/web/stock/iNdex_info/inxh/Inx_result.php?l=zh-tw&d=113/06/01
        '''
        list_  = []
        for year in tqdm(range(113, 104, -1), desc='TWOTCI from 113 to 104'):
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
        df = pd.DataFrame(list_list, columns=['da', 'op', 'hi', 'lo', 'cl', 'code'])

        def convert_to_2024(da):
            year, month, day = da.split("/")
            return f"{int(year)}-{month}-{day}"
        df['da'] = df['da'].apply(convert_to_2024)

        for i in range(1, len(df.columns)):
            df.iloc[:, i] = df.iloc[:, i].apply(lambda x: float(x.replace(",", "")))
        df.insert(loc=1, column='vol_share', value=[0]*len(df))
        df.insert(loc=2, column='vol', value=[0]*len(df))
        df['code'] = "TWOTCI Index"
        self.insert_df_into_db(df, table='public.price')

    def insert_df_into_db(self, df: pd.DataFrame, table='public.block_trade'):
        df_list = df.values.tolist()
        if table == 'public.block_trade':
            self.cursor.executemany(f'''
            INSERT INTO {table} (code, cname, type_, cl, vol_share, vol, da)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            ''', df_list)
        elif table == 'public.maincode':
            self.cursor.executemany(f'''
            INSERT INTO {table} (code, cname, listed)
            VALUES (%s, %s, %s)
            ''', df_list)
        elif table == 'public.price':
            self.cursor.executemany(f'''
            INSERT INTO {table} (da, vol_share, vol, op, hi, lo, cl, code)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            ''', df_list)     
        self.conn.commit()
    
if __name__ == "__main__":
    obj = INDEX()
    obj.twse_init()
    obj.twotci_init()