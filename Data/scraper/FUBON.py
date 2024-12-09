import pandas as pd
import requests
from bs4 import BeautifulSoup
import numpy as np


class Fubon:
    def __init__(self, date_start, date_end):
        self.date_start = date_start
        self.date_end   = date_end
        self.headers    = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3',
        'Accept-Language': 'en-US,en;q=0.5',
        'Accept-Encoding': 'gzip, deflate',
        'Connection': 'keep-alive'
        }
        # broker-to-its-url-code dict
        self.str_main   = {
            "6010":"(牛牛牛)亞證券",
            "6620":"口袋證券",
            "1030":"土銀",
            "8890":"大和國泰",
            "6460":"大昌",
            "5050":"大展",
            "6160":"中國信託",
            "8520":"中農",
            "9800":"元大",
            "2200":"元大期貨",
            "5920":"元富",
            "5960":"日茂",
            "5660":"日進",
            "7750":"北城",
            "6110":"台中銀",
            "7120":"台安",
            "8150":"台新",
            "3000":"台新銀",
            "1090":"台灣工銀",
            "8910":"台灣巴克萊",
            "1110":"台灣企銀",
            "1380":"台灣匯立證券",
            "1470":"台灣摩根士丹利",
            "6450":"永全",
            "5600":"永興",
            "9A00":"永豐金",
            "8840":"玉山",
            "7080":"石橋",
            "6380":"光和",
            "7000":"兆豐",
            "1020":"合庫",
            "8380":"安泰",
            "1260":"宏遠",
            "2180":"亞東",
            "8490":"京城",
            "6660":"和興",
            "8900":"法銀巴黎",
            "8700":"花旗",
            "1590":"花旗環球",
            "7690":"金興",
            "5860":"盈溢",
            "5260":"美好",
            "1440":"美林",
            "1480":"美商高盛",
            "7030":"致和",
            "8960":"香港上海匯豐",
            "5320":"高橋",
            "8880":"國泰",
            "7790":"國票",
            "8450":"康和",
            "5380":"第一金",
            "5850":"統一",
            "9200":"凱基",
            "9600":"富邦",
            "7530":"富順",
            "1570":"港商法國興業",
            "1560":"港商野村",
            "1360":"港商麥格理",
            "1660":"港商聯昌",
            "1400":"港商蘇皇",
            "6640":"渣打商銀",
            "9300":"華南永昌",
            "8710":"陽信",
            "1650":"新加坡商瑞銀",
            "8560":"新光",
            "6210":"新百王",
            "8690":"新壽",
            "1520":"瑞士信貸",
            "9100":"群益金鼎",
            "2210":"群益期貨",
            "1230":"彰銀",
            "6480":"福邦",
            "6950":"福勝",
            "1040":"臺銀",
            "6910":"德信",
            "8440":"摩根大通",
            "8580":"聯邦商銀",
            "5500":"豐銀",
            "7900":"豐德",
            "5690":"豐興",
            "5460":"寶盛"
        }
        self.broker_dict = self.dict_reverser()
    # step 1
    def get_top_brokers(self, ticker="2330", top=5):
        '''
        params
        interval    = "8"
        url_default = f"https://fubon-ebrokerdj.fbs.com.tw/z/zc/zco/zco_{ticker}_{interval}.djhtm"
        '''
        url_specified = f"https://fubon-ebrokerdj.fbs.com.tw/z/zc/zco/zco.djhtm?a={ticker}&e={self.date_start}&f={self.date_end}"
        res           = requests.get(url_specified, headers=self.headers)
        soup          = BeautifulSoup(res.text, "lxml")
        #
        broker_count = 15
        col_count    = 4*2
        #
        col_names_soup = soup.find_all("td", {"class": "t2"})
        td_all_value   = soup.find_all("td", {"class": "t3n1"})
        td_all_name    = soup.find_all("td", {"class": "t4t1"})
        # 
        col_names           = [i.text for i in col_names_soup[-10:]]
        long_broker_names   = [td_all_name[i].text for i in range(0, len(td_all_name), 2)][:-2]
        short_broker_names  = [td_all_name[i].text for i in range(1, len(td_all_name), 2)][:-2]
        #
        data = np.array([i.text for i in td_all_value][:col_count*broker_count]).reshape(broker_count, col_count)
        df = pd.DataFrame(data)
        df.insert(4, "買超券商", short_broker_names)
        df.insert(0, "賣超券商", long_broker_names)
        df.columns = col_names
        df['e'] = self.date_start
        df['f'] = self.date_end
        df['a'] = ticker
        top5 = list(df['買超券商'])[:top]
        return df, top5
    # no scenario to use
    def dict_reverser(self):
        broker_to_code_dict = {}
        for key, value in self.str_main.items():
            broker_to_code_dict[value] = key
        return broker_to_code_dict
    # testing function
    def get_individual_broker_detail(self, ticker='2330', BHID=9200):
        url_specific_broker_detail = f"https://fubon-ebrokerdj.fbs.com.tw/z/zc/zco/zco0/zco0.djhtm?A={ticker}&BHID={BHID}&C=3&D={self.date_start}&E={self.date_end}&ver=V3"
        res = requests.get(url_specific_broker_detail, headers=self.headers)

        soup = BeautifulSoup(res.text, "lxml")
        t4n0 = soup.find_all("td")
        list_range = t4n0[10:715]
        list_ = np.array([i.text for i in list_range]).reshape(int(len(list_range)/5), 5)
        df = pd.DataFrame(list_[1:], columns=list_[0])
        df['ticker'] = ticker
        df['BHID'] = BHID
        return df
    # main function
    def get_all_broker_details(self, ticker='2330'):
        df_list = []
        _, top5 = self.get_top_brokers(ticker)
        for broker in top5:
            broker_code = self.broker_dict[broker.split("-")[0]]
            df = self.get_individual_broker_detail(ticker=ticker, BHID=broker_code)
            df_list.append(df)
        df_concated = pd.concat(df_list)
        return df_concated    
    

if __name__ == "__main__":
    test = Fubon(date_start="2023-01-01", date_end='2024-01-01')
    print(test.get_all_broker_details(ticker="2330"))
