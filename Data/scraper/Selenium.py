import requests
import zipfile
import os

class Selenium(object):
    __slots__ = ("chromedriver_path")
    os.chdir("../db/")
    def __init__(self):
        self.chromedriver_path = self._chromedriver_init()
# 下载 ChromeDriver

    def _chromedriver_init(self):
        if "chromedriver" in os.listdir("chromedriver_mac/chromedriver-mac-x64"):
            print("chromedriver already existed, for version 126.0")
            return os.path.abspath("chromedriver_mac/chromedriver-mac-x64/chromedriver")
        print("chrome driver not existed, create one...")
        url = "https://storage.googleapis.com/chrome-for-testing-public/126.0.6478.126/mac-x64/chromedriver-mac-x64.zip"
        response = requests.get(url)

        with open("chromedriver-mac-x64.zip", "wb") as file:
            file.write(response.content)

        with zipfile.ZipFile("chromedriver-mac-x64.zip", "r") as zip_ref:
            zip_ref.extractall("chromedriver_mac")

        chromedriver_path = os.path.abspath("chromedriver_mac/chromedriver-mac-x64/chromedriver")
        print(f"ChromeDriver path: {chromedriver_path}")
        print("==================")
        return chromedriver_path
