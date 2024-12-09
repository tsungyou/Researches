import pandas as pd
import psycopg2
from datetime import datetime
from config import *
import requests
import warnings
import time
import numpy as np
warnings.filterwarnings("ignore")
import pytz
import matplotlib.pyplot as plt


# da = '2024-09-09'
class SignalGenerator():
    def __init__(self):
        self.init_minute = None
        self.iterator = 0
        self.conn = self.get_db_connection()
        self.cursor = self.conn.cursor()
        self.tz = pytz.timezone('America/New_York')
        self.da = datetime.now(self.tz).strftime("%Y-%m-%d")
    def get_db_connection(self):
        conn = psycopg2.connect(host=DB_HOST, dbname='us', user=DB_USER, password=DB_PASS)
        return conn
    
    def lineNotify(self, da, df, bm_percent, index_name):
        headers = {
            'Authorization': 'Bearer ' + LINE_TOKEN_FIRST_MINUTES
        }
        data = {
            'message':f'''
            {index_name} {bm_percent}
            {da}
            {list(df)}
            '''             
        }
        if index_name == 'us500':
            data = {
            'message':f'''
            {index_name} {bm_percent}
            {da}
            {list(df)}
            ===============
            '''             
            }
        data = requests.post(LINE_URL, headers=headers, data=data)
        self.iterator += 1
    
    def signal_generator_30(self, index_name='us30', benchmark="DIA"):
        try:
            self.cursor.execute(f"SELECT distinct code from public.maincode where listed = '{index_name}';")
            self.conn.commit()
            list_ = [i[0] for i in self.cursor.fetchall()]

            list_str = ','.join([f"'{i}'" for i in list_])
            self.cursor.execute(f"SELECT da, code, cl from public.stock_price_5m where code in ({list_str}) and da >= '{self.da} 09:30:00' and da <= '{self.da} 09:45:00' order by da desc;")
            self.conn.commit()
            res = self.cursor.fetchall()
            df = pd.DataFrame(res)
            df.columns = ['da','code', 'cl']
            pivoted = df.pivot(columns='code', values='cl', index='da')
            pivoted.ffill()

            dft = pd.DataFrame()
            dft['percent'] = np.round((pivoted.iloc[-1, :] / pivoted.iloc[0, :]) - 1, 3)
            dft['price'] = pivoted.iloc[-1, :]
            dft = dft[dft['price'] >= 50]
            dft = dft.sort_values(by='percent', ascending=False)
            if (pivoted[benchmark].iloc[-1] / pivoted[benchmark].iloc[0]) - 1 > 0:
                t = dft.tail()
            else:
                t = dft.head()
            time = pivoted.index[-1]
            bm_percent = np.round((pivoted[benchmark].iloc[-1] / pivoted[benchmark].iloc[0]) - 1, 5)
            self.lineNotify(time, t.index, bm_percent, index_name)
        except:
            return None
    def flow_controller(self):
        self.cursor.execute("SELECT da from public.stock_price_5m order by da desc limit 1;")
        self.conn.commit()
        return self.cursor.fetchone()[0]
    
    def png_to_line(self):
        tz = pytz.timezone('America/New_York')
        da = datetime.now(tz).strftime("%Y-%m-%d")
        self.cursor.execute(f"SELECT da, code, op from public.stock_price_5m where code in ('VOO', 'DIA', 'QQQ') and da >= '{da} 09:30:00' order by da desc limit 60;")
        self.conn.commit()
        res = self.cursor.fetchall()
        df = pd.DataFrame(res)
        df.columns = ['da','code', 'cl']
        pivoted = df.pivot(columns='code', values='cl', index='da')
        pivoted.ffill()
        ret = (1 + pivoted.pct_change()).cumprod()
        plt.plot(ret, label=ret.columns)
        plt.legend()
        a = '/Users/tp_mini/Desktop/IB/DailyRunning/test1.png'
        plt.savefig(a)
        headers = {
            'Authorization': 'Bearer ' + LINE_TOKEN_FIRST_MINUTES,
            'Content-Type': 'application/json'
        }
        data = {
            'messages': [
                {
                    'type': 'image',
                    'originalContentUrl': a,
                }
            ]
        }
        data = requests.post(LINE_URL, headers=headers, data=data)
        self.iterator += 1
if __name__ == "__main__":
    sg = SignalGenerator()
    while True:
        print(datetime.now())
        da = sg.flow_controller()
        if sg.init_minute != da:
            sg.init_minute = da
            sg.signal_generator_30(index_name='us30', benchmark='DIA')
            sg.signal_generator_30(index_name='us100', benchmark='QQQ')
            sg.signal_generator_30(index_name='us500', benchmark='VOO')
            # sg.png_to_line()
        else:
            time.sleep(60 - datetime.now().second + 2)