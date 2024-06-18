# selenium 相關套件
from selenium import webdriver
import selenium.webdriver.support.ui as ui
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.select import Select
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.by import By
from selenium.webdriver.common.action_chains import ActionChains
from selenium.common.exceptions import NoSuchElementException
# 時間,io相關套件使用
import time
import os
import io

# 圖片驗證碼
import pytesseract


# 抓取tesseract執行檔
pytesseract.pytesseract.tesseract_cmd = "C:\Program Files\Tesseract-OCR\\tesseract.exe"

class Auto_LogOut():
    def __init__(self, driver, action):
        self.driver = driver
        self.action = action

    # 登出畫面
    def Auto_LogOutPage(self):
        ele = self.driver.find_element(By.XPATH, "/html/body/div[1]/header/nav/div/ul/li[2]/a")
        self.action.click(ele).perform()
        time.sleep(2)

        ele = self.driver.find_element(By.XPATH, "/html/body/div[1]/header/nav/div/ul/li[2]/ul/li/div/ul/li[4]/a")
        self.action.click(ele).perform()
        time.sleep(2)