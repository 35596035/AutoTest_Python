# DAM+ 網頁功能點擊測試

## 本機測試網站

```powershell
python -m pip install -r requirements-web.txt
python web_app.py
```

開啟 [本機測試台](http://127.0.0.1:8765/)。在頁面填寫站台網址、測試帳號與密碼，選擇測試分類後按「開始測試」，再到測試開啟的 Chrome 視窗手動輸入驗證碼並登入。測試台一次執行一組測試。資料異動案例預設關閉，勾選後才會在對應分類執行。

頁面會從目前的環境變數或 `.env` 帶入預設網址與帳號。使用同一個站台來源與帳號時，兩個密碼欄位可留白以沿用原設定。變更用密碼是 `load_env.py` 的既有欄位，現有案例尚未使用。表單內容只用於當次執行，不會寫回 `.env`。

完成後會自動顯示通過、失敗與略過案例，可點選案例截圖、成功提示或操作結果圖在頁面內預覽。「執行紀錄」會讀取 `screenshots/` 既有的 `summary.json`，即使命令列產生的報告也能查看。結果和圖片保存在原本的資料夾，因此這版啟動時無需 MySQL。

## 命令列執行

使用既有的 `.env` 與 Chrome 執行 `main.py`。程式會填入測試帳號與密碼，請在開啟的 Chrome 視窗輸入驗證碼並按「登入」。登入後會依功能順序自動操作。

直接執行 `python main.py` 會跑全部分類，並各新增及儲存一筆測試報表、圖表、資料集和條件集。新增、編輯、刪除案例會另外建立臨時資料，編輯後核對識別碼，再刪除該案例建立的資料並重新查找確認。指定 `--category` 時，可以加上 `--crud` 執行對應的新增、編輯、刪除案例，或用既有的 `--create-report`、`--create-chart`、`--create-classification` 執行會保留結果的新增案例。

```powershell
python -m pip install playwright python-dotenv
python main.py --list
python main.py
python main.py --category reports --category charts
python main.py --category reports --create-report
python main.py --category charts --create-chart
python main.py --category classification --create-classification
python main.py --category dashboards --category reports --category charts --category classification --category regulations --crud
```

| 分類 | `--category` | 驗證內容 |
| --- | --- | --- |
| 首頁與側邊選單 | `home` | 收合、展開、回首頁 |
| 儀表板 | `dashboards` | 等資料庫狀態儀表板載入後截圖，另驗證臨時儀表板的新增、改名及刪除 |
| 報表查詢 | `reports` | SQL 執行報表、回傳值查詢，以及報表新增、改名及刪除 |
| 統計圖表 | `charts` | 搜尋並開啟 SQL 執行次數趨勢圖，以及圖表新增、改名及刪除 |
| 資料分類 | `classification` | 資料集與條件集清單，以及各自的新增、改名及刪除 |
| 法規 | `regulations` | 法規清單，以及臨時法規的新增、改名及刪除 |
| 排程與告警 | `alerts` | 排程類型切換與取消、週期告警時間預覽、即時告警觸發條件草稿及歷史紀錄 |
| 事件管理 | `events` | 事件審核、審核歷程及處理中／結案狀態篩選 |
| 簽核流程 | `approval` | 簽核流程清單、草稿輸入、知會預設值及取消 |
| 系統管理 | `system` | 稽核日誌清單 |

每次執行會在 `screenshots` 下建立含時間戳記的資料夾，依分類儲存畫面，並在 `summary.json` 記錄通過、失敗和略過的案例。可用 `--output` 指定輸出位置，使用 `--login-timeout` 調整登入等待秒數。若站台未提供系統資源或節點資源儀表板，對應案例會標記為略過。個別案例失敗後會繼續執行，整次執行以結束碼 `1` 回報失敗。

新增或刪除完成後，程式會等網站右下角的成功提示顯示，再另外截取當前視窗。以報表為例，`reports/report-crud-create-status.png` 和 `reports/report-crud-delete-status.png` 分別記錄創建及刪除成功。儀表板、圖表、資料集及條件集也使用相同命名方式。法規頁透過清單更新呈現結果，會截取新增後找到該筆資料、刪除後查無該筆資料的清單。`summary.json` 的 `status_screenshots` 和 `result_screenshots` 分別記錄提示及清單截圖路徑，`screenshot` 記錄案例最後的畫面。操作截圖取得失敗時，測試仍會繼續核對資料，並在 `operation_screenshot_errors` 記下原因。

新增報表會從人、事、時、地、物各隨機加入一個欄位，以過去 30 分鐘執行查詢，再以含時間戳記的名稱儲存。程式會重新開啟報表核對設定，在該次執行資料夾下儲存 `reports/create-report.png`，並在 `summary.json` 記錄報表名稱、所選欄位及查詢時段。

新增圖表會建立直條圖，從「欄位與資料集」的「人」將「資料庫使用者」拖到 X 軸，再將「次數」拖到 Y 軸。選擇過去 30 分鐘後重整，儲存並重新開啟圖表核對兩軸。這個站台重新開啟圖表時會顯示預設的過去 15 分鐘。程式會在該次執行資料夾下儲存 `charts/create-chart.png`，並在 `summary.json` 記錄圖表名稱、軸欄位及兩個時段。

資料分類新增案例會將資料集的「欄位」選為「資料庫使用者」，加入自訂資料 `test`。條件集會把「資料庫使用者」拖入條件區，將 `IS` 改成 `EXIST`。兩筆資料以含時間戳記的名稱儲存，再從各自的清單重新開啟核對。核對後回到清單，把該筆名稱填入「搜尋」，確認只顯示該筆資料再截圖。執行資料夾會保留 `classification/create-dataset.png`、`classification/create-filter-set.png` 及 `summary.json`。

## 原有的錄製工具筆記

前置動作+套件說明
```bash
python -m pip --version
python -m pip install playwright
```
- ocr 透過tesseract.exe來辨識簡易圖片內容 (因效果不好暫時改為手動輸入驗證碼)
- path 建立資料夾套件
- palywright 自動化測試關鍵套件, 且搭配codegn參數, 使用錄製操作完成自動化測試需求

輸出檔案, 並開始錄製
- 加入 `--ignore-https-errors` 參數，告訴 Playwright 強制忽略憑證錯誤即可
```python
python -m playwright codegen --channel=chrome --ignore-https-errors -o 120_v1.py https://192.168.170.120:32000/login
```
