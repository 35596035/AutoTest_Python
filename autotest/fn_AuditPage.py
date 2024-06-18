# selenium 相關套件
import sys

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

# 抓取tesseract執行檔
pytesseract.pytesseract.tesseract_cmd = "C:\Program Files\Tesseract-OCR\\tesseract.exe"


class Auto_AuditPage:
    def __init__(self, driver, action):

        self.driver = driver
        self.action = action

    def switch_frame2_init(self):
        self.driver.switch_to.default_content() # 先回去最初的iframe在切換
        frame2 = self.driver.find_element(By.XPATH, '//*[@id="iframe_page_2"]')
        self.driver.switch_to.frame(frame2)

    def Audit_HomePage(self):
        ele = self.driver.find_element(By.XPATH, "/html/body/div[1]/aside/div/section/ul/li[3]/a")
        self.action.click(ele).perform()
        time.sleep(1)
        # SQL活動追蹤
        ele = self.driver.find_element(By.XPATH, "/html/body/div[1]/aside/div/section/ul/li[3]/ul/li[1]/a")
        self.action.click(ele).perform()
        time.sleep(2)

        # # frame 內頁切換
        # frame = self.driver.find_element(By.XPATH, '//*[@id="iframe_page_1"]')
        # self.driver.switch_to.frame(frame)

        # 下拉式選單
        # ele = self.driver.find_element(By.XPATH, "/html/body/div/div/div/div/div/div[1]/span[5]/select")
        # select = Select(ele)
        # select.select_by_value("-210") #異常管理
        # self.driver.save_screenshot('AuditPage_Img/Audit.png')

        self.Audit_SendRegularly()
        # # 點選報表清單的第一行
        # ele = self.driver.find_element(By.XPATH, "/html/body/div/div/div/div/div/div[2]/div/div/div[1]/div[2]/div[2]/table/tbody/tr[1]")
        # self.action.click(ele).perform()
        #
        # # 按下定時發送報表按鈕
        # ele = self.driver.find_element(By.XPATH, "/html/body/div/div/div/div/div/div[3]/input[5]")
        # self.action.click(ele).perform()
        # time.sleep(3)
        #
        # # 跳出彈跳視窗
        # self.driver.switch_to.default_content()  # 切回最原本的iframe
        # ele = self.driver.find_element(By.XPATH, '//*[@id="ui-id-1"]/div/div[6]/div[1]/label[2]/input') # 重複發送按鈕選擇no
        # self.action.click(ele).perform()
        # ele = self.driver.find_element(By.XPATH, "/html/body/div[3]/div[3]/div/button[2]") # 送出按鈕
        # self.action.click(ele).perform()
        # time.sleep(3)
        #
        # # 點選排程設定開關
        # frame = self.driver.find_element(By.XPATH, '//*[@id="iframe_page_1"]')
        # self.driver.switch_to.frame(frame)
        #
        # for i in range(2):
        #     ele = self.driver.find_element(By.XPATH,
        #                                    "/html/body/div/div/div/div/div/div[2]/div/div/div[1]/div[2]/div[2]/table/tbody/tr[1]/td[2]/div[1]")
        #     self.action.click(ele).perform()
        #     time.sleep(3)

    def Audit_AddPage(self):
        # 新增報表
        ele = self.driver.find_element(By.XPATH, "/html/body/div/div/div/div/div/div[3]/input[1]")
        self.action.click(ele).perform()
        time.sleep(3)

        # 新增報表確認
        self.switch_frame2_init()
        # self.driver.switch_to.default_content() # 先回去最初的iframe在切換
        # New_frame = self.driver.find_element(By.XPATH, '//*[@id="iframe_page_2"]')
        # self.driver.switch_to.frame(New_frame)
        # 新增報表介面 > 點開選擇欄位的事
        ele = self.driver.find_element(By.XPATH, "/html/body/div/div/div/div/div/div[2]/div[1]/div[1]/div/div[2]/ul/li[2]/div")
        self.action.click(ele).perform()
        time.sleep(1)
        # 選擇欄位清單選擇
        self.driver.find_element(By.XPATH, "/html/body/div/div/div/div/div/div[2]/div[1]/div[1]/div/div[2]/ul/li[2]/ul/li[1]/a").click()
        self.driver.find_element(By.XPATH, "/html/body/div/div/div/div/div/div[2]/div[1]/div[1]/div/div[2]/ul/li[2]/ul/li[3]/a").click()
        self.driver.save_screenshot('AuditPage_Img/Audit_AddSelect.png')
        time.sleep(1)

        # 按下選擇條件 > 跳到選擇條件介面
        self.SelectPage()
        # 預覽按鈕
        self.Preview_Btn()
        # 儲存按鈕
        self.Save_Btn()

        # 關掉新增報表的視窗
        self.driver.switch_to.default_content() # 先回去最初的iframe在切換

        ele = self.driver.find_element(By.XPATH, '/html/body/div[1]/div[2]/ul/li[2]/a/button')
        self.action.click(ele).perform()
        time.sleep(2)

        self.Audit_defaultPage()

    # 選擇條件介面
    def SelectPage(self):
        # 新增報表確認
        self.switch_frame2_init()
        time.sleep(2)

        ele = self.driver.find_element(By.XPATH, '/html/body/div/div/div/div/div/div[1]/input[2]')
        self.action.click(ele).perform()
        time.sleep(2)
        # 選擇報表 > 套用框的操作
        ele = self.driver.find_element(By.XPATH, '/html/body/div/div/div/div/div/div[2]/div[2]/div[1]/div/div[2]/ul/li[2]/div')
        self.action.click(ele).perform()
        time.sleep(1)
        # self.driver.find_element(By.XPATH, '/html/body/div/div/div/div/div/div[2]/div[2]/div[1]/div/div[2]/ul/li[2]/ul/li[45]/a').click()
        self.driver.find_element(By.XPATH, '/html/body/div/div/div/div/div/div[2]/div[2]/div[1]/div/div[2]/ul/li[2]/ul/li[36]/a').click()
        time.sleep(2)
        ele = self.driver.find_element(By.XPATH, '/html/body/div/div/div/div/div/div[2]/div[2]/div[2]/div[1]/div[2]/div/span[3]/input')
        self.action.click(ele).perform()
        time.sleep(1)
        self.driver.switch_to.default_content()
        ele = self.driver.find_element(By.CSS_SELECTOR, '.form-control.term')
        self.action.click(ele).send_keys("CONNECT").perform()
        time.sleep(1)
        ele = self.driver.find_element(By.CSS_SELECTOR, '.btn.btn-default.new')
        self.action.click(ele).perform()
        time.sleep(1)
        ele = self.driver.find_element(By.XPATH, '/html/body/div[6]/div[3]/div/button[2]')
        self.action.click(ele).perform()
        time.sleep(1)
        # 按下套用按鈕
        frame2 = self.driver.find_element(By.XPATH, '//*[@id="iframe_page_2"]')
        self.driver.switch_to.frame(frame2)
        self.driver.find_element(By.CSS_SELECTOR, '.expression_check').click()
        self.driver.save_screenshot('AuditPage_Img/select.png')
        time.sleep(2)

    def Save_Btn(self):
        self.switch_frame2_init()
        # 儲存按鈕點選
        ele = self.driver.find_element(By.XPATH, "/html/body/div/div/div/div/div/div[3]/input[3]")
        self.action.click(ele).perform()

        # 點選儲存按鈕後跳出儲存報表框
        self.driver.switch_to.default_content()
        ele = self.driver.find_element(By.CSS_SELECTOR, ".form-control.free_form_name")
        self.action.click(ele).send_keys("test234").perform()
        time.sleep(2)

        # ele = self.driver.find_element(By.XPATH, '/html/body/div[6]/div[3]/div/button[1]') # 取消按紐
        ele = self.driver.find_element(By.XPATH, '/html/body/div[7]/div[3]/div/button[2]') # 送出按鈕
        self.action.click(ele).perform()
        time.sleep(2)

    def Preview_Btn(self):
        self.switch_frame2_init()
        self.driver.find_element(By.XPATH, '/html/body/div/div/div/div/div/div[3]/input[1]').click()
        time.sleep(5)
        ele = self.driver.find_element(By.XPATH, '/html/body/div/div/div/div/div/div[3]/input[1]')
        self.action.click(ele).perform()
        # /html/body/div/div/div/div/div/div[3]/input[1]
        time.sleep(5)

    def Audit_deletPage(self):
        frame = self.driver.find_element(By.XPATH, '//*[@id="iframe_page_1"]')
        self.driver.switch_to.frame(frame)
        # 點擊欄位名稱讓排序更新
        ele = self.driver.find_element(By.XPATH, '/html/body/div/div/div/div/div/div[2]/div/div/div[1]/div[2]/div[1]/table/thead/tr/th[1]')
        self.action.click(ele).perform()
        time.sleep(2)
        # 點擊更新欄位排序後的行
        ele = self.driver.find_element(By.XPATH, '/html/body/div/div/div/div/div/div[2]/div/div/div[1]/div[2]/div[2]/table/tbody/tr[3]')
        self.action.click(ele).perform()
        time.sleep(2)
        # 點擊刪除按鈕
        ele = self.driver.find_element(By.XPATH, '/html/body/div/div/div/div/div/div[3]/input[3]')
        self.action.click(ele).perform()
        time.sleep(2)
        # 刪除確認按鈕
        self.driver.switch_to.default_content()
        ele = self.driver.find_element(By.CSS_SELECTOR, '.confirm')
        self.action.click(ele).perform()
        self.driver.save_screenshot('AuditPage_Img/Audit_Delete.png')
        time.sleep(3)

        self.Audit_defaultPage()

    def Audit_defaultPage(self):
        self.driver.switch_to.default_content() # 先回去最初的iframe在切換

        # ele = self.driver.find_element(By.XPATH, "/html/body/div[1]/aside/div/section/ul/li[3]/a")
        # self.action.click(ele).perform()
        # time.sleep(2)
        # SQL活動追蹤
        ele = self.driver.find_element(By.XPATH, "/html/body/div[1]/aside/div/section/ul/li[3]/ul/li[1]/a")
        self.action.click(ele).perform()
        time.sleep(2)

        # ele = self.driver.find_element(By.XPATH, '/html/body/div[1]/div[2]/ul/li[1]/a')
        # self.action.click(ele).perform()
        # time.sleep(2)
        #
        # 回到最一開始的SQL活動追蹤frame
        Home_frame = self.driver.find_element(By.XPATH, '//*[@id="iframe_page_1"]')
        self.driver.switch_to.frame(Home_frame)

        # 選擇第二欄位
        ele = self.driver.find_element(By.XPATH, '/html/body/div/div/div/div/div/div[2]/div/div/div[1]/div[2]/div[2]/table/tbody/tr[2]')
        self.action.click(ele).perform()
        time.sleep(2)

        self.driver.switch_to.default_content()


    def Audit_RunBtn(self):
        frame = self.driver.find_element(By.XPATH, '//*[@id="iframe_page_1"]')
        self.driver.switch_to.frame(frame)
        # 點擊欄位名稱讓排序更新
        ele = self.driver.find_element(By.XPATH, '/html/body/div/div/div/div/div/div[2]/div/div/div[1]/div[2]/div[1]/table/thead/tr/th[1]')
        self.action.click(ele).perform()
        time.sleep(2)
        # 點擊更新欄位排序後的行
        ele = self.driver.find_element(By.XPATH, '/html/body/div/div/div/div/div/div[2]/div/div/div[1]/div[2]/div[2]/table/tbody/tr[3]')
        self.action.click(ele).perform()
        time.sleep(2)
        # 點執行按鈕
        ele = self.driver.find_element(By.CSS_SELECTOR, '.btn_run.btn.btn-danger')
        self.action.click(ele).perform()
        time.sleep(5)
        self.driver.save_screenshot('AuditPage_Img/Audit_Run.png')
        time.sleep(2)

        self.Audit_defaultPage()

    def Audit_SendRegularly(self):
        # frame 內頁切換
        frame1 = self.driver.find_element(By.XPATH, '//*[@id="iframe_page_1"]')
        self.driver.switch_to.frame(frame1)
        # 點選報表清單的第一行
        ele = self.driver.find_element(By.XPATH, "/html/body/div/div/div/div/div/div[2]/div/div/div[1]/div[2]/div[2]/table/tbody/tr[1]")
        self.action.click(ele).perform()

        # 按下定時發送報表按鈕
        ele = self.driver.find_element(By.XPATH, "/html/body/div/div/div/div/div/div[3]/input[5]")
        self.action.click(ele).perform()
        time.sleep(3)

        # 跳出彈跳視窗
        self.driver.switch_to.default_content()  # 切回最原本的iframe
        # 選擇通知對象
        ele = self.driver.find_element(By.XPATH, '//*[@id="ui-id-1"]/div/div[1]/div[1]/div/div/div[1]/div[2]/div[2]/table/tbody/tr[4]/td[2]/input')
        self.action.click(ele).perform()
        ele = self.driver.find_element(By.XPATH, '//*[@id="ui-id-1"]/div/div[6]/div[1]/label[2]/input') # 重複發送按鈕選擇no
        self.action.click(ele).perform()
        self.driver.save_screenshot('AuditPage_Img/Audit_SendRegularly.png')
        ele = self.driver.find_element(By.XPATH, "/html/body/div[3]/div[3]/div/button[2]") # 送出按鈕
        self.action.click(ele).perform()
        time.sleep(3)

        # 點選排程設定開關
        frame = self.driver.find_element(By.XPATH, '//*[@id="iframe_page_1"]')
        self.driver.switch_to.frame(frame)

        for i in range(2):
            ele = self.driver.find_element(By.XPATH,
                                           "/html/body/div/div/div/div/div/div[2]/div/div/div[1]/div[2]/div[2]/table/tbody/tr[1]/td[2]/div[1]")
            self.action.click(ele).perform()
            time.sleep(3)
        