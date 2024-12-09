
import pandas as pd # type: ignore
import psycopg2 # type: ignore
from psycopg2 import sql # type: ignore
import requests # type: ignore
import numpy as np # type: ignore
from datetime import datetime
import warnings
warnings.filterwarnings("ignore")
from config import DB_HOST, DB_NAME, DB_PASS, DB_USER

class SIGNAL(object):
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
    def signal_twse_bullbear(self):
        twse_query = "SELECT da, op, hi, lo, cl from public.price where code = 'TWSE Index' order by da asc;"
        self.cursor.execute(twse_query)
        self.conn.commit()
        twse_res = self.cursor.fetchall()
        twse = pd.DataFrame(twse_res)
        twse.columns = ['da', 'open', 'high', 'low', 'close']
        twse.set_index('da', inplace=True)

        two_query = "SELECT da, op, hi, lo, cl from public.price where code = 'TWOTCI Index' order by da asc;"
        self.cursor.execute(two_query)
        self.conn.commit()
        twotci_res = self.cursor.fetchall()
        twotci = pd.DataFrame(twotci_res)
        twotci.columns = ['da', 'open', 'high', 'low', 'close']
        twotci.set_index('da', inplace=True)

        twotci['ticker'] = "TWOTCI"
        twse['ticker'] = "TWSE"
        df = pd.concat([twse, twotci], axis=0)

        filtered_df = df.copy()
        filtered_df['AvgPrice'] = (filtered_df['high'] + filtered_df['low']) / 2
        filtered_df['Return'] = filtered_df.groupby('ticker')['AvgPrice'].pct_change()
        filtered_df['beta'] = filtered_df.groupby('ticker')['close'].pct_change().shift(-1)

        def rolling_std(group):
            group['return_stddev'] = group['Return'].rolling(window=5).std() * 100
            return group

        filtered_df = filtered_df.groupby('ticker').apply(rolling_std).reset_index(level='ticker', drop=True)

        def calculate_moving_averages(df):
            df['MA20'] = df['close'].rolling(window=20).mean()
            df['MA60'] = df['close'].rolling(window=60).mean()
            return df

        filtered_df = filtered_df.groupby('ticker').apply(calculate_moving_averages).reset_index(level='ticker', drop=True)
        start_date = '2018-01-01'
        twse = filtered_df[(filtered_df['ticker'] == 'TWSE') & (filtered_df.index >= start_date)][['close', 'AvgPrice', "Return", "beta", "return_stddev", "MA20", "MA60"]]
        twotci = filtered_df[(filtered_df['ticker'] == 'TWOTCI') & (filtered_df.index >= start_date)][['close', 'AvgPrice', "Return", "beta", "return_stddev", "MA20", "MA60"]]
        twotci.reset_index(inplace=True)
        twotci['da'] = pd.to_datetime(twotci['da'])
        twse.reset_index(inplace=True)
        twse['da'] = pd.to_datetime(twse['da'])

        def calculate_twotci_metrics(row):
            date = row['da']
            twotci_today = twotci[twotci['da'] == date]
            twotci_next = twotci[twotci['da'] > date].sort_values(by='da').head(1)

            if not twotci_today.empty and not twotci_next.empty:
                twotci_beta = twotci_next['close'].values[0] / twotci_today['close'].values[0] - 1
            else:
                twotci_beta = np.nan
            
            twotci_return_stddev = twotci[(twotci['da'] >= (pd.to_datetime(date) - pd.Timedelta(days=5))) & (twotci['da'] <= date)]['Return'].std() * 100
            twotci_ma20 = twotci[twotci['da'] <= date].sort_values(by='da', ascending=False).head(20)['close'].mean()
            twotci_ma60 = twotci[twotci['da'] <= date].sort_values(by='da', ascending=False).head(60)['close'].mean()
            twotci_cl = twotci_today['close'].values[0] if not twotci_today.empty else np.nan
            
            return pd.Series([twotci_beta, twotci_return_stddev, twotci_ma20, twotci_ma60, twotci_cl])

        final_df = twse.copy()
        final_df[['TWOTCI_BETA', 'TWOTCI_RETURN_STDDEV', 'TWOTCI_MA20', 'TWOTCI_MA60', 'TWOTCI_CL']] = final_df.apply(calculate_twotci_metrics, axis=1)
        final_df.set_index('da', inplace=True, drop=False)


        # 4 dimensions, used for factor timing

        real_exposure = []
        final_df['TWOTCI_RETURN_STDDEV_PREV'] = final_df['TWOTCI_RETURN_STDDEV'].shift(1)
        for index, row in final_df.iterrows():
            if row['TWOTCI_RETURN_STDDEV'] <= 3 and row['TWOTCI_CL'] > row['TWOTCI_MA20']:
                real_exposure.append(1)
            elif row['TWOTCI_RETURN_STDDEV'] <= 1 or row['return_stddev'] >= 3.5:
                real_exposure.append(1)
            elif (row['TWOTCI_RETURN_STDDEV']-row['TWOTCI_RETURN_STDDEV_PREV']) > 0.5 and row['TWOTCI_CL'] > row['TWOTCI_MA60'] and row['TWOTCI_CL'] < row['TWOTCI_MA20']:
                real_exposure.append(1)
            else:
                real_exposure.append(0)

        final_df_insert = final_df[['da', 'close']]
        final_df_insert.insert(loc=0, column='code', value=["TWSE Index"]*len(final_df_insert))
        final_df_insert['signal'] = real_exposure
        final_df_insert['strategy'] = "TWSE bullbear"
        final_df_insert.columns = ['code', 'da', 'cl', 'strategy', 'signal']

        
        da_query = "SELECT da from public.block_code3_deatil where strategy = 'TWSE bullbear' order by da desc limit 1;"
        self.cursor.execute(da_query)
        self.conn.commit()
        signal_da = self.cursor.fetchone()
        if not signal_da:
            self.insert_df_into_db(final_df_insert, table='public.block_code3_deatil')
        else:
            newest_da = signal_da[0]
            final_df_update = final_df_insert[final_df_insert['da'] > newest_da]
            print(final_df_update)
            if len(final_df_update) != 0:
                self.insert_df_into_db(final_df_update, table='public.block_code3_deatil')
            else:
                print("nothing to update for signal TWSE bullbear")
    

    def signal_block_trade(self):
        pass
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
        elif table == 'public.block_code3_deatil':
            self.cursor.executemany(f'''
            INSERT INTO {table} (code, da, cl, signal, strategy)
            VALUES (%s, %s, %s, %s, %s)
            ''', df_list)     
        self.conn.commit()
    
    def create_table_if_not_exist(self, db):
        '''
        db options:
        1. block_trade
        2. signal
        3. stock_code
        4. stock_price
        '''
        create_query = ""
        if db == 'signal':
            create_query = '''
            -- DROP TABLE IF EXISTS public.block_code3_deatil;

            CREATE TABLE IF NOT EXISTS public.block_code3_deatil
            (
                code character varying(50) COLLATE pg_catalog."default",
                da timestamp without time zone NOT NULL,
                cl double precision,
                strategy character varying(50),
                signal character varying(50)
            )
            WITH (
                OIDS = FALSE
            )
            TABLESPACE pg_default;

            ALTER TABLE IF EXISTS public.block_code3_deatil
                OWNER to postgres;

            GRANT ALL ON TABLE public.block_code3_deatil TO postgres;
            '''
        self.cursor.execute(create_query)
        self.conn.commit()
    def signal_pe_pb_yield(self):
        df_row = []
        month = f"0{self.month}" if self.month < 10 else self.month
        for i in range(1, datetime.now().day+1):
            try:
                da = f"0{i}" if i < 10 else i
                date = f"2024{month}{da}"
                url_json = f"https://www.twse.com.tw/rwd/zh/afterTrading/BWIBBU_d?date={date}&selectType=ALL&response=json"
                res = requests.get(url_json)
                data = res.json()['data']
                df  = pd.DataFrame(data)
                df.columns = res.json()['fields']
                df['本益比'] = df['本益比'].apply(lambda x: x.replace(",", ''))
                df = df.replace("-", 1.0)
                df['殖利率(%)'] = df['殖利率(%)'].astype(float)
                df['本益比'] = df['本益比'].astype(float)
                df['股價淨值比'] = df['股價淨值比'].astype(float)
                df['factor'] = df['殖利率(%)'] * 1/df['本益比'] * 1/df['股價淨值比']
                df.sort_values(by='factor',ascending=False, inplace=True)
                df['da'] = f"2024-{month}-{da}"
                df_row.append(df.iloc[0, :])
            except:
                pass

        self.cursor.execute(sql.SQL("Select * from public.block_code3_deatil where strategy = 'pe' order by da desc limit 1;"))
        self.conn.commit()
        res = self.cursor.fetchone()
        df_signal = pd.DataFrame(df_row)
        df_signal = df_signal[['證券代號', 'da', '本益比', 'factor', 'factor']]
        df_signal.columns = ['code', 'da', 'cl', 'signal', 'strategy']
        df_signal['strategy'] = 'pe'
        df_signal['signal'] = 1
        print(df_signal.tail())
        if res:
            df_signal = df_signal[df_signal['da'] > res[0]]
        self.insert_df_into_db(df_signal, table='public.block_code3_deatil')
        print("insert signal pe_pb_yeild success")
if __name__ == "__main__":
    obj = SIGNAL()
    obj.create_table_if_not_exist(db='signal')
    obj.signal_twse_bullbear()
    obj.signal_pe_pb_yield()