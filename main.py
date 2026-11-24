import argparse
import json
import re
from contextvars import ContextVar
from dataclasses import dataclass
from datetime import datetime, timedelta
from functools import partial
from pathlib import Path
from random import choice
from typing import Callable
from urllib.parse import urljoin, urlsplit

from playwright.sync_api import Error, Locator, Page, Playwright, Response, expect, sync_playwright


USERNAME_SELECTOR = 'input[name="username"]'
STATUS_MESSAGES = {
    "create": re.compile(r"(?:創建|建立|新增|儲存)[^\n。]{0,20}成功|成功(?:創建|建立|新增|儲存)"),
    "delete": re.compile(r"刪除[^\n。]{0,20}成功|成功刪除"),
}
operation_screenshot_recorder: ContextVar[Callable[[str, bool], None] | None] = ContextVar(
    "operation_screenshot_recorder", default=None,
)


@dataclass(frozen=True)
class Case:
    id: str
    name: str
    action: Callable[[Page], dict[str, object] | None]
    required_option: str | None = None


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


def wait_for_database_status_charts(page: Page) -> None:
    cards = content(page).locator(".react-grid-layout > .react-grid-item")
    expect(cards.first).to_be_visible()
    rendered = page.locator("canvas[data-zr-dom-id]:visible")
    no_data = page.get_by_text("此時間區段內沒有資料", exact=True)
    ready = cards.filter(
        has=rendered.or_(no_data),
        has_not=page.get_by_role("progressbar"),
    )
    expect(ready, "資料庫狀態儀表板的所有圖表應完成載入").to_have_count(
        cards.count(), timeout=30_000,
    )


def check_database_status_dashboard(page: Page) -> None:
    check_dashboard(
        page, title="資料庫狀態儀表板 (預設)", chart_title="SQL執行次數趨勢圖",
    )
    wait_for_database_status_charts(page)


REPORT_NAME = "SQL執行報表(預設)"
RELATIVE_TIME = re.compile(r"^過去\s*\d+\s*(?:小?時|天|分(?:鐘)?)$")
DATE_FORMAT = "%Y/%m/%d %H:%M"
REPORT_FIELD_GROUPS = ("人", "事", "時", "地", "物")
THIRTY_MINUTE_PERIOD = "過去 30分"
CHART_X_FIELD = "資料庫使用者"
CHART_Y_FIELD = "次數"


def open_report_list(page: Page) -> None:
    open_menu(page, "報表查詢", "報表")


def report_grid(page: Page) -> Locator:
    return content(page).get_by_role("region", name="Data Table").get_by_role("grid")


def icon_button(page: Page, icon: str) -> Locator:
    return content(page).get_by_role("button").filter(has=page.get_by_test_id(icon))


def open_sql_report(page: Page) -> Locator:
    open_report_list(page)
    open_detail(page, content(page).get_by_role("link", name=REPORT_NAME, exact=True), REPORT_NAME)
    time_column = report_grid(page).get_by_role("columnheader", name="SQL 執行時間", exact=True)
    expect(time_column).to_be_visible(timeout=20_000)
    expect(button(content(page), RELATIVE_TIME)).to_be_enabled(timeout=20_000)
    return time_column


def refresh_query(page: Page, endpoint: str, label: str) -> None:
    refresh = icon_button(page, "RestartAltOutlinedIcon")

    def matches(response: Response) -> bool:
        return response.request.method == "POST" and urlsplit(response.url).path == endpoint

    with page.expect_response(matches, timeout=20_000) as query:
        refresh.click()
    response = query.value
    if not response.ok:
        raise AssertionError(f"{label}查詢回應 HTTP {response.status}")
    expect(refresh).to_be_enabled(timeout=20_000)


def refresh_report(page: Page, result: Locator) -> None:
    refresh_query(page, "/api/search", "報表")
    expect(result).to_be_visible(timeout=20_000)


def select_thirty_minutes(page: Page) -> None:
    area = content(page)
    button(area, RELATIVE_TIME).click()
    button(page, "過去30分鐘").click()
    expect(button(area, THIRTY_MINUTE_PERIOD)).to_be_visible()


def check_report_preset(page: Page) -> None:
    time_column = open_sql_report(page)
    button(content(page), RELATIVE_TIME).click()
    button(page, "過去7天").click()
    expect(button(content(page), "過去 7天")).to_be_visible()
    refresh_report(page, time_column)


def check_report_range(page: Page) -> None:
    time_column = open_sql_report(page)
    button(content(page), RELATIVE_TIME).click()
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
    refresh_report(page, time_column)


def report_field_list(area: Locator, heading: str) -> Locator:
    return area.get_by_text(heading, exact=True).locator("xpath=following-sibling::*[1]")


def select_random_report_fields(page: Page) -> dict[str, str]:
    area = content(page)
    available = report_field_list(area, "可選欄位")
    selected = report_field_list(area, "選擇欄位")
    labels = available.locator("span.MuiTypography-root")
    fields = {}
    for group in REPORT_FIELD_GROUPS:
        for category in REPORT_FIELD_GROUPS:
            toggle = button(area, category)
            target = "true" if category == group else "false"
            if toggle.get_attribute("aria-pressed") != target:
                toggle.click()
                expect(toggle).to_have_attribute("aria-pressed", target)

        candidates = [label.strip() for label in labels.all_text_contents() if label.strip()]
        if not candidates:
            raise AssertionError(f"「{group}」分類沒有可選欄位")
        field = choice(candidates)
        row = available.get_by_text(field, exact=True).locator("xpath=..")
        row.hover()
        row.get_by_role("button").filter(has=page.get_by_test_id("AddIcon")).click()
        expect(selected.get_by_text(field, exact=True)).to_be_visible()
        fields[group] = field
    return fields


def verify_saved_report(page: Page, title: str, fields: dict[str, str]) -> None:
    expect_route(page, "/report-list")
    area = content(page)
    area.get_by_role("searchbox", name="搜尋", exact=True).fill(title)
    open_detail(page, area.get_by_role("link", name=title, exact=True), title)
    expect(button(area, THIRTY_MINUTE_PERIOD)).to_be_visible()
    selected = report_field_list(area, "選擇欄位")
    if not selected.is_visible():
        icon_button(page, "MenuOpenOutlinedIcon").click()
    for field in fields.values():
        expect(selected.get_by_text(field, exact=True)).to_be_visible()


def check_report_creation(page: Page) -> dict[str, object]:
    open_report_list(page)
    area = content(page)
    button(area, "新增").click()
    expect_route(page, "/search")
    expect(area.get_by_text("報表 —未命名", exact=True)).to_be_visible()
    fields = select_random_report_fields(page)

    select_thirty_minutes(page)
    refresh_report(page, report_grid(page))

    title = f"自動化測試報表-{datetime.now():%Y%m%d-%H%M%S-%f}"
    icon_button(page, "EditSharpIcon").click()
    dialog = page.get_by_role("dialog", name="編輯報表", exact=True)
    dialog.locator('input[type="text"]').fill(title)
    button(dialog, "儲存").click()
    expect(dialog).to_be_hidden()
    expect(area.get_by_text(title, exact=True)).to_be_visible()
    print(f"    儲存報表 {title}", flush=True)
    save_change(page, button(area, "儲存"), "/api/qrys", ("POST",))

    try:
        verify_saved_report(page, title, fields)
    except (Error, AssertionError) as error:
        raise AssertionError(f"報表「{title}」已收到儲存成功回應，重新開啟時驗證失敗。\n{error}") from error
    return {"report_name": title, "fields": fields, "time_range": THIRTY_MINUTE_PERIOD}


def check_chart(page: Page) -> None:
    title = "資料庫SQL執行次數趨勢圖 (預設)"
    open_menu(page, "統計圖表")
    area = content(page)
    grid = area.get_by_role("grid")
    expect(grid.get_by_role("columnheader", name="名稱", exact=True)).to_be_visible()
    area.get_by_role("searchbox", name="搜尋").fill("SQL執行次數趨勢圖")
    expect(grid.get_by_role("link")).to_have_count(1)
    open_detail(page, grid.get_by_role("link", name=title, exact=True), title)
    chart = area.locator('canvas[data-zr-dom-id]').or_(area.locator("svg").filter(has_text="次數"))
    no_data = area.get_by_text("此時間區段內沒有資料", exact=True)
    expect(chart.or_(no_data).first).to_be_visible(timeout=20_000)


def chart_axis(area: Locator, name: str) -> Locator:
    return area.get_by_text(name, exact=True).locator("xpath=../../..")


def chart_field_list(page: Page) -> Locator:
    area = content(page)
    people = button(area.get_by_role("group"), "人")
    if people.get_attribute("aria-pressed") != "true":
        people.click()
    expect(people).to_have_attribute("aria-pressed", "true")

    fields = area.get_by_role("region", name="scrollable content", exact=True).filter(
        has=button(page, "欄位與資料集")
    )
    for section in ("欄位與資料集", "人"):
        toggle = button(fields, section)
        expect(toggle).to_be_visible()
        if toggle.get_by_test_id("KeyboardArrowDownIcon").is_visible():
            toggle.click()
    return fields


def drag_chart_field(page: Page, fields: Locator, field: str, axis: str) -> None:
    target = chart_axis(content(page), axis)
    source = fields.locator('[draggable="true"]').filter(has=page.get_by_text(field, exact=True))
    drop_area = target.get_by_text("拖入", exact=True)
    source.hover()
    page.mouse.down()
    try:
        drop_area.hover()
        drop_area.hover()
    finally:
        page.mouse.up()
    expect(target.get_by_text(field, exact=True)).to_be_visible()


def verify_saved_chart(page: Page, title: str) -> str:
    open_menu(page, "統計圖表")
    expect_route(page, "/chart")
    area = content(page)
    area.get_by_role("searchbox", name="搜尋", exact=True).fill(title)
    open_detail(page, area.get_by_role("link", name=title, exact=True), title)
    reopened_period = button(area, RELATIVE_TIME).inner_text()
    button(area, "編輯").click()
    expect(area.get_by_text(title, exact=True)).to_be_visible()
    expect(button(area, "直條圖")).to_be_visible()
    expect(chart_axis(area, "X 軸").get_by_text(CHART_X_FIELD, exact=True)).to_be_visible()
    expect(chart_axis(area, "Y 軸").get_by_text(CHART_Y_FIELD, exact=True)).to_be_visible()
    return reopened_period


def check_chart_creation(page: Page) -> dict[str, object]:
    open_menu(page, "統計圖表")
    area = content(page)
    button(area, "新增").click()
    expect_route(page, "/chart/editor")
    expect(area.get_by_text("未命名", exact=True)).to_be_visible()
    expect(button(area, "直條圖")).to_be_visible()
    fields = chart_field_list(page)
    drag_chart_field(page, fields, CHART_X_FIELD, "X 軸")
    drag_chart_field(page, fields, CHART_Y_FIELD, "Y 軸")

    select_thirty_minutes(page)
    refresh_query(page, "/api/report/exec", "圖表")
    preview = area.locator("svg").filter(has_text=CHART_X_FIELD)
    no_data = area.get_by_text("此時間區段內沒有資料", exact=True)
    expect(preview.or_(no_data).first).to_be_visible(timeout=20_000)

    title = f"自動化測試圖表-{datetime.now():%Y%m%d-%H%M%S-%f}"
    icon_button(page, "EditIcon").click()
    dialog = page.get_by_role("dialog").filter(has=page.get_by_text("編輯圖表", exact=True))
    dialog.locator('input[name="title"]').fill(title)
    button(dialog, "儲存").click()
    expect(dialog).to_be_hidden()
    expect(area.get_by_text(title, exact=True)).to_be_visible()
    print(f"    儲存圖表 {title}", flush=True)
    save_change(page, button(area, "儲存"), "/api/qrys", ("POST",))

    try:
        reopened_period = verify_saved_chart(page, title)
    except (Error, AssertionError) as error:
        raise AssertionError(f"圖表「{title}」已收到儲存成功回應，重新開啟時驗證失敗。\n{error}") from error
    return {
        "chart_name": title,
        "chart_type": "直條圖",
        "x_axis": CHART_X_FIELD,
        "y_axis": CHART_Y_FIELD,
        "time_range": THIRTY_MINUTE_PERIOD,
        "reopened_time_range": reopened_period,
    }


CLASSIFICATION_FIELD = "資料庫使用者"
DATASET_CUSTOM_VALUE = "test"
DATASET_FIELD_SELECTOR = "#mui-component-select-field"


def open_new_classification(page: Page, label: str, route: str) -> Locator:
    open_menu(page, "資料分類", label)
    area = content(page)
    button(area, "新增").click()
    expect_route(page, route)
    return area


def search_classification(page: Page, title: str, list_route: str) -> Locator:
    expect_route(page, list_route)
    area = content(page)
    search = area.get_by_role("searchbox", name="搜尋", exact=True)
    search.fill(title)
    expect(search).to_have_value(title)
    grid = area.get_by_role("grid")
    match = grid.get_by_role("link", name=title, exact=True)
    expect(match).to_be_visible()
    expect(grid.get_by_role("link")).to_have_count(1)
    return match


def save_and_reopen_classification(page: Page, title: str, endpoint: str, list_route: str) -> None:
    area = content(page)
    print(f"    儲存 {title}", flush=True)
    save_change(page, button(area, "儲存"), endpoint, ("POST",))

    try:
        link = search_classification(page, title, list_route)
        href = link.get_attribute("href")
        if not href:
            raise AssertionError(f"找不到「{title}」的編輯連結")
        link.click()
        expect_route(page, urlsplit(href).path)
    except (Error, AssertionError) as error:
        raise AssertionError(f"「{title}」已收到儲存成功回應，重新開啟時驗證失敗。\n{error}") from error


def show_classification_result(page: Page, title: str, list_route: str) -> None:
    page.go_back(wait_until="domcontentloaded")
    search_classification(page, title, list_route)


def check_dataset_creation(page: Page) -> dict[str, object]:
    area = open_new_classification(page, "資料集", "/value-set/create")
    field = area.locator(DATASET_FIELD_SELECTOR)
    field.click()
    page.get_by_role("option", name=CLASSIFICATION_FIELD, exact=True).click()
    confirm = button(page.get_by_role("dialog", name="切換欄位", exact=True), "確認")
    add_custom = button(area, "新增自訂資料")
    expect(confirm.or_(add_custom).first).to_be_visible()
    if confirm.is_visible():
        confirm.click()
    expect(field).to_have_text(CLASSIFICATION_FIELD)

    add_custom.click()
    custom = page.get_by_role("textbox", name="輸入字串", exact=True)
    custom.fill(DATASET_CUSTOM_VALUE)
    custom.locator("xpath=../../..").get_by_role("button").filter(
        has=page.get_by_test_id("AddIcon")
    ).click()
    if custom.is_visible():
        page.keyboard.press("Escape")
    expect(custom).to_be_hidden()
    expect(area.get_by_text(DATASET_CUSTOM_VALUE, exact=True)).to_be_visible()

    title = f"自動化測試資料集-{datetime.now():%Y%m%d-%H%M%S-%f}"
    name = area.get_by_role("textbox", name="資料集名稱", exact=True)
    name.fill(title)
    save_and_reopen_classification(page, title, "/api/valueSet", "/value-set/list")
    expect(name).to_have_value(title)
    expect(field).to_have_text(CLASSIFICATION_FIELD)
    expect(area.get_by_text(DATASET_CUSTOM_VALUE, exact=True)).to_be_visible()
    show_classification_result(page, title, "/value-set/list")
    return {"dataset_name": title, "field": CLASSIFICATION_FIELD, "custom_value": DATASET_CUSTOM_VALUE}


def check_filter_set_creation(page: Page) -> dict[str, object]:
    area = open_new_classification(page, "條件集", "/filter-set/create")
    source = area.locator('[draggable="true"]').filter(
        has=page.get_by_text(CLASSIFICATION_FIELD, exact=True)
    )
    group = button(area, "AND")
    source.drag_to(group)
    condition = group.locator("xpath=..")
    operator = condition.get_by_role("combobox")
    expect(condition.get_by_text(CLASSIFICATION_FIELD, exact=True)).to_be_visible()
    expect(operator).to_have_text("IS")
    operator.click()
    page.get_by_role("option", name="EXIST", exact=True).click()
    expect(operator).to_have_text("EXIST")

    title = f"自動化測試條件集-{datetime.now():%Y%m%d-%H%M%S-%f}"
    name = area.get_by_role("textbox", name="請輸入", exact=True)
    name.fill(title)
    save_and_reopen_classification(page, title, "/api/filterSet", "/filter-set/list")
    expect(name).to_have_value(title)
    expect(condition.get_by_text(CLASSIFICATION_FIELD, exact=True)).to_be_visible()
    expect(operator).to_have_text("EXIST")
    show_classification_result(page, title, "/filter-set/list")
    return {"filter_set_name": title, "field": CLASSIFICATION_FIELD, "operator": "EXIST"}


def open_crud_list(page: Page, route: str) -> Locator:
    page.goto(urljoin(page.url, route), wait_until="domcontentloaded")
    expect_route(page, route)
    grid = content(page).get_by_role("grid")
    expect(grid).to_be_visible()
    return grid


def crud_row(page: Page, grid: Locator, title: str) -> Locator:
    search = content(page).get_by_role("searchbox", name="搜尋", exact=True)
    search.fill(title)
    return grid.get_by_role("row").filter(
        has=page.get_by_role("cell", name=title, exact=True)
    )


def capture_operation_screenshot(operation: str, *, has_toast: bool) -> None:
    record_screenshot = operation_screenshot_recorder.get()
    if record_screenshot:
        record_screenshot(operation, has_toast)


def save_change(
    page: Page, trigger: Locator, endpoint: str, methods: tuple[str, ...], *, capture_toast: bool = True,
) -> None:
    def matches(response: Response) -> bool:
        path = urlsplit(response.url).path
        method = response.request.method
        return method in methods and (
            path == endpoint or (method in ("PUT", "PATCH") and path.startswith(f"{endpoint}/"))
        )

    with page.expect_response(matches, timeout=20_000) as saved:
        trigger.click()
    response = saved.value
    method = response.request.method
    if not response.ok:
        raise AssertionError(f"{method} {endpoint} 回應 HTTP {response.status}")

    operation = {"POST": "create", "DELETE": "delete"}.get(method)
    if operation and capture_toast:
        capture_operation_screenshot(operation, has_toast=True)


def rename_report(page: Page, row: Locator, title: str) -> None:
    row.get_by_role("link").click()
    icon_button(page, "EditSharpIcon").click()
    dialog = page.get_by_role("dialog", name="編輯報表", exact=True)
    dialog.locator('input[type="text"]').fill(title)
    button(dialog, "儲存").click()
    expect(dialog).to_be_hidden()
    save_change(page, button(content(page), "儲存"), "/api/qrys", ("PUT", "PATCH"))


def rename_chart(page: Page, row: Locator, title: str) -> None:
    row.get_by_role("link").click()
    button(content(page), "編輯").click()
    icon_button(page, "EditIcon").click()
    dialog = page.get_by_role("dialog").filter(has=page.get_by_text("編輯圖表", exact=True))
    dialog.locator('input[name="title"]').fill(title)
    button(dialog, "儲存").click()
    expect(dialog).to_be_hidden()
    save_change(page, button(content(page), "更新"), "/api/qrys", ("PUT", "PATCH"))


def rename_classification(
    page: Page, row: Locator, title: str, *, field_name: str, endpoint: str,
) -> None:
    row.get_by_role("link").click()
    area = content(page)
    name = area.get_by_role("textbox", name=field_name, exact=True)
    expect(name).not_to_have_value("")
    name.fill(title)
    save_change(page, button(area, "儲存"), endpoint, ("PUT", "PATCH"))


def create_regulation(page: Page) -> dict[str, object]:
    open_menu(page, "法規")
    area = content(page)
    button(area, "新增").click()
    dialog = page.get_by_role("dialog", name="新增法規", exact=True)
    title = f"自動化測試法規-{datetime.now():%Y%m%d-%H%M%S-%f}"
    dialog.get_by_role("textbox").fill(title)
    save_change(page, button(dialog, "送出"), "/api/regulations", ("POST",), capture_toast=False)
    expect(dialog).to_be_hidden()
    expect(crud_row(page, area.get_by_role("grid"), title)).to_be_visible()
    capture_operation_screenshot("create", has_toast=False)
    return {"regulation_name": title}


def set_dashboard_name(page: Page, title: str) -> None:
    icon_button(page, "EditSharpIcon").click()
    dialog = page.get_by_role("dialog", name="編輯儀表板", exact=True)
    dialog.locator('input[type="text"]').fill(title)
    button(dialog, "確認").click()
    expect(dialog).to_be_hidden()


def create_dashboard(page: Page) -> dict[str, object]:
    open_menu(page, "儀表板")
    area = content(page)
    button(area, "新增").click()
    expect_route(page, "/dashboard/editor")
    title = f"自動化測試儀表板-{datetime.now():%Y%m%d-%H%M%S-%f}"
    set_dashboard_name(page, title)
    save_change(page, button(area, "儲存"), "/api/qrys", ("POST",))
    return {"dashboard_name": title}


def rename_dashboard(page: Page, row: Locator, title: str) -> None:
    row.get_by_role("link").click()
    area = content(page)
    button(area, "編輯").click()
    set_dashboard_name(page, title)
    save_change(page, button(area, re.compile(r"^(儲存|更新)$")), "/api/qrys", ("PUT", "PATCH"))


def rename_regulation(page: Page, row: Locator, title: str) -> None:
    row.hover()
    row.get_by_role("button").filter(has=page.get_by_test_id("EditSharpIcon")).click()
    dialog = page.get_by_role("dialog")
    dialog.get_by_role("textbox").fill(title)
    save_change(page, button(dialog, "送出"), "/api/regulations", ("PUT", "PATCH"))
    expect(dialog).to_be_hidden()


def delete_crud_row(page: Page, grid: Locator, row: Locator, endpoint: str, record_id: str) -> None:
    row.get_by_role("checkbox", name="Select row", exact=True).check()
    expect(grid.get_by_role("row", selected=True)).to_have_count(1)
    expect(row).to_have_attribute("aria-selected", "true")
    button(content(page), "刪除").click()
    dialog = page.get_by_role("dialog", name="刪除確認", exact=True)
    expect(dialog).to_contain_text(re.compile(r"所選的\s*1\s*個項目"))
    save_change(
        page, button(dialog, "確認刪除"), f"{endpoint}/{record_id}", ("DELETE",),
        capture_toast=endpoint != "/api/regulations",
    )
    expect(dialog).to_be_hidden()


def check_crud_lifecycle(
    page: Page,
    *,
    create: Callable[[Page], dict[str, object]],
    name_key: str,
    route: str,
    endpoint: str,
    rename: Callable[[Page, Locator, str], None],
) -> dict[str, object]:
    record = create(page)
    title = str(record[name_key])
    grid = open_crud_list(page, route)
    row = crud_row(page, grid, title)
    record_id = row.get_attribute("data-id")
    if not record_id:
        raise AssertionError(f"找不到本次新增的資料識別碼「{title}」")

    updated_title = f"{title}-已編輯"
    print(f"    編輯 {title}", flush=True)
    try:
        rename(page, row, updated_title)
        remove_crud_record(page, route, endpoint, updated_title, record_id)
    except (Error, AssertionError) as error:
        raise AssertionError(f"臨時測試資料識別碼 {record_id}，名稱「{title}」。\n{error}") from error
    return {"created_name": title, "edited_name": updated_title, "record_id": record_id, "deleted": True}


def remove_crud_record(page: Page, route: str, endpoint: str, title: str, record_id: str) -> None:
    grid = open_crud_list(page, route)
    updated = crud_row(page, grid, title)
    expect(updated).to_have_attribute("data-id", record_id)
    print(f"    刪除 {title}", flush=True)
    delete_crud_row(page, grid, updated, endpoint, record_id)
    grid = open_crud_list(page, route)
    removed = crud_row(page, grid, title)
    expect(grid.get_by_text(re.compile(r"^(?:No rows|No results found)\.?$"))).to_be_visible()
    expect(removed).to_have_count(0)
    if endpoint == "/api/regulations":
        capture_operation_screenshot("delete", has_toast=False)


def check_schedule_draft(page: Page) -> None:
    open_menu(page, "排程與告警", "排程")
    button(content(page), "新增").click()
    dialog = page.get_by_role("dialog", name="新增排程", exact=True)
    periodic = dialog.get_by_role("radio", name="週期性", exact=True)
    once = dialog.get_by_role("radio", name="一次性", exact=True)
    expect(periodic).to_be_checked()
    once.check()
    expect(once).to_be_checked()
    button(dialog, "取消").click()
    expect(dialog).to_be_hidden()
    expect_route(page, "/schedule/list")


def check_alert_draft(page: Page, *, label: str, route: str, periodic: bool) -> None:
    open_menu(page, "排程與告警", label)
    area = content(page)
    button(area, "新增").click()
    expect_route(page, route)
    name = area.get_by_role("textbox", name="輸入告警名稱", exact=True)
    title = f"自動化測試{label}草稿"
    name.fill(title)
    expect(name).to_have_value(title)
    level = button(area, "低")
    level.click()
    expect(level).to_have_attribute("aria-pressed", "true")
    expect(area.get_by_role("tab", name="發送設定", exact=True)).to_be_visible()
    if periodic:
        expect(area.get_by_role("table").get_by_role("row")).to_have_count(4)
    else:
        group = button(area, "AND")
        area.locator('[draggable="true"]').filter(
            has=page.get_by_text(CLASSIFICATION_FIELD, exact=True)
        ).drag_to(group)
        expect(group.locator("xpath=..").get_by_role("combobox")).to_have_text("IS")


def check_approval_draft(page: Page) -> None:
    open_menu(page, "簽核流程")
    area = content(page)
    button(area, "新增").click()
    expect_route(page, "/approval/create")
    name = area.get_by_role("textbox", name="輸入簽核流程名稱", exact=True)
    name.fill("自動化測試簽核草稿")
    expect(name).to_have_value("自動化測試簽核草稿")
    expect(area.get_by_role("checkbox", name="啟用知會", exact=True)).not_to_be_checked()
    button(area, "取消").click()
    expect_route(page, "/approval/list")


def check_event_history_status(page: Page) -> None:
    check_page(page, ("事件管理", "審核歷程"), "/approval-trail", "審核歷程")
    area = content(page)
    status = area.get_by_role("combobox", name="狀態", exact=True)
    for option in ("處理中", "結案"):
        status.click()
        page.get_by_role("option", name=option, exact=True).click()
        expect(status).to_have_text(option)
        expect(area.get_by_role("grid").get_by_role("columnheader", name="狀態", exact=True)).to_be_visible()


CATEGORIES: dict[str, tuple[str, tuple[Case, ...]]] = {
    "home": ("首頁與側邊選單", (
        Case("sidebar", "收合與展開側邊選單，再回首頁", check_home_menu),
    )),
    "dashboards": ("儀表板", (
        Case("database-status", "資料庫狀態儀表板", check_database_status_dashboard),
        Case("dashboard-crud", "新增、編輯及刪除臨時儀表板", partial(
            check_crud_lifecycle, create=create_dashboard, name_key="dashboard_name",
            route="/dashboard", endpoint="/api/qrys", rename=rename_dashboard,
        ), "--crud"),
        # Case("system-resources", "系統資源儀表板", partial(
        #     check_dashboard, title="系統資源儀表板 (預設)", chart_title="系統CPU", optional=True,
        # )),
        # Case("node-resources", "節點資源儀表板", partial(
        #     check_dashboard, title="節點資源儀表板 (預設)", chart_title="節點CPU", optional=True,
        # )),
    )),
    "reports": ("報表查詢", (
        Case("sql-preset", "SQL 執行報表套用「過去 7 天」", check_report_preset),
        Case("sql-range", "SQL 執行報表套用指定日期區間", check_report_range),
        navigation_case("return-data", "/return-data", "報表查詢", "回傳值查詢"),
        Case("create-report", "新增報表，依人事時地物選欄位、查詢並儲存", check_report_creation, "--create-report"),
        Case("report-crud", "新增、編輯及刪除臨時報表", partial(
            check_crud_lifecycle, create=check_report_creation, name_key="report_name",
            route="/report-list", endpoint="/api/qrys", rename=rename_report,
        ), "--crud"),
    )),
    "charts": ("統計圖表", (
        Case("sql-trend", "搜尋並開啟資料庫 SQL 執行次數趨勢圖", check_chart),
        Case("create-chart", "新增資料庫使用者次數圖表、重整並儲存", check_chart_creation, "--create-chart"),
        Case("chart-crud", "新增、編輯及刪除臨時圖表", partial(
            check_crud_lifecycle, create=check_chart_creation, name_key="chart_name",
            route="/chart", endpoint="/api/qrys", rename=rename_chart,
        ), "--crud"),
    )),
    "classification": ("資料分類", (
        navigation_case("datasets", "/value-set/list", "資料分類", "資料集"),
        navigation_case("filter-sets", "/filter-set/list", "資料分類", "條件集"),
        Case("create-dataset", "新增資料庫使用者資料集並自訂資料 test", check_dataset_creation, "--create-classification"),
        Case("create-filter-set", "新增資料庫使用者條件集並設為 EXIST", check_filter_set_creation, "--create-classification"),
        Case("dataset-crud", "新增、編輯及刪除臨時資料集", partial(
            check_crud_lifecycle, create=check_dataset_creation, name_key="dataset_name",
            route="/value-set/list", endpoint="/api/valueSet",
            rename=partial(rename_classification, field_name="資料集名稱", endpoint="/api/valueSet"),
        ), "--crud"),
        Case("filter-set-crud", "新增、編輯及刪除臨時條件集", partial(
            check_crud_lifecycle, create=check_filter_set_creation, name_key="filter_set_name",
            route="/filter-set/list", endpoint="/api/filterSet",
            rename=partial(rename_classification, field_name="請輸入", endpoint="/api/filterSet"),
        ), "--crud"),
    )),
    "regulations": ("法規", (
        navigation_case("regulations", "/regulation/list", "法規", title="法規清單"),
        Case("regulation-crud", "新增、編輯及刪除臨時法規", partial(
            check_crud_lifecycle, create=create_regulation, name_key="regulation_name",
            route="/regulation/list", endpoint="/api/regulations", rename=rename_regulation,
        ), "--crud"),
    )),
    "alerts": ("排程與告警", (
        navigation_case("schedules", "/schedule/list", "排程與告警", "排程"),
        Case("schedule-draft", "切換排程類型並取消新增", check_schedule_draft),
        navigation_case("periodic-alerts", "/periodic-alert/list", "排程與告警", "週期告警"),
        Case("periodic-alert-draft", "填寫週期告警草稿並核對執行時間預覽", partial(
            check_alert_draft, label="週期告警", route="/periodic-alert/create", periodic=True,
        )),
        navigation_case("real-time-alerts", "/realtime-alert/list", "排程與告警", "即時告警"),
        Case("real-time-alert-draft", "填寫即時告警草稿並加入觸發條件", partial(
            check_alert_draft, label="即時告警", route="/realtime-alert/create", periodic=False,
        )),
        navigation_case("history", "/historical-record/list", "排程與告警", "歷史紀錄"),
    )),
    "events": ("事件管理", (
        navigation_case("review", "/approval-events", "事件管理", "事件審核"),
        navigation_case("history", "/approval-trail", "事件管理", "審核歷程"),
        Case("history-status-filter", "切換審核歷程的處理中與結案篩選", check_event_history_status),
    )),
    "approval": ("簽核流程", (
        navigation_case("flows", "/approval/list", "簽核流程"),
        Case("approval-draft", "填寫簽核流程草稿、檢查知會設定並取消", check_approval_draft),
    )),
    "system": ("系統管理", (
        navigation_case("audit-log", "/audit-log-list", "系統管理", "稽核日誌", title="稽核日誌清單"),
    )),
}


def run_cases(
    page: Page,
    categories: tuple[str, ...],
    output_dir: Path,
    *,
    create_report: bool = False,
    create_chart: bool = False,
    create_classification: bool = False,
    crud: bool = False,
) -> int:
    start_url = page.url
    enabled = {
        "--create-report": create_report,
        "--create-chart": create_chart,
        "--create-classification": create_classification,
        "--crud": crud,
    }
    results = []
    for key in categories:
        category, cases = CATEGORIES[key]
        print(f"\n【{category}】", flush=True)
        for case in cases:
            result = {"category": category, "id": f"{key}/{case.id}", "name": case.name}
            results.append(result)
            page_errors: list[str] = []
            status_screenshots: dict[str, str] = {}
            result_screenshots: dict[str, str] = {}
            operation_screenshot_errors: dict[str, str] = {}

            def record_page_error(error: Error) -> None:
                page_errors.append(str(error))

            def record_operation(operation: str, has_toast: bool) -> None:
                kind = "status" if has_toast else "result"
                screenshot = Path(key) / f"{case.id}-{operation}-{kind}.png"
                try:
                    if has_toast:
                        toast = page.get_by_role("alert").filter(has_text=STATUS_MESSAGES[operation]).last
                        expect(toast).to_be_in_viewport(ratio=0.9, timeout=8_000)
                    (output_dir / screenshot).parent.mkdir(parents=True, exist_ok=True)
                    page.screenshot(path=output_dir / screenshot, timeout=5_000)
                except (AssertionError, Error, OSError) as error:
                    operation_screenshot_errors[f"{operation}-{kind}"] = str(error).strip()
                else:
                    screenshots = status_screenshots if has_toast else result_screenshots
                    screenshots[operation] = screenshot.as_posix()

            page.on("pageerror", record_page_error)
            screenshot_token = operation_screenshot_recorder.set(record_operation)
            try:
                if case.required_option and not enabled[case.required_option]:
                    raise CaseSkipped(f"使用 {case.required_option} 執行此新增案例")
                page.goto(start_url, wait_until="domcontentloaded")
                expect(button(sidebar(page), "首頁")).to_be_visible()
                data = case.action(page)
            except CaseSkipped as error:
                result.update(status="SKIP", detail=str(error))
            except (AssertionError, Error) as error:
                result.update(status="FAIL", detail=str(error).strip())
                if page_errors:
                    result["page_errors"] = page_errors
            else:
                result["status"] = "PASS"
                if data:
                    result["data"] = data
            finally:
                operation_screenshot_recorder.reset(screenshot_token)
                page.remove_listener("pageerror", record_page_error)

            if status_screenshots:
                result["status_screenshots"] = status_screenshots
            if result_screenshots:
                result["result_screenshots"] = result_screenshots
            if operation_screenshot_errors:
                result["operation_screenshot_errors"] = operation_screenshot_errors
                if result["status"] == "PASS":
                    result.update(status="FAIL", detail="新增或刪除截圖取得失敗，詳見 operation_screenshot_errors。")

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


def run(
    playwright: Playwright,
    categories: tuple[str, ...],
    output_dir: Path,
    login_timeout: int,
    *,
    create_report: bool = False,
    create_chart: bool = False,
    create_classification: bool = False,
    crud: bool = False,
) -> int:
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
            return run_cases(
                page, categories, output_dir,
                create_report=create_report, create_chart=create_chart,
                create_classification=create_classification,
                crud=crud,
            )
        finally:
            context.close()
    finally:
        browser.close()


def main() -> int:
    parser = argparse.ArgumentParser(description="DAM+ 網頁功能點擊測試")
    parser.add_argument("--list", action="store_true", help="列出功能分類與測試案例")
    parser.add_argument("--category", action="append", choices=CATEGORIES, help="指定分類，可重複使用。預設包含新增、編輯與刪除測試")
    parser.add_argument("--create-report", action="store_true", help="指定報表分類時，一併執行新增報表")
    parser.add_argument("--create-chart", action="store_true", help="指定圖表分類時，一併執行新增圖表")
    parser.add_argument("--create-classification", action="store_true", help="指定資料分類時，一併執行新增資料集與條件集")
    parser.add_argument("--crud", action="store_true", help="指定分類時，一併驗證臨時測試資料的新增、編輯與刪除")
    parser.add_argument("--output", type=Path, help="指定截圖及測試結果的輸出資料夾")
    parser.add_argument("--login-timeout", type=int, default=180, help="手動登入等待秒數，預設 180")
    args = parser.parse_args()
    if args.login_timeout <= 0:
        parser.error("--login-timeout 必須大於 0")

    full_suite = args.category is None
    categories = tuple(key for key in CATEGORIES if full_suite or key in args.category)
    if args.list:
        for key in categories:
            name, cases = CATEGORIES[key]
            print(f"【{name}】 {key}")
            for case in cases:
                option = f"（{case.required_option}）" if case.required_option and not full_suite else ""
                print(f"  {case.name}{option}")
        return 0

    output_dir = args.output or Path(__file__).resolve().parent / "screenshots" / datetime.now().strftime("%Y%m%d-%H%M%S-%f")
    try:
        with sync_playwright() as playwright:
            return run(
                playwright, categories, output_dir, args.login_timeout,
                create_report=full_suite or args.create_report,
                create_chart=full_suite or args.create_chart,
                create_classification=full_suite or args.create_classification,
                crud=full_suite or args.crud,
            )
    except (AssertionError, Error, KeyError, OSError) as error:
        print(f"測試執行中止。{str(error).strip().splitlines()[0]}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
