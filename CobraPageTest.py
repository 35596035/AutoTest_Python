import fn_AutoTest
# selenium 相關套件
from selenium import webdriver
import selenium.webdriver.support.ui as ui

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

driver = webdriver.Chrome()
driver.get("https://192.168.127.51:8443/tw/#")

driver.maximize_window()
#driver.set_window_size(1280,1024) 視窗大小
action = ActionChains(driver)

fn_AutoTest = fn_AutoTest.Driver(driver,action)

fn_AutoTest.Show()
# ---------------
# 連線不安全認證

fn_AutoTest.NotSafe_Page()

# 登入畫面

fn_AutoTest.Inpot_LogIn_Page()

# 取得驗證碼圖片
path = "0528.png"
fn_AutoTest.get_captcha(path)

#驗證碼輸入框
# path = "0528.png"
# driver.save_screenshot(path)
# image = Image.open(path)  # 將 screen load 至 memory
# image = image.crop((987, 490, 1137, 520))  # 根據位置剪裁圖片
# image.save(path, 'png')

fn_AutoTest.Input_Num(fn_AutoTest.ImgNum(path))

# 進入畫面
while True:
    try:
        # 進入系統管理
        fn_AutoTest.Check_UserELE()
        break
    except:
        ele = driver.find_element(By.XPATH, "/html/body/div[4]/div[7]/div/button")
        action.click(ele).perform()
        print("驗證碼判定錯誤")
        # 帳號密碼輸入
        fn_AutoTest.Inpot_LogIn_Page()
        # 取得驗證碼圖片
        fn_AutoTest.get_captcha(path)
        # 驗證碼判定&輸入
        fn_AutoTest.Input_Num(fn_AutoTest.ImgNum(path))

driver.save_screenshot('LogIn.png')

fn_AutoTest.System_PltPage()
fn_AutoTest.Systen_Resorce_Page()

# 系統管理 -> 使用者帳戶管理
fn_AutoTest.Setting_Click()
fn_AutoTest.Setting_Menu_User()

# 儀錶板
fn_AutoTest.homePage()

# 登出畫面
fn_AutoTest.LogOut_Page()

driver.save_screenshot('LogOut.png')