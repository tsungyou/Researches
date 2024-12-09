
import pandas as pd
import numpy as np
import os

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.support.ui import Select

from Selenium import Selenium


class MOPS(Selenium):
    __slots__ = ("test1", "test2", "service")
    os.chdir('../db/')
    print(os.getcwd())
    def __init__(self):
        super().__init__()
        obj = Selenium()
        obj.chromedriver_path
        self.service = Service(executable_path=obj.chromedriver_path)
        print("chrome driverpath: ", self.chromedriver_path)
    def _get_BS_company(self, ticker='2330', da=2024):
        '''
        url: 'https://mops.twse.com.tw/mops/web/t164sb03'
        '''
        driver = webdriver.Chrome()
        url = 'https://mops.twse.com.tw/mops/web/t164sb03'
        driver.get(url)

        wait = WebDriverWait(driver, 20)

        select_element = wait.until(EC.presence_of_element_located((By.ID, 'isnew')))
        select = Select(select_element)
        select.select_by_visible_text('歷史資料')

        company_code_input = wait.until(EC.presence_of_element_located((By.ID, 'co_id')))
        company_code_input.send_keys('2330')

        year_input = driver.find_element(By.ID, 'year')
        year_input.send_keys('112')

        select_element = wait.until(EC.presence_of_element_located((By.ID, 'season')))
        select = Select(select_element)
        select.select_by_visible_text('1')

        search_button = driver.find_element(By.CSS_SELECTOR, 'input[type="button"][value=" 查詢 "]')
        search_button.click()

        wait.until(EC.presence_of_element_located((By.ID, 'table01')))
        data = []
        table = driver.find_element(By.CLASS_NAME, 'hasBorder')
        rows = table.find_elements(By.TAG_NAME, "tr")
        for row in rows:
            cols = row.find_elements(By.TAG_NAME, 'td')
            cols = [col.text for col in cols]
            data.append(cols)
        df = pd.DataFrame(data)
        return df

    def _get_CF_company(self, ticker='2330', da=2024):
        pass



if __name__ == "__main__":
    mops = MOPS()
    print(mops.__slots__)