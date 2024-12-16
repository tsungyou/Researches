import pandas as pd # type: ignore
import yfinance as yf # type: ignore
import requests # type: ignore
from bs4 import BeautifulSoup # type: ignore

class Screener:
    def penny_stock_range_breakout_2f(
            symbol='QBTS', 
            start='2024-09-01', 
            hold=20, 
            price_bo_period=20,
            vol_ma_period=20,
            vol_ratio=2.4):
        
        qbts = yf.download(symbol, start=start, progress=False)
        # Volume Surge
        condition_vol = []
        vol = qbts[['Volume']]
        vol['ma20'] = vol['Volume'].rolling(vol_ma_period).mean()
        vol['ratio'] = vol['Volume']/vol['ma20']
        for i in range(len(vol)):
            if vol['ratio'].iloc[i] >= vol_ratio:
                condition_vol.append(vol.index[i])

        # Price breakout 
        condition_price = []
        price = qbts[['Close']]
        price['Max'] = price['Close'].rolling(price_bo_period).max()
        price['Max'] = price['Max'].shift(2)
        for i in range(len(price)):
            if price['Max'].iloc[i] < price['Close'].iloc[i]:
                condition_price.append(price.index[i])

        # day of signal
        final = []
        first = 0
        for i in condition_vol:
            if i in condition_price:
                if first == 0: 
                    first = i
                    final.append(i)
                else:
                    if (i - first).days >= 30:
                        first = i
                        final.append(i)
                    else:
                        continue

        # Rate of success
        price_bt = qbts[['Open']]
        price_bt['Open_s20'] = price_bt['Open'].shift(-hold)
        price_bt.ffill(inplace=True)
        price_bt['Entry'] = price_bt.apply(lambda x: 1 if x.name in final else 0, axis=1)
        price_bt['Entry'] = price_bt['Entry'].shift(1)
        price_bt_traded = price_bt[price_bt['Entry'] == 1]
        price_bt_traded['profit'] = price_bt_traded.apply(lambda x: x["Open_s20"]/x['Open']-1, axis=1)
        price_bt_traded['Symbol'] = symbol
        return price_bt_traded.iloc[:, [0, 1, 3, 4]]


class Scraper:
    def scrape_second_table():
        url = "https://finance.yahoo.com/u/yahoo-finance/watchlists/most-active-penny-stocks/"
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/86.0.4240.198 Safari/537.36"
        }
        response = requests.get(url, headers=headers)
        
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, 'html.parser')
            tables = soup.find_all('table')  # Get all tables on the page
            
            if len(tables) >= 2:  # Ensure at least two tables exist
                table = tables[1]  # Select the second table
                
                # Extract headers
                headers = [header.text for header in table.find_all('th')]
                
                # Extract rows
                rows = []
                for row in table.find_all('tr')[1:]:  # Skip header row
                    cells = row.find_all('td')
                    if len(cells) == len(headers):
                        rows.append([cell.text.strip() for cell in cells])
                
                # Create DataFrame
                df = pd.DataFrame(rows, columns=headers)
                return df
            else:
                print("Second table not found on the webpage.")
        else:
            print(f"Failed to retrieve data. HTTP Status Code: {response.status_code}")


if __name__ == "__main__":

    df_list = []
    for i in ['QBTS', "NVDA"]:
        df = penny_stock_range_breakout_2f(symbol=i)
        df_list.append(df)
    print(df_list)