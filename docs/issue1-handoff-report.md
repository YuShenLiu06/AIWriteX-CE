# Issue #1 交接报告 — 鉴权传递缺陷(Basic Auth + SPA fetch 不兼容)

> 交接时间: 2026-06-28 · 容器: `aiwritex-server` (Up, healthy, 宿主 8888)
> 前序: `docs/issue1-fix-report.md`(原始 3 个 bug 的修复报告)

---

## 一、TL;DR(给接手人)

- **原始 3 个 bug(鉴权默认不生效 / 配置 500 / 模板 500)在服务端已修复并验证**——`curl -u admin:<pwd>` 下所有端点 200,无凭证 401,响应头含正确 `WWW-Authenticate`。
- **但真实浏览器测试暴露出一个新的、更关键的缺陷**:浏览器能加载主页(`GET /` 鉴权通过),却**不把 HTTP Basic 凭证带到 SPA 的 `fetch('/api/*')` 请求上**,导致 `/api/config`、`/api/templates/categories`、`/api/articles`、`/api/scheduled-tasks/runtime/status` **全部 401** → 前端"文章/模板/配置加载失败"。
- **根因**:HTTP Basic Auth 与基于 `fetch()` 的 SPA 天然不兼容。浏览器对"原生 401 弹窗获取的凭证"不会可靠地附加到程序化 `fetch` 请求上(仅靠内嵌凭证 URL 才会被 Chrome 激进缓存并附加)。
- **我之前的截图"全好"是假象**:我用内嵌凭证 URL `http://admin:pwd@host/` 开浏览器,Chrome 缓存凭证并对所有同源请求自动带凭证 → /api/* 全 200。普通浏览器走正常弹窗,不带凭证 → /api/* 全 401。**测试方法掩盖了真 bug,是我的失误。**
- **推荐修复**:见第五节(已验证可行方向:改 SPA fetch 包装 + 内嵌凭证 URL;或更稳妥地换成 session/cookie-token 鉴权)。

---

## 二、当前环境状态

| 项 | 值 |
|---|---|
| 容器 | `aiwritex-server`,Up 32min,healthy |
| 端口 | 宿主 `0.0.0.0:8888 -> 8888`(IPv4+IPv6) |
| 镜像 | `aiwritex:latest`(已 rebuild,含全部修复) |
| 容器内监听 | `0.0.0.0:8888`(`/proc/net/tcp` = `00000000:22B8`) |
| 鉴权开关 | `AIWRITEX_AUTH_ENABLED=true` |
| 凭证来源 | `.env`(已 gitignore) |
| 用户名 | `admin` |
| 密码 | `<redacted, 见本地 .env>` |
| API Key(可选) | `<redacted, 见本地 .env>` |

> `.env` 内容:`AIWRITEX_AUTH_USER=admin` / `AIWRITEX_AUTH_PASSWORD=<redacted, 见本地 .env>` / `AIWRITEX_AUTH_API_KEY=<redacted, 见本地 .env>` / `AIWRITEX_AUTH_ENABLED=true` / `AIWRITEX_PORT=8888`。`.env` 已在 `.gitignore`,不会提交。

---

## 三、铁证(日志 + curl + 真机)

### 3.1 服务端本身完全正确
```
端点                                   带凭证(-u)   无凭证
/                                      200          401
/api/config/                           200          401
/api/templates/categories              200          401
/api/articles/                         200          401
/api/scheduled-tasks/runtime/status    200          401
```
- `/api/config/` 响应体是**满的**:11 个模型平台(OpenRouter/Deepseek/Grok/Claude/Qwen/Gemini/Ollama/SiliconFlow/Kimi/GLM/MiniMax),各有 models/api_base/max_tokens。
- `/api/templates/categories` 返回 13 个真实分类(财经投资/科技数码/…)。
- `/api/articles` 是 307 → `/api/articles/` → 200(只是末尾斜杠,无害)。
- 401 响应头含 `www-authenticate: Basic realm="AIWriteX"`(格式正确)。
- 鉴权代码(`web/auth.py`)无任何 localhost/trusted 本机放行逻辑——对全部来源一视同仁。

### 3.2 用户浏览器(192.168.65.1)的 /api/* 全 401(根因铁证)
```
INFO: 192.168.65.1 - "GET /api/config/ HTTP/1.1"                    401
INFO: 192.168.65.1 - "GET /api/templates/categories HTTP/1.1"       401
INFO: 192.168.65.1 - "GET /api/articles/ HTTP/1.1"                  401
INFO: 192.168.65.1 - "GET /api/scheduled-tasks/runtime/status"  401
```
浏览器加载了主页(GET / 200,"进了主页面"),但**所有后续 API 调用 401** → 前端"文章/模板/配置加载失败"。

### 3.3 内嵌凭证 URL 下,干净的同源 fetch 是 200(证明浏览器能带凭证,只是普通方式不带)
chrome-devtools 真机测试:从 `http://admin:pwd@localhost:8888/` 页面发起**不带内嵌凭证的绝对 URL** fetch:
```
fetch('http://localhost:8888/api/config/ui-config') → 200, {"theme":"light",...}
```
证明:只要凭证被浏览器缓存(内嵌 URL 方式),干净的同源请求就会被自动带上 Basic 头 → 200。

### 3.4 SPA 的相对 fetch 在内嵌凭证 URL 下会抛错(另一个待修 bug)
```
console error: 加载模板分类失败: TypeError: Failed to execute 'fetch':
  Request cannot be constructed from a URL that includes credentials: /api/config/template-categories
console error: 加载UI配置失败: ... /api/config/ui-config
```
原因:`fetch('/api/config/...')` 相对路径会解析成 `http://admin:pwd@host/api/config/...`(带凭证),`fetch()` 规范直接拒绝带 userinfo 的 URL。

---

## 四、机制解释(为什么 Basic Auth + SPA 会这样)

1. 首次访问 `GET /` → 服务端 401 + `WWW-Authenticate: Basic realm="AIWriteX"` → 浏览器**原生弹窗**。
2. 用户输入 `admin/pwd` → 浏览器重发 `GET /` 带 Basic 头 → 200,SPA HTML/JS 加载(表现为"进了主页面")。
3. SPA JS 执行,发起 `fetch('/api/config/...')` 等 XHR。
4. **问题在这一步**:浏览器对"原生弹窗获取的 Basic 凭证"**不会可靠地附加到程序化 `fetch` 请求上**(各浏览器实现不一,Chrome 尤其不稳定)。这些 `/api/*` 请求以**无凭证**发出 → 服务端 401 → 前端"加载失败"。
5. 浏览器**不会**对 XHR 的 401 再次弹窗(规范如此,防弹窗死循环),所以用户"看不到弹窗、却进不了内容"。
6. 只有当凭证通过**内嵌凭证 URL**(`http://user:pass@host/`)提供时,Chrome 才会激进缓存并对所有同源请求自动附加——这就是为什么我用内嵌 URL 测试时"全好",而普通浏览器"全坏"。

> 补充:VSCode 内置浏览器的 `{"detail":"无效的认证凭证"}` 是另一回事——VSCode webview 根本不支持 HTTP Basic 原生弹窗,所以连 `GET /` 都拿不到凭证。

---

## 五、推荐修复(按推荐度排序)

### 方案 A(最稳,推荐用于生产):换成 session/cookie 或 token 鉴权
- 新增 `POST /api/auth/login`(校验 user/pass),成功后下发 **HttpOnly cookie**(session id)或返回 **token**。
- SPA 登录表单提交 → 拿到 cookie/token → 后续所有 `fetch` 自动带 cookie(SameSite)或在 header 里带 token。
- `verify_auth` 放宽:接受 Basic / X-API-Key / 有效 session cookie 任一。
- 彻底消除 "Basic Auth 不传给 fetch" 的问题,且能提供"退出登录"。
- 代价:中等(加登录页 + session 存储),但这是 fetch-SPA 的正解。

### 方案 B(最小改动,已验证可行):改 SPA fetch 包装 + 内嵌凭证 URL
1. **修 SPA fetch**:加全局 `window.fetch` 包装,剥离请求 URL 里的 userinfo(让相对/绝对 fetch 都解析成干净 URL),消除第 3.4 节的抛错。
   ```js
   // 放在最早加载的 JS 顶部(index.html inline 或 main.js 顶)
   (function(){
     const _f = window.fetch;
     window.fetch = function(input, init){
       try {
         let url = (typeof input === 'string') ? input
                 : (input && input.url) ? input.url : null;
         if (url) {
           const u = new URL(url, location.origin);
           if (u.username || u.password) {
             const clean = u.origin + u.pathname + u.search + u.hash;
             input = (typeof input === 'string') ? clean : new Request(clean, input);
           }
         }
       } catch(e){}
       return _f.call(this, input, init);
     };
   })();
   ```
2. **用户改用内嵌凭证 URL**:`http://admin:<redacted, 见本地 .env>@localhost:8888/`。
3. 已验证(第 3.3 节):内嵌凭证文档下的干净 fetch 返回 200,浏览器会自动带 Basic 头。
- 代价:小。缺点:密码出现在 URL/历史里;登出不便;部分浏览器对内嵌凭证 URL 有安全提示。

### 方案 C(纯运维,临时绕过,不改代码):关鉴权或仅本机
- 临时把 `AIWRITEX_AUTH_ENABLED=false` 跑通功能验证(仅限受控环境,公网务必配合反代鉴权)。
- 不建议长期使用——会重新打开 issue #1 修掉的越权访问口子。

> 我的建议:**生产用方案 A**;若只想快速让用户能登录验证,**方案 B** 立即可用且已验证。

---

## 六、原始 Issue #1 三个 bug 的状态(服务端层面,已完成)

| Bug | 状态 | 说明 |
|---|---|---|
| #1 鉴权默认不生效(公网越权) | ✅ 已修复 | `GET /` 无凭证 401 + 正确 WWW-Authenticate;`lifespan` 拆分,鉴权恒初始化(fail-safe) |
| #2 配置 500(tuple) | ✅ 已修复 | `_ensure_config_dict` 自愈 + `load_config` 校验 + deepcopy 防别名;`/api/config/` 200 且数据满 |
| #3 模板 500(FileNotFoundError) | ✅ 已修复 | `get_template_dir` dev 分支 mkdir + `iterdir` 守卫 + Dockerfile `COPY knowledge`;`/api/templates/categories` 200 |

> 注意:这三个是**服务端**修复,验证方式是 `curl -u`(带凭证)。**真实浏览器的可用性问题(Basic Auth 不传给 fetch)是新发现的第四类问题,尚未修复,见第五节。**

---

## 七、已改动文件清单(本地未提交)

```
Dockerfile                           (+COPY knowledge, +mkdir 预建目录)
.dockerignore                        (放行 knowledge)
docker-compose.yml                   (移除 obsolete version)
src/ai_write_x/config/config.py      (_ensure_config_dict + load_config 校验 + deepcopy)
src/ai_write_x/web/auth.py           (load_auth_config 容忍非 dict)
src/ai_write_x/web/app.py            (lifespan 拆分异常边界, 鉴权恒初始化)
src/ai_write_x/utils/path_manager.py (dev 分支 mkdir)
src/ai_write_x/web/api/templates.py  (iterdir 守卫)
tests/test_issue1_fixes.py           (新增回归测试)
docs/issue1-fix-report.md            (前序修复报告)
docs/issue1-handoff-report.md        (本交接报告)
docs/issue1-screenshots/             (E2E 截图;注意:截图是用内嵌凭证 URL 取的,掩盖了 fetch 鉴权问题)
.env                                 (gitignored,测试凭证)
```

**待改动(方案 B)**:`src/ai_write_x/web/static/js/main.js`(或 index.html inline script)顶部加全局 fetch 包装。
**待改动(方案 A)**:`web/api/` 新增 auth 路由 + session 存储;`auth.py` 放宽接受 cookie;前端加登录页。

---

## 八、复现/验证命令(给接手人)

```bash
# 1. 服务端正确性(应全 200/401)
for ep in / /api/config/ /api/templates/categories /api/articles/ /api/scheduled-tasks/runtime/status; do
  echo "$ep -> 带:$(curl -s -o /dev/null -w '%{http_code}' -u admin:<redacted, 见本地 .env> http://localhost:8888$ep) 无:$(curl -s -o /dev/null -w '%{http_code}' http://localhost:8888$ep)"
done

# 2. 看用户浏览器是不是 /api/* 全 401(根因)
docker logs aiwritex-server --tail 200 2>&1 | grep -E '/api/' | grep -E '401|200'

# 3. 容器内确认监听 0.0.0.0
docker exec aiwritex-server sh -c "cat /proc/net/tcp | awk '\$2 ~ /:22B8/' "

# 4. 重建(若改了代码)
docker compose build && docker compose up -d
```

---

## 九、下一步建议(优先级)

1. **[P0] 修鉴权传递**:选方案 A 或 B,让普通浏览器能正常加载 /api/*。这是当前阻塞用户使用的唯一问题。
2. **[P1] 加 `Cache-Control: no-store`** 到 `/` 和 `/api/*`:防止 rebuild 后浏览器吃到旧缓存(本次也曾干扰判断)。
3. **[P2] 修 `/api/articles` 307**:router 统一末尾斜杠,避免无谓重定向。
4. **[P2] 提交代码**:确认方案后按 `fix:` 规范提交(`.env` 已 gitignore,勿提交)。
5. **[LOW] `.env.example` 占位密码启动期校验、鉴权失败速率限**(见前序报告第十节)。

---

## 十、后续修复：Basic Auth + SPA fetch 鉴权不传递（session cookie 方案）

> 接续第五节"方案 A（最稳，推荐用于生产）"——已落地，无新依赖。

- **根因**：浏览器对"原生 Basic 弹窗获取的凭证"不会可靠附加到程序化 `fetch()`，导致 SPA 加载主页（`GET /` 200）后所有 `/api/*` 调用 401，用户"看到主页面、却加载不出内容"（详见第三节铁证）。

- **修复方案**：引入 Starlette `SessionMiddleware`（签名 cookie，`itsdangerous` 随 starlette 安装，**无新依赖**）。
  - **后端**：新增 `POST /api/auth/login`（校验 user/pass，下发签名 cookie）、`POST /api/auth/logout`（清除会话）、`GET /api/auth/status`（查询当前会话）；`verify_auth` 放宽接受 session cookie，同时**保留 Basic + `X-API-Key` 向后兼容**；`GET /` 未登录改为 `302 → /login`（不再弹原生 Basic 框，从源头消除不传递缺陷）；WebSocket 鉴权同样接受该 session cookie。
  - **前端**：新增 `login.html` 登录页 + `auth-redirect.js`——仅观测 401 后跳转 `/login`，**不改写现有 95+ 处 fetch 调用**（最小侵入）。
  - **密钥**：新增环境变量 `AIWRITEX_SESSION_SECRET`；缺省时从 `AIWRITEX_AUTH_PASSWORD` 派生（改密码即令所有已签发会话失效）；生产环境应设置为足够长的随机字符串。

- **向后兼容**：`curl -u`、`X-API-Key` 头、WebSocket `?api_key=` 查询参数**仍然可用**——CLI / 脚本 / 第三方集成无需改动。

- **验证方式**：
  - 经 `docker compose` 运行 `tests/test_auth_sessions.py`（登录、登出、cookie 签名校验、向后兼容路径覆盖）。
  - 真机浏览器流程：访问 `/` → 跳 `/login` → 登录成功后 `/api/*` 全 200；Network 面板可见 `aiwritex_session` cookie 自动随同源请求发送。

- **不引入**：不增加新的运行时依赖（`itsdangerous` 随 starlette 安装）；不引入带数据库的重型 auth 框架（KISS）。
