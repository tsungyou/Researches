import pandas as pd
import psycopg2
from datetime import datetime
from config import *
import requests
import warnings
import time
import numpy as np
warnings.filterwarnings("ignore")

class SignalGenerator():
    def __init__(self):
        self.list_ = None
        self.init_minute = None
        self.iterator = 0
        self.rolling = 5
        self.benchmark = 2
        self.benchmark_index = "DIA"
        self.conn = self.get_db_connection()
        self.cursor = self.conn.cursor()
        self.get_code_list(index='us30')
    def get_db_connection(self):
        conn = psycopg2.connect(host=DB_HOST, dbname='us', user=DB_USER, password=DB_PASS)
        return conn
    
    def get_code_list(self, index='us30'):
        self.cursor.execute(f"SELECT distinct code from public.maincode where listed = '{index}';")
        self.conn.commit()
        self.list_ = [i[0] for i in self.cursor.fetchall()]
        return None
    def backtest_strat2(self, code):
        self.cursor.execute(f"SELECT da, code, cl from public.stock_price_5m where code in ('{code}', 'DIA') order by da desc limit 50;")
        self.conn.commit()
        res = self.cursor.fetchall()
        df = pd.DataFrame(res)
        df.columns = ['da','code', 'cl']
        pivoted = df.pivot(columns='code', values='cl', index='da')
        if len(pivoted.columns) == 1: return None
        pivoted.ffill()
        ret = pivoted.pct_change()
        ret['ret_diff'] = ret[code] - ret['DIA']
        ret['ret_diff_std'] = ret['ret_diff'].rolling(self.rolling).std() * 100
        ret['ret_diff_mean'] = ret['ret_diff'].rolling(self.rolling).mean() * 100
        ret['stdize_ret_diff'] = abs((ret['ret_diff'] - ret['ret_diff_mean'])/ret['ret_diff_std'])
        ret['code'] = ret[code]
        ret['code1'] = ret[code].shift(1)
        ret['code2'] = ret[code].shift(2)
        ret['code3'] = ret[code].shift(3)
        ret['code4'] = ret[code].shift(4)
        ret['all_positive'] = (ret['code'] > 0) & (ret['code1'] > 0)&(ret['code2'] > 0)&(ret['code3'] > 0)&(ret['code4'] > 0)
        ret['all_negative'] = (ret['code'] < 0) & (ret['code1'] < 0)&(ret['code2'] < 0)&(ret['code3'] < 0)&(ret['code4'] < 0)
        ret['all_pos'] = ret['all_positive'].apply(lambda x: 1 if x else 0)
        ret['all_neg'] = ret['all_negative'].apply(lambda x: -1 if x else 0)
        ret[code] = pivoted[code]
        ret['DIA'] = pivoted['DIA']
        ret['index'] = [i for i in range(len(ret))]
        ret['lag10'] = ret[code].shift(5) 
        ret['direction'] = ret.apply(lambda x: -1 if x[code] > x['lag10'] else 1, axis=1) # -1 if current larger than future but wrong
        ret[f'{code}_30min_future'] = ret[code].shift(-10)
        ret['target_30mins'] = np.round((ret[f'{code}_30min_future'] - ret[code])/ret[code], 3) * ret['direction']
        ret['da'] = pivoted.index
        ret.set_index('index', inplace=True, drop=False)
        last = ret.iloc[-1, :]
        if last['stdize_ret_diff'] >= self.benchmark:
            if  last['direction'] == -1 and last['all_pos'] == 1:
                self.lineNotify(code, last[code], last['direction'] , np.round((last[code] - last['lag10'])/last['lag10'] * 100, 2), last['da'])
            elif last['direction'] == 1 and last['all_neg'] == -1:
                self.lineNotify(code, last[code], last['direction'] , np.round((last[code] - last['lag10'])/last['lag10'] * 100, 2), last['da'])

    def lineNotify(self, code, price, direction, stdsize123, da):
        direction_icon = '📈' if direction == 1 else '📉'
        time_ = datetime.now()
        headers = {
            'Authorization': 'Bearer ' + LINE_US30_TOKEN
        }
        data = {
            'message':f'''
            {direction_icon} {code}({price})
            current time:{time_.minute}:{time_.second}
            signal_time: {da}
            last 5mins diff:{stdsize123}
            '''             
        }
        data = requests.post(LINE_URL, headers=headers, data=data)
        self.iterator += 1
    def signal_generator(self):
        for code in self.list_:
            if code == self.benchmark_index: continue
            self.backtest_strat2(code)
        
    def flow_controller(self):
        self.cursor.execute("SELECT da from public.stock_price_5m order by da desc limit 1;")
        self.conn.commit()
        return self.cursor.fetchone()[0]
if __name__ == "__main__":
    sg = SignalGenerator()
    while True:
        print(datetime.now())
        da = sg.flow_controller()
        if sg.init_minute != da:
            sg.init_minute = da
            sg.signal_generator()
        else:
            time.sleep(60 - datetime.now().second + 2)