# selenium 相關套件
from selenium import webdriver
import selenium.webdriver.support.ui as ui
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.select import Select
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.by import By
from selenium.webdriver.common.action_chains import ActionChains
# 時間,io相關套件使用
import time
import os
import io
# 畫面切割/分割/儲存/開啟
from PIL import Image
# 圖片驗證碼
import pytesseract
#抓取tesseract執行檔
pytesseract.pytesseract.tesseract_cmd = "C:\Program Files\Tesseract-OCR\\tesseract.exe"

class Driver():
    def __init__(self,driver,action):
        # driver = webdriver.Chrome()
        # driver.get("https://192.168.127.55:8443/tw/#")
        # driver.maximize_window()
        # action = ActionChains(driver)
        #-----------
        self.driver = driver
        self.action = action

    # def fn_Click(self, ele):
    #     self.action.click(ele).perform()

    def Show(self):
        print(self.driver,"\n",self.action)

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
        self.action.click(ele).send_keys("admin").perform()

        ele = self.driver.find_element(By.XPATH, "/html/body/div[1]/div[2]/div/div/div[3]/div[1]/input")
        self.action.click(ele).send_keys("aegIS@123").perform()

        time.sleep(1)

    # 取得驗證碼圖片
    def get_captcha(self, path):
        element = self.driver.find_element(By.XPATH, "/html/body/div[1]/div[2]/div/div/div[5]/div[1]/div/div[2]/img")
        self.driver.save_screenshot(path)          # 先將目前的 screen 存起來
        location = element.location           # 取得圖片 element 的位置
        size = element.size                   # 取得圖片 element 的大小
        left = location['x'] + 130                  # 決定上下左右邊界
        top = location['y'] + 95
        right = location['x'] + size['width'] + 230
        bottom = location['y'] + size['height'] + 120
        image = Image.open(path)              # 將 screen load 至 memory
        image = image.crop((left, top, right, bottom)) # 根據位置剪裁圖片
        image.save(path, 'png')               # 重新儲存圖片為 png 格式
        time.sleep(3)

    #圖片辨識
    def ImgNum(self, path):
        img = Image.open(path)
        result = pytesseract.image_to_string(img)
        print("驗證碼:{:}".format(result))
        return result

    # 驗證碼輸入框
    def Input_Num(self,ImgNum):
        ele = self.driver.find_element(By.XPATH, "/html/body/div[1]/div[2]/div/div/div[5]/div[1]/div/div[1]/input")
        self.action.click(ele).send_keys(ImgNum).perform()
        time.sleep(3)

    # 進入畫面
    def Check_UserELE(self):
        time.sleep(3)
        self.driver.find_element(By.XPATH, "/html/body/div[1]/header/nav/div/ul/li[2]/a")
        self.driver.save_screenshot('LogInHomePage.png')

    #模組狀態監控
    def HomePage_menu2(self):
        ele = self.driver.find_element(By.XPATH,"/html/body/div[1]/aside/div/section/ul/li[1]/ul/li[2]/a")
        self.action.click(ele).perform()

    #系統報表
    def System_PltPage(self):
        ele = self.driver.find_element(By.XPATH, "/html/body/div[1]/aside/div/section/ul/li[2]/a")
        self.action.click(ele).perform()
        #Driver.fn_Click(self, ele)
        time.sleep(3)

    # 系統資源狀況
    def Systen_Resorce_Page(self):
        ele = self.driver.find_element(By.XPATH, "/html/body/div[1]/aside/div/section/ul/li[2]/ul/li[1]/a")
        self.action.click(ele).perform()
        time.sleep(3)

    # 系統管理
    def Setting_Click(self):
        ele = self.driver.find_element(By.XPATH, "/html/body/div[1]/aside/div/section/ul/li[5]/a")
        self.action.click(ele).perform()
        time.sleep(3)

    # 使用者帳戶管理
    def Setting_Menu_User(self):
        ele = self.driver.find_element(By.XPATH, "/html/body/div[1]/aside/div/section/ul/li[5]/ul/li[4]/a")
        self.action.click(ele).perform()
        time.sleep(5)
    
    #儀錶板
    def homePage(self):
        ele = self.driver.find_element(By.XPATH, "/html/body/div[1]/aside/div/section/ul/li[1]/a")
        self.action.click(ele).perform()
        time.sleep(2)    

    # 登出畫面
    def LogOut_Page(self):
        ele = self.driver.find_element(By.XPATH, "/html/body/div[1]/header/nav/div/ul/li[2]/a")
        self.action.click(ele).perform()
        time.sleep(2)

        ele = self.driver.find_element(By.XPATH, "/html/body/div[1]/header/nav/div/ul/li[2]/ul/li/div/ul/li[4]/a")
        self.action.click(ele).perform()
        time.sleep(2)

