import requests # type: ignore
import pandas as pd # type: ignore
import psycopg2 # type: ignore
from psycopg2 import sql # type: ignore
from tqdm import tqdm # type: ignore
# import yfinance as yf # type: ignore
from datetime import datetime
from config import DB_HOST, DB_NAME, DB_PASS, DB_USER

class TWSE(object):
    def __init__(self):
        self.conn = None
        self.cursor = None    
        self.db_init_year = 2019
        self.year = datetime.now().year
        self.month = datetime.now().month
        self._connection()
    def _connection(self):
        if self.conn == None:
            print(f"Connecting to database {DB_NAME}...")
            conn = psycopg2.connect(host=DB_HOST, dbname=DB_NAME, user=DB_USER, password=DB_PASS)
            self.conn = conn
            self.cursor = self.conn.cursor()
        return None
    
    def block_trading_init(self):
        final_list = []
        for year in range(self.year, self.db_init_year-1, -1):
            month_limit = datetime.now().month + 1 if year == self.year else 13
            
            for date in tqdm(range(1, 367), desc=f'{year}'):
                try:
                    url = f'https://www.twse.com.tw/rwd/zh/block/BFIAUU?date={year}01{date}&selectType=S&response=json'
                    res = requests.get(url)
                    res.raise_for_status()
                    data = res.json().get('data', [])
                    da = res.json()['title'].replace("年", "-").replace("月", "-")[:9]
                    year = str(int(da[:3]) + 1911)
                    da = year + da[3:]
                    
                    if not data: continue
                    data = [i + [da] for i in data[:-1]]
                    for j in data:
                        final_list.append(j)
                except Exception as e:
                    continue

            df = pd.DataFrame(final_list)
            df[3] = df[3].str.replace(',', '')
            df[3] = df[3].apply(lambda x: float(x) if x != '' else 0.0)
            df[4] = df[4].str.replace(',', '').astype(int)
            df[5] = df[5].str.replace(',', '').astype(int)
            df[6] = pd.to_datetime(df[6], format='%Y-%m-%d') 
            
            df.columns = ['code', 'codename', 'type_', 'cl', 'vol_share', 'vol', 'da']
            df = df.drop_duplicates(subset=['code', 'da'])
            self.insert_df_into_db(df, table='public.block_trade')

    # def stock_code_init(self):
    #     url_stock_list_goodinfo = "https://goodinfo.tw/tw/Lib.js/StockTW_ID_NM_List.js"
    #     res = requests.get(url_stock_list_goodinfo)
    #     soup = BeautifulSoup(res.text, 'lxml')
    #     list_1 = soup.string.split("','")
    #     list_4 = [i.split(" ")[0] for i in list_1[2].split("','")[2:]][:2179]
    #     list_4[-1] = list_4[-1].split("'")[0]
    #     list_4_cname = [i.split(" ")[0] for i in list_1[3].split("','")[2:]][:2179]
    #     list_4_cname[-1] = list_4_cname[-1].split("'")[0]

    #     list_listed = []
    #     for ticker in tqdm(list_4):
    #         df = yf.download(f"{ticker}.TW", start='2024-08-01', progress=False)
    #         if len(df) != 0:
    #             list_listed.append("TW")
    #         else:
    #             df = yf.download(f"{ticker}.TWO", start='2024-08-01', progress=False)
    #             if len(df) != 0:
    #                 list_listed.append("TWO")
    #             else:
    #                 list_listed.append("None")
    #     df = pd.DataFrame({
    #         "code": list_4,
    #         "cname": list_4_cname,
    #         "listed": list_listed
    #     })
    #     self.insert_df_into_db(df, table='public.maincode')

    def stock_code_init_tw(self):
        '''
        https://www.twse.com.tw/zh/trading/historical/bwibbu-day.html   
        https://www.twse.com.tw/rwd/zh/afterTrading/BWIBBU_d?date=20240809&selectType=ALL&response=json
        '''

        uri = "https://www.twse.com.tw/rwd/zh/afterTrading/BWIBBU_d?date=20240809&selectType=ALL&response=json"
        res = requests.get(uri)
        data = res.json()['data']
        code = [i[0] for i in data]
        cname = [i[1] for i in data]
        listed = ["TW"] * len(code)
        df = pd.DataFrame({
            "code": code,
            "cname": cname,
            "listed": listed
        })
        self.insert_df_into_db(df, table='public.maincode')
        return None
    
    def stock_price_init(self, current, start):
        self.cursor.execute(sql.SQL("Select distinct code from public.maincode where listed = 'TW';"))
        self.conn.commit()
        res = self.cursor.fetchall()
        stock_list = [i[0] for i in res]
        for year in range(current, start, -1):
            for code in tqdm(stock_list):
                try:
                    list_df = []
                    df = self._(code, year=year)
                    list_df.append(df)
                    final_df = pd.concat(list_df)
                    self.insert_df_into_db(final_df, table='public.price')
                except:
                    print(code, year)
                    continue
    def _(self, code, year):
        list_concat = []
        df_final = []
        limit_month = self.month if year == self.year else 12
        for _, month in enumerate(range(limit_month, 0, -1)):
            try:
                month = f"0{month}" if month < 10 else month
                da = f"{year}{month}01"
                url_json = f"https://www.twse.com.tw/exchangeReport/STOCK_DAY?response=json&date={da}&stockNo={code}"
                response = requests.get(url_json)
                list_concat.append(response.json()['data'])
            except:
                if month == 1:
                    return []
                else:
                    list_concat = [item for item in list_concat if item is not None]                                        
                    break
        try:
            df_final = pd.DataFrame(sum(list_concat, []))
            df_final = df_final.iloc[:, 0:-2]
            df_final.columns = ['da', 'vol_share', 'vol', 'op', 'hi', 'lo', 'cl']
            df_final.replace("--", None, inplace=True)
            df_final.replace("-", None, inplace=True)
            df_final.ffill(inplace=True)
            def convert_to_2024(da):
                year, month, day = da.split("/")
                return f"{int(year)+1911}-{month}-{day}"
            df_final['da'] = df_final['da'].apply(convert_to_2024)
            for i in range(1, len(df_final.columns)):
                df_final.iloc[:, i] = df_final.iloc[:, i].apply(lambda x: float(x.replace(",", "")))
            df_final['vol_share'] = df_final['vol_share'].astype(int) 
            df_final['vol'] = df_final['vol'].astype(int) 
            df_final['code'] = code
            return df_final 
        except Exception as e:
            return []
        

    def insert_df_into_db(self, df: pd.DataFrame, table='public.block_trade'):
        df_list = df.values.tolist()
        try:
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
        except Exception as e:
            print(e)
            
    def create_table_if_not_exist(self, db):
        '''
        db options:
        1. block_trade
        2. signal
        3. stock_code
        4. stock_price
        '''
        create_query = ""
        if db == "block_trade":
            create_query = '''
            CREATE TABLE IF NOT EXISTS public.block_trade
            (
                code character varying(50) COLLATE pg_catalog."default" NOT NULL,
                cname character varying(50) COLLATE pg_catalog."default" NOT NULL,
                type_ character varying(50) COLLATE pg_catalog."default" NOT NULL,
                cl double precision,
                vol_share bigint,
                vol bigint,
                da timestamp without time zone NOT NULL
            )
            WITH (
                OIDS = FALSE
            )
            TABLESPACE pg_default;

            ALTER TABLE IF EXISTS public.block_trade
                OWNER to mini;

            GRANT ALL ON TABLE public.block_trade TO mini;
            '''
        elif db == "signal":
            create_query = '''
            -- Table: public.block_code3_deatil
            -- DROP TABLE IF EXISTS public.block_code3_deatil;
            CREATE TABLE IF NOT EXISTS public.block_code3_deatil
            (
                code character varying(50) COLLATE pg_catalog."default",
                da timestamp without time zone NOT NULL,
                cl double precision,
                strategy character varying(50) COLLATE pg.pg_catalog."default" NOT NULL
            )
            WITH (
                OIDS = FALSE
            )
            TABLESPACE pg_default;

            ALTER TABLE IF EXISTS public.block_code3_deatil
                OWNER to mini;

            GRANT ALL ON TABLE public.block_code3_deatil TO mini;
            '''
        elif db == "stock_code":
            create_query = '''
            CREATE TABLE IF NOT EXISTS public.maincode
            (
                code character varying(50) COLLATE pg_catalog."default" NOT NULL,
                cname character varying(50) COLLATE pg_catalog."default" NOT NULL,
                listed character varying(50) COLLATE pg_catalog."default" NOT NULL
            )
            WITH (
                OIDS = FALSE
            )
            TABLESPACE pg_default;

            ALTER TABLE IF EXISTS public.maincode
                OWNER to mini;

            GRANT ALL ON TABLE public.maincode TO mini;
            '''
        
        elif db == "stock_price":
            create_query = '''
            -- Table: public.price
            -- DROP TABLE IF EXISTS public.price;

            CREATE TABLE IF NOT EXISTS public.price
            (
                da timestamp without time zone NOT NULL,
                vol_share bigint,
                vol bigint,
                op double precision,
                hi double precision,
                lo double precision,
                cl double precision,
                code VARCHAR COLLATE pg_catalog."default" NOT NULL,
                CONSTRAINT price_backup_pkey PRIMARY KEY (code, da)
            )
            WITH (
                OIDS = FALSE
            )
            TABLESPACE pg_default;

            ALTER TABLE IF EXISTS public.price
                OWNER to mini;

            GRANT ALL ON TABLE public.price TO mini;
            -- Index: idx_price_backup_code

            -- DROP INDEX IF EXISTS public.idx_price_backup_code;

            CREATE INDEX IF NOT EXISTS idx_price_backup_code
                ON public.price USING btree
                (code COLLATE pg_catalog."default" ASC NULLS LAST)
                TABLESPACE pg_default;
            -- Index: idx_price_code

            -- DROP INDEX IF EXISTS public.idx_price_code;

            CREATE INDEX IF NOT EXISTS idx_price_code
                ON public.price USING btree
                (code COLLATE pg_catalog."default" ASC NULLS LAST)
                TABLESPACE pg_default;
            -- Index: idx_price_da

            -- DROP INDEX IF EXISTS public.idx_price_da;

            CREATE INDEX IF NOT EXISTS idx_price_da
                ON public.price USING btree
                (da ASC NULLS LAST)
                TABLESPACE pg_default;
            -- Index: idx_price_future_backup_code

            -- DROP INDEX IF EXISTS public.idx_price_future_backup_code;

            CREATE INDEX IF NOT EXISTS idx_price_future_backup_code
                ON public.price USING btree
                (code COLLATE pg_catalog."default" ASC NULLS LAST)
                TABLESPACE pg_default;
            -- Index: price_backup_index

            -- DROP INDEX IF EXISTS public.price_backup_index;

            CREATE INDEX IF NOT EXISTS price_backup_index
                ON public.price USING btree
                (da ASC NULLS LAST, code COLLATE pg_catalog."default" ASC NULLS LAST)
                TABLESPACE pg_default;
            -- Index: price_future_backup_index

            -- DROP INDEX IF EXISTS public.price_future_backup_index;

            CREATE INDEX IF NOT EXISTS price_future_backup_index
                ON public.price USING btree
                (da ASC NULLS LAST, code COLLATE pg_catalog."default" ASC NULLS LAST)
                TABLESPACE pg_default;
            '''
        self.cursor.execute(create_query)
        self.conn.commit()
        print(db, "init success")
    def stock_pe_init(self):
        pass
if __name__ == "__main__":
    obj = TWSE()
    # obj.create_table_if_not_exist(db='signal')
    # obj.create_table_if_not_exist(db='stock_code')
    # obj.create_table_if_not_exist(db='stock_price')
    # obj.block_trading_init()
    # obj.stock_code_init()
    # obj.create_table_if_not_exist(db='block_trade')
    # obj.stock_price_init(current=2023, start=2020)

    obj.stock_code_init_tw()
    obj.stock_price_init(current=obj.year, start=obj.db_init_year)