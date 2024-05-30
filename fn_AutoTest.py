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
    def __init__(self, driver, action):
        self.d = driver
        self.a = action

    def fn_Click(self, ele):
        self.a.click(ele).perform()

    def Show(self):
        print(self.d,"\n",self.a)

    # 連線不安全認證
    def NotSafe_Page(self):
        ele = self.d.find_element(By.XPATH, '//*[@id="details-button"]')
        self.a.click(ele).perform()

        ele = self.d.find_element(By.XPATH, '//*[@id="proceed-link"]')
        self.a.click(ele).perform()
        time.sleep(3)

    # 輸入登入畫面輸入框
    def Inpot_LogIn_Page(self):
        ele = self.d.find_element(By.XPATH, "/html/body/div[1]/div[2]/div/div/div[2]/div[1]/input")
        self.a.click(ele).send_keys("admin").perform()

        ele = self.d.find_element(By.XPATH, "/html/body/div[1]/div[2]/div/div/div[3]/div[1]/input")
        self.a.click(ele).send_keys("aegIS@123").perform()

        time.sleep(1)

    # 取得驗證碼圖片
    def get_captcha(self, path):
        element = self.d.find_element(By.XPATH, "/html/body/div[1]/div[2]/div/div/div[5]/div[1]/div/div[2]/img")
        self.d.save_screenshot(path)          # 先將目前的 screen 存起來
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
        ele = self.d.find_element(By.XPATH, "/html/body/div[1]/div[2]/div/div/div[5]/div[1]/div/div[1]/input")
        self.a.click(ele).send_keys(ImgNum).perform()
        time.sleep(3)

    # 進入畫面
    def Check_UserELE(self):
        time.sleep(3)
        self.d.find_element(By.XPATH, "/html/body/div[1]/header/nav/div/ul/li[2]/a")

    #系統報表
    def System_PltPage(self):
        ele = self.d.find_element(By.XPATH, "/html/body/div[1]/aside/div/section/ul/li[2]/a")
        Driver.fn_Click(self, ele)
        time.sleep(3)

    # 系統資源狀況
    def Systen_Resorce_Page(self):
        ele = self.d.find_element(By.XPATH, "/html/body/div[1]/aside/div/section/ul/li[2]/ul/li[1]/a")
        Driver.fn_Click(self,ele)
        time.sleep(3)

    # 系統管理
    def Setting_Click(self):
        ele = self.d.find_element(By.XPATH, "/html/body/div[1]/aside/div/section/ul/li[5]/a")
        self.a.click(ele).perform()
        time.sleep(3)

    # 使用者帳戶管理
    def Setting_Menu_User(self):
        ele = self.d.find_element(By.XPATH, "/html/body/div[1]/aside/div/section/ul/li[5]/ul/li[4]/a")
        self.a.click(ele).perform()
        time.sleep(5)

    def homePage(self):
        ele = self.d.find_element(By.XPATH, "/html/body/div[1]/aside/div/section/ul/li[1]/a")
        self.a.click(ele).perform()
        time.sleep(2)    

    # 登出畫面
    def LogOut_Page(self):
        ele = self.d.find_element(By.XPATH, "/html/body/div[1]/header/nav/div/ul/li[2]/a")
        self.a.click(ele).perform()
        time.sleep(2)

        ele = self.d.find_element(By.XPATH, "/html/body/div[1]/header/nav/div/ul/li[2]/ul/li/div/ul/li[4]/a")
        self.a.click(ele).perform()
        time.sleep(2)

class Drive2(Driver):
    def __init__(self, driver, action):
        super().__init__(driver, action)

    def homePage2(self):
        ele = self.d.find_element(By.XPATH, "/html/body/div[1]/aside/div/section/ul/li[1]/a")
        self.a.click(ele).perform()
        time.sleep(2)