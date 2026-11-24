import json
import os
import re
import subprocess
import sys
from datetime import datetime
from pathlib import Path, PurePosixPath
from secrets import compare_digest, token_hex
from threading import Lock, Thread
from urllib.parse import urlsplit

from flask import Flask, abort, redirect, render_template, request, send_file, session, url_for

from load_env import ENV_FIELDS, env_defaults
from main import CATEGORIES


PROJECT_DIR = Path(__file__).resolve().parent
RUN_ID = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,127}")
RUN_MARKER = "web-run.json"
SUMMARY = "summary.json"
FIELD_LABELS = {
    "BASE_URL": "測試站台網址",
    "TEST_USERNAME": "測試帳號",
    "TEST_PASSWORD": "測試密碼",
    "TEST_CHANGE_PASSWORD": "變更用密碼",
}
TEST_OPTIONS = {
    "--create-report": "新增並保留測試報表",
    "--create-chart": "新增並保留測試圖表",
    "--create-classification": "新增並保留測試資料集及條件集",
    "--crud": "新增、編輯及刪除臨時測試資料",
}
CASE_STATES = {"PASS": "通過", "FAIL": "失敗", "SKIP": "略過"}
RUN_STATES = {
    "starting": "啟動中",
    "login": "等待登入",
    "running": "測試中",
    "complete": "已完成",
    "aborted": "執行中止",
}
ACTIVE_STATES = ("starting", "login", "running")
RUN_MESSAGES = {
    "starting": "正在啟動 Chrome。",
    "login": "請到測試開啟的 Chrome 視窗輸入驗證碼並按下「登入」。",
    "running": "已登入，正在執行測試。完成後會自動顯示報告。",
    "aborted": "測試未完成，請返回測試設定重新執行。",
}
IMAGE_TYPES = {".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".webp": "image/webp"}


def run_file(directory: Path, relative_path: str) -> Path | None:
    path = PurePosixPath(relative_path.replace("\\", "/"))
    if path.is_absolute() or not path.parts or ".." in path.parts or ":" in relative_path:
        return None
    try:
        filename = directory.joinpath(*path.parts).resolve()
        if filename.is_relative_to(directory) and filename.is_file():
            return filename
    except (OSError, ValueError, RuntimeError):
        pass
    return None


def read_json(directory: Path, name: str) -> dict | None:
    filename = run_file(directory, name)
    if filename is None:
        return None
    try:
        data = json.loads(filename.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    return data if isinstance(data, dict) else None


def screenshots(case: dict):
    if isinstance(case.get("screenshot"), str):
        yield "案例截圖", case["screenshot"]
    for field, kind in (("status_screenshots", "成功提示"), ("result_screenshots", "操作結果")):
        files = case.get(field)
        if isinstance(files, dict):
            for operation, path in files.items():
                if isinstance(path, str):
                    label = {"create": "新增", "update": "編輯", "delete": "刪除"}.get(operation, operation)
                    yield f"{label} · {kind}", path


class TestRuns:
    def __init__(self, root: Path):
        self.root = root.resolve()
        self.lock = Lock()
        self.active_id = None
        self.phase = None

    def start(self, environment: dict[str, str], categories: list[str], options: list[str]) -> str | None:
        with self.lock:
            if self.active_id is not None:
                return None
            now = datetime.now().astimezone()
            run_id = now.strftime("%Y%m%d-%H%M%S-%f")
            directory = self.root / run_id
            directory.mkdir(parents=True, exist_ok=False)
            metadata = {"started_at": now.isoformat(timespec="seconds"), "categories": categories}
            self.write_marker(directory, metadata)
            self.active_id = run_id
            self.phase = "starting"
            Thread(target=self.execute, args=(directory, metadata, environment, options), daemon=True).start()
            return run_id

    @staticmethod
    def write_marker(directory: Path, metadata: dict) -> None:
        (directory / RUN_MARKER).write_text(json.dumps(metadata, ensure_ascii=False), encoding="utf-8")

    def execute(self, directory: Path, metadata: dict, environment: dict[str, str], options: list[str]) -> None:
        command = [sys.executable, "-u", str(PROJECT_DIR / "main.py"), "--output", str(directory)]
        for category in metadata["categories"]:
            command.extend(("--category", category))
        command.extend(options)
        try:
            with subprocess.Popen(
                command, cwd=PROJECT_DIR, env={**os.environ, **environment, "PYTHONIOENCODING": "utf-8"},
                stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, encoding="utf-8", errors="replace",
            ) as process:
                for line in process.stdout:
                    if line.startswith("請在 Chrome 輸入驗證碼"):
                        with self.lock:
                            self.phase = "login"
                    elif line.startswith("登入成功，開始測試。"):
                        with self.lock:
                            self.phase = "running"
        except OSError:
            pass
        finally:
            with self.lock:
                metadata["finished_at"] = datetime.now().astimezone().isoformat(timespec="seconds")
                metadata["last_phase"] = self.phase
                try:
                    self.write_marker(directory, metadata)
                finally:
                    self.active_id = None
                    self.phase = None

    def get(self, run_id: str) -> dict | None:
        if not RUN_ID.fullmatch(run_id):
            return None
        directory = self.root / run_id
        try:
            if directory.resolve() != directory or not directory.is_dir():
                return None
        except (OSError, RuntimeError):
            return None

        with self.lock:
            metadata = read_json(directory, RUN_MARKER) or {}
            active_phase = self.phase if self.active_id == run_id else None
        report = read_json(directory, SUMMARY)
        results = report.get("results") if report else None
        counts = None
        message = ""
        if active_phase:
            state = active_phase
        elif isinstance(results, list):
            state = "complete"
            results = [case for case in results if isinstance(case, dict)]
            counts = {status: sum(case.get("status") == status for case in results) for status in CASE_STATES}
        elif metadata:
            state = "aborted"
            if metadata.get("last_phase") == "starting":
                message = "測試在登入前中止。請確認已安裝 Chrome，並檢查測試站台可連線。"
            elif metadata.get("last_phase") == "login":
                message = "尚未完成登入。請確認測試帳號、密碼及驗證碼，並在 Chrome 關閉前完成登入。"
        else:
            return None

        started_at = metadata.get("started_at") or datetime.fromtimestamp(
            directory.stat().st_mtime,
        ).astimezone().isoformat(timespec="seconds")
        return {
            "id": run_id, "directory": directory, "state": state, "results": results or [], "counts": counts,
            "message": message or RUN_MESSAGES.get(state, ""), "started_at": started_at,
            "finished_at": metadata.get("finished_at"), "categories": metadata.get("categories", []),
        }

    def history(self) -> list[dict]:
        if not self.root.is_dir():
            return []
        records = [run for directory in self.root.iterdir() if (run := self.get(directory.name))]
        return sorted(records, key=lambda run: run["started_at"], reverse=True)


def target_origin(value: str) -> tuple[str, str, int] | None:
    if "\\" in value or any(character.isspace() or ord(character) < 32 for character in value):
        return None
    try:
        url = urlsplit(value)
        port = url.port
    except ValueError:
        return None
    if url.scheme not in ("http", "https") or not url.hostname or url.username is not None or port == 0:
        return None
    return url.scheme, url.hostname, port or (443 if url.scheme == "https" else 80)


def create_app(output_root: Path = PROJECT_DIR / "screenshots") -> Flask:
    app = Flask(__name__)
    app.config.update(
        SECRET_KEY=os.urandom(32), TRUSTED_HOSTS=["127.0.0.1", "localhost"],
        SESSION_COOKIE_SAMESITE="Strict", MAX_CONTENT_LENGTH=32_768,
    )
    app.json.ensure_ascii = False
    runs = TestRuns(output_root)
    app.jinja_env.globals.update(
        case_states=CASE_STATES, run_states=RUN_STATES, categories=CATEGORIES,
        active_states=ACTIVE_STATES, screenshots=screenshots,
    )

    @app.after_request
    def protect_local_data(response):
        response.headers["Cache-Control"] = "no-store"
        response.headers["Referrer-Policy"] = "no-referrer"
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        return response

    def form(values, selected, options, error="", status=200):
        token = session.setdefault("csrf", token_hex(32))
        return render_template(
            "index.html", fields=FIELD_LABELS, values=values, selected=selected, options=options,
            test_options=TEST_OPTIONS, runs=runs.history(), token=token, error=error,
        ), status

    @app.get("/")
    def index():
        defaults = env_defaults()
        base_url = defaults["BASE_URL"].strip()
        values = {"BASE_URL": base_url if target_origin(base_url) else "", "TEST_USERNAME": defaults["TEST_USERNAME"]}
        return form(values, CATEGORIES, [])

    @app.post("/runs")
    def start():
        expected = session.get("csrf")
        posted = request.form.get("csrf", "")
        if not expected or not compare_digest(posted.encode(), expected.encode()):
            abort(403)

        environment = {key: request.form.get(key, "") for key in ENV_FIELDS}
        values = {"BASE_URL": environment["BASE_URL"].strip(), "TEST_USERNAME": environment["TEST_USERNAME"]}
        environment.update(values)
        defaults = env_defaults()
        environment["BASE_URL"] = environment["BASE_URL"] or defaults["BASE_URL"].strip()
        environment["TEST_USERNAME"] = environment["TEST_USERNAME"] or defaults["TEST_USERNAME"]
        origin = target_origin(environment["BASE_URL"])
        selected = [key for key in CATEGORIES if key in request.form.getlist("category")]
        options = [key for key in TEST_OPTIONS if key in request.form.getlist("option")]
        if origin is None:
            return form(values, selected, options, "請輸入有效的 HTTP 或 HTTPS 測試站台網址。", 400)
        same_origin = origin == target_origin(defaults["BASE_URL"].strip())
        same_account = environment["TEST_USERNAME"] == defaults["TEST_USERNAME"]
        if same_origin and same_account:
            for key in ("TEST_PASSWORD", "TEST_CHANGE_PASSWORD"):
                environment[key] = environment[key] or defaults[key]
        if not environment["TEST_USERNAME"].strip() or not environment["TEST_PASSWORD"]:
            return form(values, selected, options, "請填寫測試帳號與密碼。使用預設站台與帳號時，密碼可留白。", 400)
        if not selected:
            return form(values, selected, options, "請至少選取一個測試分類。", 400)
        if any("\0" in value for value in environment.values()):
            return form(values, selected, options, "測試參數包含無法使用的字元。", 400)
        try:
            run_id = runs.start(environment, selected, options)
        except OSError:
            return form(values, selected, options, "無法建立測試結果資料夾，請檢查 screenshots 的寫入權限。", 500)
        if run_id is None:
            return form(values, selected, options, "已有測試在執行，請等它完成後再啟動下一次測試。", 409)
        return redirect(url_for("detail", run_id=run_id), code=303)

    def find_run(run_id):
        run = runs.get(run_id)
        if run is None:
            abort(404)
        return run

    @app.get("/runs/<run_id>")
    def detail(run_id):
        return render_template("run.html", run=find_run(run_id))

    @app.get("/runs/<run_id>/state")
    def state(run_id):
        run = find_run(run_id)
        return {"state": run["state"], "label": RUN_STATES[run["state"]], "message": run["message"]}

    @app.get("/runs/<run_id>/images/<path:filename>")
    def image(run_id, filename):
        run = find_run(run_id)
        relative_path = filename.replace("\\", "/")
        if run["state"] != "complete" or not any(
            path.replace("\\", "/") == relative_path for case in run["results"] for _, path in screenshots(case)
        ):
            abort(404)
        path = run_file(run["directory"], relative_path)
        if path is None or path.suffix.lower() not in IMAGE_TYPES:
            abort(404)
        return send_file(path, mimetype=IMAGE_TYPES[path.suffix.lower()])

    return app


if __name__ == "__main__":
    create_app().run(host="127.0.0.1", port=8765, debug=False, load_dotenv=False)
