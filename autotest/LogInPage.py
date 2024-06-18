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
# 畫面切割/分割/儲存/開啟
from PIL import Image
# 圖片驗證碼
import pytesseract


class Auto_LogIn:
    def __init__(self, driver, action):
        self.driver = driver
        self.action = action

    # 連線不安全認證
    def NotSafe_Page(self):
        ele = self.driver.find_element(By.XPATH, '//*[@id="details-button"]')
        self.action.click(ele).perform()

        ele = self.driver.find_element(By.XPATH, '//*[@id="proceed-link"]')
        self.action.click(ele).perform()
        time.sleep(3)

    # 輸入登入畫面輸入框
    def Inpot_LogIn_Page(self):
        ele = self.driver.find_element(By.XPATH, "/html/body/div[1]/div[2]/div/div/div[2]/div[1]/input")
        # 維護人員
        self.action.click(ele).send_keys("test").perform()

        ele = self.driver.find_element(By.XPATH, "/html/body/div[1]/div[2]/div/div/div[3]/div[1]/input")
        self.action.click(ele).send_keys("aegIS@123").perform()
        time.sleep(1)

    # 取得驗證碼圖片
    def get_captcha(self, path):
        element = self.driver.find_element(By.XPATH, "/html/body/div[1]/div[2]/div/div/div[5]/div[1]/div/div[2]/img")
        self.driver.save_screenshot(path)  # 先將目前的 screen 存起來
        location = element.location  # 取得圖片 element 的位置
        size = element.size  # 取得圖片 element 的大小
        left = location['x'] + 130  # 決定上下左右邊界
        top = location['y'] + 95
        right = location['x'] + size['width'] + 230
        bottom = location['y'] + size['height'] + 120
        image = Image.open(path)  # 將 screen load 至 memory
        image = image.crop((left, top, right, bottom))  # 根據位置剪裁圖片
        image.save(path, 'png')  # 重新儲存圖片為 png 格式
        time.sleep(3)

    # 圖片辨識
    def ImgNum(self, path):
        img = Image.open(path)
        result = pytesseract.image_to_string(img)
        print("驗證碼:{:}".format(result))
        return result

    # 驗證碼輸入框
    def Input_Num(self, ImgNum):
        ele = self.driver.find_element(By.XPATH, "/html/body/div[1]/div[2]/div/div/div[5]/div[1]/div/div[1]/input")
        self.action.click(ele).send_keys(ImgNum).perform()
        time.sleep(2)

    # 進入畫面
    def Check_UserELE(self):
        time.sleep(2)
        self.driver.find_element(By.XPATH, "/html/body/div[1]/header/nav/div/ul/li[2]/a")
        self.driver.save_screenshot('LogInHomePage.png')

    def CheckLogIn(self, path):
        while True:
            try:
                self.Check_UserELE()
                break
            except:
                ele = self.driver.find_element(By.XPATH, "/html/body/div[4]/div[7]/div/button")
                self.action.click(ele).perform()
                print("驗證碼判定錯誤")
                # 帳號密碼輸入
                self.Inpot_LogIn_Page()
                # 取得驗證碼圖片
                self.get_captcha(path)
                # 驗證碼判定&輸入
                self.Input_Num(self.ImgNum(path))