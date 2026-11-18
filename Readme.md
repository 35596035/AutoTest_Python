# DAM+ 網頁功能點擊測試

使用既有的 `.env` 與 Chrome 執行 `main.py`。程式會填入測試帳號與密碼，請在開啟的 Chrome 視窗輸入驗證碼並按「登入」。登入後會依功能順序自動操作。

```powershell
python -m pip install playwright python-dotenv
python main.py --list
python main.py
python main.py --category reports --category charts
```

| 分類 | `--category` | 驗證內容 |
| --- | --- | --- |
| 首頁與側邊選單 | `home` | 收合、展開、回首頁 |
| 儀表板 | `dashboards` | 開啟資料庫狀態、系統資源與節點資源儀表板，確認明細及圖表標題 |
| 報表查詢 | `reports` | SQL 執行報表套用過去 7 天及指定日期區間，確認查詢回應與結果表格，另驗證回傳值查詢頁面 |
| 統計圖表 | `charts` | 以關鍵字篩選圖表，再打開 SQL 執行次數趨勢圖 |
| 資料分類 | `classification` | 資料集、條件集 |
| 法規 | `regulations` | 法規清單 |
| 排程與告警 | `alerts` | 排程、週期告警、即時告警、歷史紀錄 |
| 事件管理 | `events` | 事件審核、審核歷程 |
| 簽核流程 | `approval` | 簽核流程清單 |
| 系統管理 | `system` | 稽核日誌清單 |

每次執行會在 `screenshots` 下建立含時間戳記的資料夾，依分類儲存畫面，並在 `summary.json` 記錄通過、失敗和略過的案例。可用 `--output` 指定輸出位置，使用 `--login-timeout` 調整登入等待秒數。若站台未提供系統資源或節點資源儀表板，對應案例會標記為略過。個別案例失敗後會繼續執行，整次執行以結束碼 `1` 回報失敗。

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
