
import requests
import pandas as pd
import psycopg2
from psycopg2 import sql
import time
from datetime import datetime
from config import DB_HOST, DB_NAME, DB_PASS, DB_USER
import warnings
warnings.filterwarnings("ignore")
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
            print("Connection Successful!")
        print("Connection already existed")
        return None
    def twse_update(self):
        '''
        url     : https://www.twse.com.tw/zh/indices/taiex/mi-5min-hist.html
        url_json: https://www.twse.com.tw/rwd/zh/TAIEX/MI_5MINS_HIST?date=20240701&response=json
        '''
        list_ = []
        query = sql.SQL("select da from price where code = 'TWSE Index' order by da desc limit 1;")
        self.cursor.execute(query)
        rows = self.cursor.fetchone()
        da_newest = rows[0]
        newest_mo = da_newest.month
        current_mo = self.month
        for mo in range(current_mo - newest_mo + 1):
            try:
                month = f"0{current_mo}" if current_mo < 10 else current_mo
                url_twse = f"https://www.twse.com.tw/rwd/zh/TAIEX/MI_5MINS_HIST?date={self.year}{month}01&response=json"
                res = requests.get(url_twse)
                js = res.json()
                list_.append(js['data'])
            except:
                print(js)
            current_mo += 1
        list_list = sum(list_, [])
        df = pd.DataFrame(list_list, columns=['da', 'op', 'hi', 'lo', 'cl'])
        def convert_to_2024(da):
            year, month, day = da.split("/")
            return pd.to_datetime(f"{int(year)+1911}-{month}-{day}")
        df['da'] = df['da'].apply(convert_to_2024)
        for i in range(1, len(df.columns)):
            df.iloc[:, i] = df.iloc[:, i].apply(lambda x: float(x.replace(",", "")))
        appending = df[df['da'] > da_newest]
        if len(appending) == 0:
            print("nothing to append for TWSE")
        else:
            appending.insert(loc=1, column='vol_share', value=[0]*len(appending))
            appending.insert(loc=2, column='vol', value=[0]*len(appending))
            appending['code'] = "TWSE Index"
            self.insert_df_into_db(appending, table='public.price')

    def twotci_update(self=None):
        '''
        url     : https://www.tpex.org.tw/web/stock/iNdex_info/inxh/Inx.php?l=zh-tw
        url_json: https://www.tpex.org.tw/web/stock/iNdex_info/inxh/Inx_result.php?l=zh-tw&d=113/06/01
        '''
        list_ = []
        query = sql.SQL("select da from price where code = 'TWOTCI Index' order by da desc limit 1;")
        self.cursor.execute(query)
        rows = self.cursor.fetchone()
        da_newest = rows[0]
        newest_mo = da_newest.month
        current_mo = self.month
        for mo in range(current_mo - newest_mo + 1):
            month = f"0{current_mo}" if current_mo < 10 else current_mo
            try:
                url_twotci = f'https://www.tpex.org.tw/web/stock/iNdex_info/inxh/Inx_result.php?l=zh-tw&d={self.year-1911}/{month}/01'
                res = requests.get(url_twotci)
                js = res.json()
                list_.append(js['aaData'])
            except KeyError:
                time.sleep(2)
                print("again for ", self.year , month)
                mo = f"0{month}" if month < 10 else month
                url_twotci = f'https://www.tpex.org.tw/web/stock/iNdex_info/inxh/Inx_result.php?l=zh-tw&d={self.year-1911}/{mo}/01'
                res = requests.get(url_twotci)
                js = res.json()
                list_.append(js['aaData'])

        list_list = sum(list_, [])
        df = pd.DataFrame(list_list, columns=['da', 'op', 'hi', 'lo', 'cl', 'code'])

        def convert_to_2024(da):
            year, month, day = da.split("/")
            return pd.to_datetime(f"{int(self.year)}-{month}-{day}")
        df['da'] = df['da'].apply(convert_to_2024)

        for i in range(1, len(df.columns)):
            df.iloc[:, i] = df.iloc[:, i].apply(lambda x: float(x.replace(",", "")))
        appending = df[df['da'] > da_newest]
        if len(appending) == 0:
            print("nothing to append for TWOTCI")
        else:
            appending.insert(loc=1, column='vol_share', value=[0]*len(appending))
            appending.insert(loc=2, column='vol', value=[0]*len(appending))
            appending['code'] = "TWOTCI Index"
            self.insert_df_into_db(appending, table='public.price')

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
    obj.twse_update()
    obj.twotci_update()