# AIWriteX 部署指南

本指南介绍如何使用 Docker 部署 AIWriteX 服务器。

---

## 前置要求

- Docker 20.10+
- Docker Compose 2.0+（可选，用于简化部署）
- 至少 2GB 可用内存
- 至少 5GB 可用磁盘空间

---

## 快速开始

### 1. 获取代码

```bash
git clone https://github.com/iniwap/AIWriteX.git
cd AIWriteX
```

### 2. 配置环境变量

复制示例环境文件并填入实际值：

```bash
cp .env.example .env
```

编辑 `.env` 文件，至少配置以下必需项：

```bash
# 必需：Basic Auth 密码
AIWRITEX_AUTH_PASSWORD=your_secure_password

# 必需：至少一个 LLM API 密钥
OPENROUTER_API_KEY=sk-or-...
# 或 DEEPSEEK_API_KEY=sk-...
```

### 3. 启动服务

使用 Docker Compose（推荐）：

```bash
docker compose up -d --build
```

或使用纯 Docker：

```bash
docker build -t aiwritex:latest .
docker run -d \
  --name aiwritex-server \
  -p 8888:8888 \
  -v aiwritex-config:/app/src/ai_write_x/config \
  -v aiwritex-output:/app/output \
  -e AIWRITEX_AUTH_PASSWORD=your_password \
  -e OPENROUTER_API_KEY=your_key \
  aiwritex:latest
```

### 4. 验证部署

检查服务健康状态：

```bash
curl http://localhost:8888/health
```

预期响应：

```json
{
  "status": "healthy",
  "timestamp": 1715423200.123
}
```

访问 Web UI：

```bash
# 浏览器访问
http://localhost:8888
```

使用 Basic Auth 登录（默认用户名：`admin`，密码：你设置的密码）。

---

## 配置 LLM 和微信

### 配置 LLM API

在容器内编辑配置文件：

```bash
# 进入容器
docker exec -it aiwritex-server bash

# 编辑配置（容器内路径）
vi /app/src/ai_write_x/config/config.yaml
```

或通过挂载 volume 后在外部编辑：

```bash
# 查看 volume 挂载位置
docker volume inspect aiwritex-config

# 编辑外部路径的 config.yaml
# ...
```

配置示例：

```yaml
api:
  api_type: "openrouter"
  api_key: "sk-or-..."
  model: "anthropic/claude-3.5-sonnet"
  api_base: "https://openrouter.ai/api/v1"
```

### 配置微信公众号

在同一 `config.yaml` 文件中添加：

```yaml
wechat:
  credentials:
    - appid: "your_appid"
      appsecret: "your_appsecret"
      author: "公众号名称"
```

---

## Nginx 反向代理

### 基础配置

```nginx
server {
    listen 80;
    server_name your-domain.com;

    # 基础代理
    location / {
        proxy_pass http://127.0.0.1:8888;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    # WebSocket 支持
    location /ws/ {
        proxy_pass http://127.0.0.1:8888;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_read_timeout 86400;
    }
}
```

### HTTPS 配置（推荐）

使用 Let's Encrypt 获取免费 SSL 证书：

```bash
# 安装 certbot
apt install certbot python3-certbot-nginx

# 获取证书
certbot --nginx -d your-domain.com
```

Nginx 会自动更新配置启用 HTTPS。

---

## 运维管理

### 查看日志

```bash
# Docker Compose
docker compose logs -f aiwritex

# 纯 Docker
docker logs -f aiwritex-server
```

### 查看应用日志

日志文件位于 volume 中：

```bash
docker exec aiwritex-server ls -la /app/logs/

# 查看当天日志
docker exec aiwritex-server cat /app/logs/WEB_$(date +%Y-%m-%d).log
```

### 重启服务

```bash
# Docker Compose
docker compose restart aiwritex

# 纯 Docker
docker restart aiwritex-server
```

### 停止服务

```bash
# Docker Compose
docker compose down

# 纯 Docker
docker stop aiwritex-server
```

### 备份数据

备份所有 volume：

```bash
# 备份配置
docker run --rm -v aiwritex-config:/data -v $(pwd):/backup alpine tar czf /backup/config-backup.tar.gz -C /data .

# 备份输出文件
docker run --rm -v aiwritex-output:/data -v $(pwd):/backup alpine tar czf /backup/output-backup.tar.gz -C /data .

# 备份图片
docker run --rm -v aiwritex-image:/data -v $(pwd):/backup alpine tar czf /backup/image-backup.tar.gz -C /data .
```

恢复数据：

```bash
# 恢复配置
docker run --rm -v aiwritex-config:/data -v $(pwd):/backup alpine tar xzf /backup/config-backup.tar.gz -C /data
```

---

## 升级

### 1. 拉取最新代码

```bash
git pull origin main
```

### 2. 重新构建并启动

```bash
docker compose up -d --build
```

### 3. 验证

```bash
curl http://localhost:8888/health
```

---

## 安装 CLI（可选）

如需使用命令行工具，安装客户端：

```bash
cd client
pip install -e .
```

验证安装：

```bash
aiwritex --help
```

---

## 故障排查

### 服务无法启动

1. 检查端口占用：

```bash
netstat -tlnp | grep 8888
```

2. 检查日志：

```bash
docker logs aiwritex-server
```

### 认证失败

1. 确认环境变量已设置：

```bash
docker exec aiwritex-server env | grep AUTH
```

2. 检查配置文件：

```bash
docker exec aiwritex-server cat /app/src/ai_write_x/config/config.yaml
```

### LLM 调用失败

1. 验证 API 密钥有效性
2. 检查网络连接（如有代理，需配置）

### 文章发布失败

1. 检查微信公众号配置
2. 查看日志中的具体错误信息

---

## 生产环境建议

1. **启用 HTTPS**：使用 Nginx + Let's Encrypt
2. **设置强密码**：使用随机生成的长密码
3. **限制 CORS**：仅允许可信域名
4. **定期备份**：设置自动备份任务
5. **监控健康**：使用 `/health` 端点配合监控系统
6. **资源限制**：在 docker-compose.yml 中设置内存/CPU 限制

### 资源限制示例

```yaml
services:
  aiwritex:
    # ...
    deploy:
      resources:
        limits:
          cpus: '2'
          memory: 4G
        reservations:
          cpus: '0.5'
          memory: 1G
```
