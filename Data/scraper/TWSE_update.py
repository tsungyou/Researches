import requests # type: ignore
import pandas as pd # type: ignore
import psycopg2 # type: ignore
from psycopg2 import sql # type: ignore
from datetime import datetime, timedelta
from config import DB_HOST, DB_NAME, DB_PASS, DB_USER

class TWSE_update(object):
    def __init__(self):
        self.conn = None
        self.year = datetime.now().year
        self.month = datetime.now().month
    def _connection(self):
        if self.conn == None:
            print(f"Connecting to database {DB_NAME}...")
            conn = psycopg2.connect(host=DB_HOST, dbname=DB_NAME, user=DB_USER, password=DB_PASS)
            self.conn = conn
            print("Connection Successful!")
            return None
        print("Connection already existed")
        return None
    
    def block_trading_update(self):
        self._connection()
        cursor = self.conn.cursor()
        query = sql.SQL('select da from block_trade order by da desc limit 1;')
        cursor.execute(query)
        rows = cursor.fetchone()
        da_newest = rows[0]
        print("block trade start since", da_newest)
        final_list = []
        for i in range((datetime.now() - da_newest).days):
            try:
                da = da_newest + timedelta(i+1)
                year, mo, date = da.year, da.month, da.day
                mo = f"0{mo}" if mo < 10 else mo
                date = f"0{date}" if date < 10 else date
                url = f'https://www.twse.com.tw/rwd/zh/block/BFIAUU?date={year}{mo}{date}&selectType=S&response=json'
                res = requests.get(url)
                res.raise_for_status()
                data = res.json().get('data', [])
                da = res.json()['title'].replace("年", "-").replace("月", "-")[:9]
                year = str(int(da[:3]) + 1911)
                da = year + da[3:]
                data = [i + [da] for i in data[:-1]]
                for j in data:
                    final_list.append(j)
                df = pd.DataFrame(final_list)
                df[3] = df[3].str.replace(',', '')
                df[3] = df[3].apply(lambda x: float(x) if x != '' else 0.0)
                df[4] = df[4].str.replace(',', '').astype(int)
                df[5] = df[5].str.replace(',', '').astype(int)
                df[6] = pd.to_datetime(df[6], format='%Y-%m-%d') 
                
                df.columns = ['code', 'codename', 'type_', 'cl', 'vol_share', 'vol', 'da']
                df = df.drop_duplicates(subset=['code', 'da'])
                self.insert_df_into_db(df, cursor)
            except Exception as e:
                print(f"no data to update for block_trading, {year}{mo}{date}, passed")
    def stock_price_update(self):
        pass
    
    def insert_df_into_db(self, df: pd.DataFrame, cursor):
        df_list = df.values.tolist()
        cursor.executemany('''
        INSERT INTO public.block_trade (code, cname, type_, cl, vol_share, vol, da)
        VALUES (%s, %s, %s, %s, %s, %s, %s)
        ''', df_list)
        self.conn.commit()
        print("commit to block_trade successful")
        return None
if __name__ == "__main__":
    obj = TWSE_update()
    obj.block_trading_update()