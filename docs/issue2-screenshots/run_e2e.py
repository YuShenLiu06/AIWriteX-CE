# -*- coding: UTF-8 -*-
"""
Issue #2 浏览器 E2E 取证脚本(Playwright):定时任务状态生命周期。

针对修复「定时任务完成后 Web 面板仍显示『执行中』」,真实捕获三种状态:
  1. 失败 (failed) —— 启动一致性修复(Fix2)把残留 running 记录标记为 failed 后的真实展示
  2. 执行中 (running) —— 立即执行触发后、生成进行中的瞬时态
  3. 完成 (success) —— 生成成功(发布失败 → 未发布)的终态

设计要点:
- 镜像 issue1 脚本:sync_playwright + chromium + 上下文级 Basic Auth(http_credentials)。
- API 调用走 page.evaluate(fetch),复用浏览器上下文已携带的凭证。
- **先在 UI 选中目标任务**,使执行记录面板真实渲染,再截图(PNG 与 JSON 一一对应)。
- 失败状态复用 Fix2 产生的真实 failed 记录,无需人为制造失败;执行中/完成来自一次真实 run-now。
- 每个状态独立 try/except,失败写 <name>-ERROR.txt,绝不静默吞错、绝不伪造。

运行(仓库根目录):
  docker run --rm --add-host=host.docker.internal:host-gateway \\
    -v "$(pwd)/docs/issue2-screenshots:/out" \\
    [-e TASK_ID=task_2bd4f655] \\
    mcr.microsoft.com/playwright/python:v1.49.0-noble python /out/run_e2e.py
"""
import json
import os
import sys
import time
import traceback

from playwright.sync_api import sync_playwright

BASE = os.environ.get("AIWRITEX_BASE", "http://host.docker.internal:8888")
USER = "admin"
PASSWORD = "aiwritex-test-2026"
OUT = "/out"
TASK_ID = os.environ.get("TASK_ID", "task_2bd4f655")

NAV_SELECTOR = 'a.nav-link[data-view="scheduled-task-manager"]'
VIEWPORT = {"width": 1440, "height": 900}
POLL_INTERVAL = 3
POLL_TIMEOUT = 15 * 60  # 真实 LLM 生成 + 发布尝试,给足余量


def shot(page, name):
    path = f"{OUT}/{name}.png"
    page.screenshot(path=path, full_page=True)
    print(f"[shot] {path}")


def write_file(name, text):
    path = f"{OUT}/{name}"
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(text)
    print(f"[file] {path}")


def api_get(page, path):
    """浏览器上下文内 fetch GET(同源自动携带 Basic 凭证)。"""
    return page.evaluate(
        """async (url) => {
            const r = await fetch(url, {credentials: 'include'});
            let body = null;
            try { body = await r.json(); } catch (e) { body = await r.text(); }
            return {status: r.status, body: body};
        }""",
        f"{BASE}{path}",
    )


def api_post(page, path, payload=None):
    return page.evaluate(
        """async ([url, data]) => {
            const opt = {method: 'POST', credentials: 'include',
                         headers: data ? {'Content-Type': 'application/json'} : {}};
            if (data !== null && data !== undefined) opt.body = JSON.stringify(data);
            const r = await fetch(url, opt);
            let body = null;
            try { body = await r.json(); } catch (e) { body = await r.text(); }
            return {status: r.status, body: body};
        }""",
        [f"{BASE}{path}", payload],
    )


def latest_record(records_resp):
    body = records_resp.get("body") or {}
    records = (body.get("data") or {}).get("records") or []
    if not records:
        return None
    return sorted(records, key=lambda r: r.get("started_at") or "", reverse=True)[0]


def login(page):
    """POST /api/auth/login(表单)写入 session cookie,与浏览器上下文共享。
    必需:Issue #1 修复后 GET / 未登录会 303 → /login,http_credentials(仅响应 401 挑战)不再生效。"""
    resp = page.request.post(f"{BASE}/api/auth/login", form={"username": USER, "password": PASSWORD})
    print(f"[login] POST /api/auth/login -> HTTP {resp.status}")
    if resp.status != 200:
        raise RuntimeError(f"登录失败 HTTP {resp.status}: {resp.text()}")


def open_task_manager(page):
    login(page)
    page.goto(BASE, wait_until="networkidle", timeout=30000)
    if "/login" in page.url:
        raise RuntimeError(f"登录后仍被重定向到登录页: {page.url}")
    page.wait_for_timeout(1500)
    page.locator(NAV_SELECTOR).first.click()
    page.wait_for_timeout(1500)
    page.wait_for_selector("#scheduled-task-manager-view:not([style*='display: none'])", timeout=10000)
    shot(page, "00-task-manager")


def select_task(page, task_id):
    """选中任务卡片以加载执行记录面板;点击卡片左上角(标题区)避免误触动作按钮。"""
    card = page.locator(f'.scheduled-task-card[data-task-id="{task_id}"]').first
    if not card.count():
        return False
    card.click(position={"x": 20, "y": 20})
    try:
        page.wait_for_selector(".scheduled-task-history-item", timeout=5000)
    except Exception:
        pass
    page.wait_for_timeout(800)
    return True


def refresh_records_panel(page):
    try:
        btn = page.locator("#scheduled-task-history-refresh-btn")
        if btn.count():
            btn.first.click()
            page.wait_for_timeout(1000)
    except Exception as e:
        print(f"[refresh] 异常(忽略): {e}")


def capture(page, label, png_name, json_name, expect_label=None):
    """刷新并截图当前执行记录面板,同时落盘 records JSON;返回最新记录。

    为确保面板真实反映当前状态(而非停留在旧 DOM):先取一次 records 确认状态,
    再重新点击任务卡片强制 loadTaskRecords+renderHistory,并等待期望徽章文本出现。
    """
    resp = api_get(page, f"/api/scheduled-tasks/{TASK_ID}/records")
    write_file(json_name, json.dumps(resp.get("body"), ensure_ascii=False, indent=2))
    rec = latest_record(resp)
    cur_status = rec.get("status") if rec else None
    print(f"[state] {label}: status={cur_status} "
          f"finished_at={rec.get('finished_at') if rec else None}")

    # 重新选中任务卡片,强制面板重新拉取并渲染执行记录
    card = page.locator(f'.scheduled-task-card[data-task-id="{TASK_ID}"]').first
    if card.count():
        card.click(position={"x": 20, "y": 20})
    page.wait_for_timeout(1500)
    # 等待期望徽章文本出现(证明面板确已渲染到该状态)
    if expect_label:
        try:
            badge = page.locator(".scheduled-task-history-item .scheduled-task-status-badge").first
            badge.wait_for(state="visible", timeout=8000)
            for _ in range(20):
                txt = (badge.inner_text() or "").strip()
                if expect_label in txt:
                    break
                refresh_records_panel(page)
                page.wait_for_timeout(800)
        except Exception as e:
            print(f"[capture] 等待徽章「{expect_label}」超时(忽略): {e}")
    shot(page, png_name)
    return rec


def poll_until_terminal(page, task_id):
    deadline = time.time() + POLL_TIMEOUT
    while time.time() < deadline:
        resp = api_get(page, f"/api/scheduled-tasks/{task_id}/records")
        rec = latest_record(resp)
        if rec and rec.get("finished_at"):
            return rec, resp
        refresh_records_panel(page)  # 期间持续刷新,顺带验证自动刷新
        time.sleep(POLL_INTERVAL)
    raise TimeoutError("等待终态超时")


def write_readme(note):
    content = f"""# Issue #2 定时任务状态 E2E 取证说明

本目录由 `docs/issue2-screenshots/run_e2e.py` 生成,针对「定时任务完成后 Web 面板仍显示
『执行中』」的修复,真实捕获三种状态。PNG 与同名 JSON 一一对应(UI 截图 + 该时刻的 /records 响应)。

## 文件清单
- `00-task-manager.png` 定时任务管理视图入口
- `01-failed.png` / `01-failed.json` 失败(Fix2 启动一致性修复产生的 failed 记录)
- `02-running.png` / `02-running.json` 执行中(run-now 触发后瞬时态)
- `03-success.png` / `03-success.json` 完成(生成成功,发布失败 → 未发布)
- `ERROR.txt` / `*-ERROR.txt` 采集异常堆栈(若有)

被驱动任务: `{TASK_ID}`

## 配套真实取证命令(操作员粘贴**真实**容器输出,严禁编造)

# 启动一致性修复(Fix2)+ 任务执行日志
docker logs aiwritex-server 2>&1 | grep -E "一致性修复|开始执行|执行成功|执行失败" | tail -40

# 持久化执行记录(权威证据)
docker compose exec aiwritex cat /app/runtime_config/scheduled_task_execution_records.json

# 任务定义 last_status
docker compose exec aiwritex cat /app/runtime_config/scheduled_tasks.json

## 运行方式
docker run --rm --add-host=host.docker.internal:host-gateway \\
  -v "$(pwd)/docs/issue2-screenshots:/out" \\
  [-e TASK_ID=task_2bd4f655] \\
  mcr.microsoft.com/playwright/python:v1.49.0-noble python /out/run_e2e.py

## 本次运行备注
{note}
"""
    write_file("README.md", content)


def main():
    if not TASK_ID or TASK_ID == "REPLACE_WITH_TASK_ID":
        print("[fatal] 未设置 TASK_ID,请用 -e TASK_ID=task_xxxxxxxx 覆盖")
        sys.exit(2)

    terminal_rec = None
    errors = []
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, args=["--no-sandbox"])
        ctx = browser.new_context(http_credentials={"username": USER, "password": PASSWORD}, viewport=VIEWPORT)
        page = ctx.new_page()
        page.on("console", lambda m: errors.append(f"{m.type}: {m.text}") if m.type == "error" else None)
        page.on("pageerror", lambda e: errors.append(f"pageerror: {e}"))

        try:
            open_task_manager(page)
            if not select_task(page, TASK_ID):
                raise RuntimeError(f"未找到任务卡片 {TASK_ID}")

            # ---- 状态 1:失败 (failed) —— Fix2 修复后的真实 failed 记录 ----
            try:
                rec = capture(page, "失败(已存在的 failed 记录)", "01-failed", "01-failed.json", "失败")
                if not rec or rec.get("status") != "failed":
                    write_file("01-failed-NOTE.txt",
                               f"最新记录 status={(rec or {}).get('status')}(非 failed),"
                               "可能是任务已被重新执行;请查看 01-failed.json 全部历史记录。\n")
            except Exception:
                write_file("01-failed-ERROR.txt", traceback.format_exc())

            # ---- 状态 2:执行中 (running) ----
            try:
                run_resp = api_post(page, f"/api/scheduled-tasks/{TASK_ID}/run-now")
                print(f"[run-now] POST /run-now -> HTTP {run_resp.get('status')}")
                page.wait_for_timeout(1500)  # 等待 running 记录落库
                capture(page, "执行中(触发后瞬时)", "02-running", "02-running.json", "执行中")
            except Exception:
                write_file("02-running-ERROR.txt", traceback.format_exc())

            # ---- 轮询至终态 ----
            try:
                terminal_rec, terminal_resp = poll_until_terminal(page, TASK_ID)
                write_file("03-success.json", json.dumps(terminal_resp.get("body"), ensure_ascii=False, indent=2))
                print(f"[state] 完成: status={terminal_rec.get('status')} "
                      f"published={terminal_rec.get('published')} "
                      f"article_path={terminal_rec.get('article_path')}")
                # 重新选中任务卡片,等待「成功」徽章出现后再截图
                card = page.locator(f'.scheduled-task-card[data-task-id="{TASK_ID}"]').first
                if card.count():
                    card.click(position={"x": 20, "y": 20})
                try:
                    badge = page.locator(".scheduled-task-history-item .scheduled-task-status-badge").first
                    badge.wait_for(state="visible", timeout=8000)
                    for _ in range(20):
                        if "成功" in (badge.inner_text() or ""):
                            break
                        refresh_records_panel(page)
                        page.wait_for_timeout(800)
                except Exception as e:
                    print(f"[capture] 成功徽章等待超时(忽略): {e}")
                shot(page, "03-success")
                # 关键反 bug 断言
                assert terminal_rec.get("status") != "running", "终态仍为 running(BUG 未修复!)"
                assert terminal_rec.get("finished_at"), "finished_at 为空(BUG 未修复!)"
            except Exception:
                write_file("03-success-ERROR.txt", traceback.format_exc())

        except Exception as exc:  # noqa: BLE001
            write_file("ERROR.txt", f"{exc}\n{traceback.format_exc()}")
            try:
                shot(page, "ERROR")
            except Exception:
                pass

        print(f"[console-errors] count={len(errors)}")
        for e in errors[:20]:
            print("  CE:", e)
        ctx.close()
        browser.close()

    write_readme(f"- 控制台错误数: {len(errors)}\n- 终态记录: {terminal_rec}")
    print("DONE")


if __name__ == "__main__":
    main()
