import fn_AutoTest
# selenium 相關套件
from selenium import webdriver
from selenium.webdriver.common.action_chains import ActionChains

# Mypackage
from autotest.fn_AuditPage import Auto_AuditPage
from autotest.fn_LogOut import Auto_LogOut
from autotest.LogInPage import Auto_LogIn
# 辨識圖片套件
import pytesseract
# 抓取tesseract執行檔
pytesseract.pytesseract.tesseract_cmd = "C:\Program Files\Tesseract-OCR\\tesseract.exe"

driver = webdriver.Chrome()
driver.get("https://192.168.127.55:8443/tw/#")

# driver.set_window_size(1280,1024) 視窗大小
driver.maximize_window()
action = ActionChains(driver)

# driver & action 初始畫設置
fn_AutoTest = fn_AutoTest.Driver(driver, action)
fn_AuditPage = Auto_AuditPage(driver, action)
fn_LogOut = Auto_LogOut(driver, action)
fn_LonIn = Auto_LogIn(driver, action)

fn_AutoTest.Show()

# 連線不安全認證
# fn_AutoTest.NotSafe_Page()
fn_LonIn.NotSafe_Page()

# 登入畫面
# fn_AutoTest.Input_LogIn_Page()
fn_LonIn.Inpot_LogIn_Page()

# 取得驗證碼圖片
path = "0528.png"
# fn_AutoTest.get_captcha(path)
fn_LonIn.get_captcha(path)

# 驗證碼輸入框
# path = "0528.png"
# driver.save_screenshot(path)
# image = Image.open(path)  # 將 screen load 至 memory
# image = image.crop((987, 490, 1137, 520))  # 根據位置剪裁圖片
# image.save(path, 'png')

# fn_AutoTest.Input_Num(fn_AutoTest.ImgNum(path))
fn_LonIn.Input_Num(fn_AutoTest.ImgNum(path))

# 進入畫面
fn_LonIn.CheckLogIn(path)
# while True:
#     try:
#         # 進入系統管理
#         fn_AutoTest.Check_UserELE()
#         break
#     except:
#         ele = driver.find_element(By.XPATH, "/html/body/div[4]/div[7]/div/button")
#         action.click(ele).perform()
#         print("驗證碼判定錯誤")
#         # 帳號密碼輸入
#         fn_AutoTest.Inpot_LogIn_Page()
#         # 取得驗證碼圖片
#         fn_AutoTest.get_captcha(path)
#         # 驗證碼判定&輸入
#         fn_AutoTest.Input_Num(fn_AutoTest.ImgNum(path))

driver.save_screenshot('LogIn.png')

# 儀錶板 > 模組狀態監控
fn_AutoTest.homePage()

# 稽核報表操作
# fn_AutoTest.AuditPage()
fn_AuditPage.Audit_HomePage()
fn_AuditPage.Audit_AddPage()
fn_AuditPage.Audit_RunBtn()
fn_AuditPage.Audit_deletPage()


# fn_AutoTest.System_PltPage()
# fn_AutoTest.Systen_Resorce_Page()
#
# # 系統管理 -> 使用者帳戶管理
# fn_AutoTest.Setting_Click()
# fn_AutoTest.Setting_Menu_User()

# 登出畫面
fn_LogOut.Auto_LogOutPage()

driver.save_screenshot('LogOut.png')
