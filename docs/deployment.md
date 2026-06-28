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

# 可选：持久化数据根目录（默认 ./data，所有配置/文章/图片/日志/知识库落盘到此）
AIWRITEX_DATA_DIR=./data
```

### 3. 启动服务

使用 Docker Compose（推荐）：

```bash
docker compose up -d --build
```

或使用纯 Docker（bind mount 到宿主机 `./data`，与 compose 行为一致）：

```bash
docker build -t aiwritex:latest .
mkdir -p data/config data/output data/image data/logs data/temp data/knowledge_storage data/knowledge_texts
docker run -d \
  --name aiwritex-server \
  -p 8888:8888 \
  -e AIWRITEX_CONFIG_DIR=/app/runtime_config \
  -v "$PWD/data/config:/app/runtime_config" \
  -v "$PWD/data/output:/app/output" \
  -v "$PWD/data/image:/app/image" \
  -v "$PWD/data/logs:/app/logs" \
  -v "$PWD/data/temp:/app/temp" \
  -v "$PWD/data/knowledge_storage:/app/knowledge_storage" \
  -v "$PWD/data/knowledge_texts:/app/knowledge/texts" \
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

## 数据持久化

所有需要持久化的内容（配置、生成的文章、图片、日志、知识库等）通过 **bind mount** 挂载到宿主机，根目录由 `.env` 的 `AIWRITEX_DATA_DIR` 配置（默认 `./data`）。容器重启 / 重建 / `down -v` 后数据均不丢失，且在宿主机可直接查看、编辑、备份。

| 宿主机路径 | 容器路径 | 内容 |
|---|---|---|
| `data/config` | `/app/runtime_config` | config.yaml、aiforge.toml、定时任务、UI 配置等（由 `AIWRITEX_CONFIG_DIR` 指定） |
| `data/output` | `/app/output` | 生成的文章、发布记录、设计数据 |
| `data/image` | `/app/image` | 图片资源 |
| `data/logs` | `/app/logs` | 应用日志 |
| `data/temp` | `/app/temp` | 临时文件 |
| `data/knowledge_storage` | `/app/knowledge_storage` | ChromaDB 向量库 + CrewAI 存储 |
| `data/knowledge_texts` | `/app/knowledge/texts` | 文本知识库索引 / 入库文本 |

> 注意：仅挂载 `knowledge/texts` 子目录，**默认文章模板** `knowledge/templates` 保留在镜像内（随镜像发布），不会被宿主目录遮蔽。
>
> 注意：配置数据挂载到独立的 `/app/runtime_config`（由环境变量 `AIWRITEX_CONFIG_DIR` 指定），**而非** Python 包目录 `src/ai_write_x/config`（那里存放 `config.py` 源码，若被 bind mount 遮蔽会导致 import 失败）。

生产环境建议把 `AIWRITEX_DATA_DIR` 指向独立数据盘的绝对路径（如 `/srv/aiwritex/data`），便于扩容与备份。

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

或直接编辑宿主机上的配置文件（bind mount，无需进容器）：

```bash
# 编辑宿主机 data/config/config.yaml
vi ./data/config/config.yaml

# 改完后重启容器使配置生效
docker compose restart aiwritex
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

日志文件位于宿主机 `data/logs/`（bind mount）：

```bash
# 宿主机直接查看
ls -la data/logs/
cat data/logs/WEB_$(date +%Y-%m-%d).log

# 或进容器
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

所有持久化数据都在宿主机 `./data`（或 `AIWRITEX_DATA_DIR` 指定的目录）下，直接整目录备份即可：

```bash
# 停服后备份（推荐，避免写入中文件不一致）
docker compose down
tar czf aiwritex-data-backup-$(date +%F).tar.gz data/

# 恢复：解压回原位再启动
tar xzf aiwritex-data-backup-YYYY-MM-DD.tar.gz
docker compose up -d
```

> 从旧版（命名卷）升级到 bind mount 后，旧命名卷内的数据不会自动迁移。如需迁移，参考 PR 说明中的迁移命令。

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
