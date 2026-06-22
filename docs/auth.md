# AIWriteX 认证机制

本文档说明 AIWriteX 的认证机制和安全配置。

---

## 认证方式

AIWriteX 支持**双轨认证**，两种方式可同时使用：

1. **Basic Auth**（HTTP 基础认证）
2. **API Key**（请求头认证）

---

## 1. Basic Auth

### 配置

通过环境变量配置：

```bash
AIWRITEX_AUTH_ENABLED=true
AIWRITEX_AUTH_USER=admin
AIWRITEX_AUTH_PASSWORD=your_secure_password
```

或通过 `config.yaml` 配置：

```yaml
auth:
  enabled: true
  user: "admin"
  password: "your_secure_password"
```

### 使用方式

#### curl

```bash
curl -u admin:your_password http://localhost:8888/api/config
```

#### 浏览器访问

访问 `http://localhost:8888` 时，浏览器会弹出原生登录框：

```
┌────────────────────────────┐
│     Authentication        │
│                            │
│  Username: [admin       ] │
│  Password: [************] │
│                            │
│        [Login] [Cancel]    │
└────────────────────────────┘
```

#### JavaScript (fetch)

```javascript
fetch('http://localhost:8888/api/config', {
  headers: {
    'Authorization': 'Basic ' + btoa('admin:your_password')
  }
})
```

---

## 2. API Key

### 配置

通过环境变量配置：

```bash
AIWRITEX_AUTH_API_KEY=your_secret_api_key
```

或通过 `config.yaml` 配置：

```yaml
auth:
  api_key: "your_secret_api_key"
```

### 使用方式

#### curl

```bash
curl -H "X-API-Key: your_secret_api_key" http://localhost:8888/api/config
```

#### JavaScript (fetch)

```javascript
fetch('http://localhost:8888/api/config', {
  headers: {
    'X-API-Key': 'your_secret_api_key'
  }
})
```

---

## 凭证优先级

当环境变量和 `config.yaml` 同时存在时，优先级如下：

1. **环境变量**（最高优先级）
2. **config.yaml**
3. **默认值**（最低优先级）

### 示例

```bash
# 环境变量
AIWRITEX_AUTH_USER=myuser

# config.yaml
auth:
  user: "config_user"

# 实际生效：myuser（环境变量优先）
```

---

## 环境变量名与 config 路径对照

| 环境变量 | config.yaml 路径 | 说明 |
|----------|------------------|------|
| `AIWRITEX_AUTH_ENABLED` | `auth.enabled` | 启用认证 |
| `AIWRITEX_AUTH_USER` | `auth.user` | Basic Auth 用户名 |
| `AIWRITEX_AUTH_PASSWORD` | `auth.password` | Basic Auth 密码 |
| `AIWRITEX_AUTH_API_KEY` | `auth.api_key` | API 密钥 |
| `AIWRITEX_CORS_ORIGINS` | `auth.cors_origins` | CORS 允许的源 |

---

## 浏览器弹窗原理

Basic Auth 使用 HTTP 标准的 `401 Unauthorized` 响应触发浏览器登录框：

1. 客户端请求受保护资源
2. 服务器返回 `401` + `WWW-Authenticate: Basic` 头
3. 浏览器检测到此头，弹出原生登录框
4. 用户输入凭证后，浏览器自动在请求头中携带 `Authorization: Basic base64(user:pass)`
5. 服务器验证凭证，返回资源

### 关键响应头

```
HTTP/1.1 401 Unauthorized
WWW-Authenticate: Basic realm="AIWriteX"
Content-Type: application/json
```

---

## WebSocket 鉴权

WebSocket 连接（如 `/ws/generate/logs`）使用查询参数传递凭证：

```javascript
// Basic Auth 方式
const ws = new WebSocket('ws://admin:password@localhost:8888/ws/generate/logs');

// API Key 方式（需要在后端实现支持）
const ws = new WebSocket('ws://localhost:8888/ws/generate/logs?api_key=your_key');
```

---

## 安全建议

### 1. 启用 HTTPS

生产环境必须使用 HTTPS，避免凭证被窃听：

```nginx
server {
    listen 443 ssl;
    ssl_certificate /path/to/cert.pem;
    ssl_certificate_key /path/to/key.pem;

    location / {
        # ...代理配置
    }
}
```

### 2. 使用强密码

密码应满足：
- 至少 16 位
- 包含大小写字母、数字、特殊字符
- 不使用字典词汇

生成强密码示例：

```bash
# Linux/Mac
openssl rand -base64 24

# Python
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

### 3. 限制 CORS

仅允许可信域名访问：

```bash
AIWRITEX_CORS_ORIGINS=https://your-trusted-domain.com,https://app.your-domain.com
```

### 4. 定期轮换凭证

建议每 90 天轮换一次 API Key 和密码。

### 5. 最小权限原则

- 使用专用的 LLM API Key，避免使用主账户密钥
- 为不同环境（开发、测试、生产）使用不同的凭证

### 6. 日志审计

定期检查认证失败日志：

```bash
docker logs aiwritex-server | grep "401\|Unauthorized"
```

---

## 认证失败响应

### 401 Unauthorized

```json
{
  "detail": "Invalid authentication credentials"
}
```

### 403 Forbidden

```json
{
  "detail": "Access denied"
}
```

---

## 禁用认证（仅限开发）

⚠️ **警告**：生产环境禁用认证存在严重安全风险。

```bash
# 环境变量
AIWRITEX_AUTH_ENABLED=false

# 或 config.yaml
auth:
  enabled: false
```

---

## 故障排查

### 浏览器不弹登录框

1. 确认 `AIWRITEX_AUTH_ENABLED=true`
2. 检查浏览器是否已缓存凭证（退出登录后重试）
3. 使用开发者工具查看响应头是否包含 `WWW-Authenticate`

### API Key 验证失败

1. 确认请求头为 `X-API-Key`（而非 `Authorization`）
2. 检查 API Key 是否正确（无多余空格）
3. 使用 curl 测试：`curl -v -H "X-API-Key: your_key" http://localhost:8888/health`

### CORS 错误

1. 检查 `AIWRITEX_CORS_ORIGINS` 配置
2. 确认请求的 Origin 在允许列表中
3. 查看浏览器控制台的具体错误信息
