import argparse
import json
import re
from dataclasses import dataclass
from datetime import datetime, timedelta
from functools import partial
from pathlib import Path
from typing import Callable
from urllib.parse import urlsplit

from playwright.sync_api import Error, Locator, Page, Playwright, Response, expect, sync_playwright


USERNAME_SELECTOR = 'input[name="username"]'


@dataclass(frozen=True)
class Case:
    id: str
    name: str
    action: Callable[[Page], None]


class CaseSkipped(Exception):
    pass


def button(scope: Page | Locator, name: str | re.Pattern) -> Locator:
    return scope.get_by_role("button", name=name, exact=isinstance(name, str))


def sidebar(page: Page) -> Locator:
    return page.get_by_role("region", name="scrollable content", exact=True).filter(
        has=button(page, "首頁")
    )


def content(page: Page) -> Locator:
    return page.locator("main:not(main main)")


def open_menu(page: Page, *labels: str) -> None:
    expand = button(page, "展開菜單")
    if expand.is_visible():
        expand.click()
    menu = sidebar(page)
    button(menu, labels[0]).click()
    for label in labels[1:]:
        # 子選單完成展開後才點擊，避免動畫期間點到下方項目。
        button(menu.locator(".MuiCollapse-entered"), label).click()


def expect_route(page: Page, route: str) -> None:
    expect(page).to_have_url(re.compile(rf"^https?://[^/]+{re.escape(route)}(?:[?#].*)?$"))


def check_page(page: Page, menu: tuple[str, ...], route: str, title: str) -> None:
    open_menu(page, *menu)
    expect_route(page, route)
    expect(content(page).get_by_text(title, exact=True)).to_be_visible()


def navigation_case(case_id: str, route: str, *menu: str, title: str | None = None) -> Case:
    action = partial(check_page, menu=menu, route=route, title=title or menu[-1])
    return Case(case_id, " → ".join(menu), action)


def check_home_menu(page: Page) -> None:
    collapse = button(page, "縮小菜單")
    expand = button(page, "展開菜單")
    if expand.is_visible():
        expand.click()
    collapse.click()
    expect(expand).to_be_visible()
    expand.click()
    expect(collapse).to_be_visible()
    open_menu(page, "首頁")
    expect(content(page).get_by_text("首頁", exact=True)).to_be_visible()


def open_detail(page: Page, link: Locator, title: str) -> None:
    href = link.get_attribute("href")
    if not href:
        raise AssertionError(f"找不到「{title}」的明細連結")
    link.click()
    expect_route(page, urlsplit(href).path)
    expect(content(page).get_by_text(title, exact=True)).to_be_visible()


def check_dashboard(page: Page, title: str, chart_title: str, optional: bool = False) -> None:
    open_menu(page, "儀表板")
    dashboard_list = content(page)
    grid = dashboard_list.get_by_role("grid")
    expect(grid.get_by_role("columnheader", name="名稱", exact=True)).to_be_visible()
    link = grid.get_by_role("link", name=title, exact=True)
    if optional:
        dashboard_list.get_by_role("searchbox", name="搜尋").fill(title)
        empty = grid.get_by_text(re.compile(r"^(?:No rows|No results found)\.?$"))
        expect(link.or_(empty)).to_be_visible(timeout=10_000)
        if empty.is_visible():
            raise CaseSkipped(f"目前站台的儀表板列表未提供「{title}」")

    open_detail(page, link, title)
    expect(content(page).get_by_text(chart_title, exact=True)).to_be_visible(timeout=20_000)


REPORT_NAME = "SQL執行報表(預設)"
REPORT_TIME = re.compile(r"^過去\s*\d+\s*(?:小?時|天|分(?:鐘)?)$")
DATE_FORMAT = "%Y/%m/%d %H:%M"


def open_sql_report(page: Page) -> Locator:
    open_menu(page, "報表查詢", "報表")
    open_detail(page, content(page).get_by_role("link", name=REPORT_NAME, exact=True), REPORT_NAME)
    grid = content(page).get_by_role("region", name="Data Table").get_by_role("grid")
    expect(grid.get_by_role("columnheader", name="SQL 執行時間", exact=True)).to_be_visible(timeout=20_000)
    expect(button(content(page), REPORT_TIME)).to_be_enabled(timeout=20_000)
    return grid


def is_report_query(response: Response) -> bool:
    return response.request.method == "POST" and urlsplit(response.url).path == "/api/search"


def refresh_report(page: Page, grid: Locator) -> None:
    refresh = content(page).get_by_role("button").filter(
        has=page.get_by_test_id("RestartAltOutlinedIcon")
    )
    with page.expect_response(is_report_query, timeout=20_000) as query:
        refresh.click()
    response = query.value
    if not response.ok:
        raise AssertionError(f"報表查詢回應 HTTP {response.status}")
    expect(refresh).to_be_enabled(timeout=20_000)
    expect(grid.get_by_role("columnheader", name="SQL 執行時間", exact=True)).to_be_visible()


def check_report_preset(page: Page) -> None:
    grid = open_sql_report(page)
    button(content(page), REPORT_TIME).click()
    button(page, "過去7天").click()
    expect(button(content(page), "過去 7天")).to_be_visible()
    refresh_report(page, grid)


def check_report_range(page: Page) -> None:
    grid = open_sql_report(page)
    button(content(page), REPORT_TIME).click()
    page.get_by_role("tab", name="指定時間段", exact=True).click()
    button(page, "絕對時間").click()
    field = page.get_by_role("textbox", name="YYYY/MM/DD hh:mm", exact=True)
    end = field.input_value()
    try:
        end_time = datetime.strptime(end, DATE_FORMAT)
    except ValueError as error:
        raise AssertionError(f"日期欄位格式不符，預期 YYYY/MM/DD hh:mm，實際為 {end!r}") from error
    start = (end_time - timedelta(days=1)).strftime(DATE_FORMAT)
    field.fill(start)
    field.press("Tab")
    expect(button(page, start)).to_be_visible()
    button(page, "套用").click()
    expect(button(content(page), f"{start} - {end}")).to_be_visible()
    refresh_report(page, grid)


def check_chart(page: Page) -> None:
    title = "資料庫SQL執行次數趨勢圖 (預設)"
    open_menu(page, "統計圖表")
    area = content(page)
    grid = area.get_by_role("grid")
    unrelated = grid.get_by_role("link", name="SQL分類圓餅圖 (預設)", exact=True)
    expect(unrelated).to_be_visible()
    area.get_by_role("searchbox", name="搜尋").fill("SQL執行次數趨勢圖")
    expect(unrelated).to_be_hidden()
    open_detail(page, grid.get_by_role("link", name=title, exact=True), title)
    expect(area.locator("svg").filter(has_text="次數")).to_be_visible(timeout=20_000)


CATEGORIES: dict[str, tuple[str, tuple[Case, ...]]] = {
    "home": ("首頁與側邊選單", (
        Case("sidebar", "收合與展開側邊選單，再回首頁", check_home_menu),
    )),
    "dashboards": ("儀表板", (
        Case("database-status", "資料庫狀態儀表板", partial(
            check_dashboard, title="資料庫狀態儀表板 (預設)", chart_title="SQL執行次數趨勢圖",
        )),
        Case("system-resources", "系統資源儀表板", partial(
            check_dashboard, title="系統資源儀表板 (預設)", chart_title="系統CPU", optional=True,
        )),
        Case("node-resources", "節點資源儀表板", partial(
            check_dashboard, title="節點資源儀表板 (預設)", chart_title="節點CPU", optional=True,
        )),
    )),
    "reports": ("報表查詢", (
        Case("sql-preset", "SQL 執行報表套用「過去 7 天」", check_report_preset),
        Case("sql-range", "SQL 執行報表套用指定日期區間", check_report_range),
        navigation_case("return-data", "/return-data", "報表查詢", "回傳值查詢"),
    )),
    "charts": ("統計圖表", (
        Case("sql-trend", "搜尋並開啟資料庫 SQL 執行次數趨勢圖", check_chart),
    )),
    "classification": ("資料分類", (
        navigation_case("datasets", "/value-set/list", "資料分類", "資料集"),
        navigation_case("filter-sets", "/filter-set/list", "資料分類", "條件集"),
    )),
    "regulations": ("法規", (
        navigation_case("regulations", "/regulation/list", "法規", title="法規清單"),
    )),
    "alerts": ("排程與告警", (
        navigation_case("schedules", "/schedule/list", "排程與告警", "排程"),
        navigation_case("periodic-alerts", "/periodic-alert/list", "排程與告警", "週期告警"),
        navigation_case("real-time-alerts", "/realtime-alert/list", "排程與告警", "即時告警"),
        navigation_case("history", "/historical-record/list", "排程與告警", "歷史紀錄"),
    )),
    "events": ("事件管理", (
        navigation_case("review", "/approval-events", "事件管理", "事件審核"),
        navigation_case("history", "/approval-trail", "事件管理", "審核歷程"),
    )),
    "approval": ("簽核流程", (
        navigation_case("flows", "/approval/list", "簽核流程"),
    )),
    "system": ("系統管理", (
        navigation_case("audit-log", "/audit-log-list", "系統管理", "稽核日誌", title="稽核日誌清單"),
    )),
}


def run_cases(page: Page, categories: tuple[str, ...], output_dir: Path) -> int:
    start_url = page.url
    results = []
    for key in categories:
        category, cases = CATEGORIES[key]
        print(f"\n【{category}】", flush=True)
        for case in cases:
            result = {"category": category, "id": f"{key}/{case.id}", "name": case.name}
            results.append(result)
            page_errors: list[str] = []

            def record_page_error(error: Error) -> None:
                page_errors.append(str(error))

            page.on("pageerror", record_page_error)
            try:
                page.goto(start_url, wait_until="domcontentloaded")
                expect(button(sidebar(page), "首頁")).to_be_visible()
                case.action(page)
            except CaseSkipped as error:
                result.update(status="SKIP", detail=str(error))
            except (AssertionError, Error) as error:
                result.update(status="FAIL", detail=str(error).strip())
                if page_errors:
                    result["page_errors"] = page_errors
            else:
                result["status"] = "PASS"
            finally:
                page.remove_listener("pageerror", record_page_error)

            can_capture = not page.is_closed() and not page.locator(USERNAME_SELECTOR).is_visible()
            if result["status"] != "SKIP" and can_capture:
                screenshot = Path(key) / f"{case.id}.png"
                (output_dir / screenshot).parent.mkdir(parents=True, exist_ok=True)
                try:
                    page.screenshot(path=output_dir / screenshot, full_page=True, timeout=5_000)
                except Error as error:
                    result["screenshot_error"] = str(error).splitlines()[0]
                else:
                    result["screenshot"] = screenshot.as_posix()

            print(f"  [{result['status']}] {case.name}", flush=True)
            if result.get("detail"):
                print(f"    {result['detail'].splitlines()[0]}", flush=True)
            for error in result.get("page_errors", []):
                print(f"    網頁錯誤 {error}", flush=True)

    counts = {status: sum(result["status"] == status for result in results) for status in ("PASS", "FAIL", "SKIP")}
    output_dir.mkdir(parents=True, exist_ok=True)
    summary = output_dir / "summary.json"
    summary.write_text(
        json.dumps({"counts": counts, "results": results}, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(f"\n通過 {counts['PASS']}，失敗 {counts['FAIL']}，略過 {counts['SKIP']}")
    print(f"測試結果 {summary.resolve()}")
    return int(bool(counts["FAIL"]))


def run(playwright: Playwright, categories: tuple[str, ...], output_dir: Path, login_timeout: int) -> int:
    from load_env import config

    browser = playwright.chromium.launch(channel="chrome", headless=False)
    try:
        context = browser.new_context(
            ignore_https_errors=True, viewport={"width": 1280, "height": 720}, device_scale_factor=1,
        )
        try:
            page = context.new_page()
            page.set_default_timeout(10_000)
            page.goto(config.BASE_URL, timeout=20_000)
            page.locator(USERNAME_SELECTOR).fill(config.TEST_USERNAME)
            page.locator('input[name="password"]').fill(config.TEST_PWD)
            captcha = page.get_by_role("textbox", name="驗證碼, 點擊圖片刷新", exact=True)
            captcha.focus()
            print(f"請在 Chrome 輸入驗證碼並按「登入」，等待上限 {login_timeout} 秒。", flush=True)
            expect(button(sidebar(page), "首頁")).to_be_visible(timeout=login_timeout * 1_000)
            print("登入成功，開始測試。", flush=True)
            return run_cases(page, categories, output_dir)
        finally:
            context.close()
    finally:
        browser.close()


def main() -> int:
    parser = argparse.ArgumentParser(description="DAM+ 網頁功能點擊測試")
    parser.add_argument("--list", action="store_true", help="列出功能分類與測試案例")
    parser.add_argument("--category", action="append", choices=CATEGORIES, help="指定分類，可重複使用，預設執行全部")
    parser.add_argument("--output", type=Path, help="指定截圖及測試結果的輸出資料夾")
    parser.add_argument("--login-timeout", type=int, default=180, help="手動登入等待秒數，預設 180")
    args = parser.parse_args()
    if args.login_timeout <= 0:
        parser.error("--login-timeout 必須大於 0")

    categories = tuple(key for key in CATEGORIES if not args.category or key in args.category)
    if args.list:
        for key in categories:
            name, cases = CATEGORIES[key]
            print(f"【{name}】 {key}")
            for case in cases:
                print(f"  {case.name}")
        return 0

    output_dir = args.output or Path(__file__).resolve().parent / "screenshots" / datetime.now().strftime("%Y%m%d-%H%M%S-%f")
    try:
        with sync_playwright() as playwright:
            return run(playwright, categories, output_dir, args.login_timeout)
    except (AssertionError, Error, KeyError, OSError) as error:
        print(f"測試執行中止。{str(error).strip().splitlines()[0]}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
