# AIWriteX API 参考文档

本文档提供 AIWriteX REST API 的完整参考。

## 认证方式

AIWriteX 支持两种认证方式：

### 1. Basic Auth（基础认证）

使用用户名和密码进行 HTTP 基础认证：

```bash
curl -u admin:your_password http://localhost:8888/api/config
```

### 2. API Key（密钥认证）

使用请求头进行 API 密钥认证：

```bash
curl -H "X-API-Key: your_api_key" http://localhost:8888/api/config
```

---

## 端点列表

### 系统端点

| 端点 | 方法 | 描述 | 认证 |
|------|------|------|------|
| `/health` | GET | 健康检查 | 否 |
| `/` | GET | 主页面（Web UI） | 否 |
| `/shutdown` | POST | 关闭服务器 | 否 |

#### GET /health

健康检查端点，用于服务监控。

**响应示例：**

```json
{
  "status": "healthy",
  "timestamp": 1715423200.123
}
```

---

### 配置管理 (`/api/config`)

| 端点 | 方法 | 描述 |
|------|------|------|
| `/api/config` | GET | 获取当前配置 |
| `/api/config` | PATCH | 更新内存配置 |
| `/api/config` | POST | 保存配置到文件 |
| `/api/config/default` | GET | 获取默认配置 |
| `/api/config/ui-config` | GET | 获取 UI 配置 |
| `/api/config/ui-config` | POST | 保存 UI 配置 |
| `/api/config/template-categories` | GET | 获取模板分类 |
| `/api/config/templates/{category}` | GET | 获取分类下的模板 |
| `/api/config/platforms` | GET | 获取支持的平台 |
| `/api/config/page-design` | GET | 获取页面设计配置 |
| `/api/config/help-manual` | GET | 获取使用手册 |
| `/api/config/check-updates` | GET | 检查更新 |
| `/api/config/open-url` | POST | 打开外部链接 |

#### GET /api/config

获取当前系统配置。

**请求示例：**

```bash
curl -u admin:password http://localhost:8888/api/config
```

**响应示例：**

```json
{
  "status": "success",
  "data": {
    "platforms": [...],
    "publish_platform": "wechat",
    "api": {...},
    "wechat": {...},
    "article_format": "html",
    "auto_publish": false
  }
}
```

---

### 文章管理 (`/api/articles`)

| 端点 | 方法 | 描述 |
|------|------|------|
| `/api/articles` | GET | 获取文章列表 |
| `/api/articles/content` | GET | 获取文章内容 |
| `/api/articles/content` | PUT | 更新文章内容 |
| `/api/articles/preview` | GET | 预览文章 |
| `/api/articles/{article_path:path}` | DELETE | 删除文章 |
| `/api/articles/publish` | POST | 发布文章 |
| `/api/articles/platforms` | GET | 获取支持的平台 |
| `/api/articles/publish-history/{article_path:path}` | GET | 获取发布历史 |
| `/api/articles/design` | POST | 保存文章设计 |
| `/api/articles/design` | GET | 加载文章设计 |
| `/api/articles/upload-image` | POST | 上传图片 |
| `/api/articles/images` | GET | 获取图片列表 |

#### GET /api/articles

获取文章列表。

**响应示例：**

```json
{
  "status": "success",
  "data": [
    {
      "name": "article_title",
      "path": "/app/output/article_title.html",
      "title": "Article Title",
      "format": "HTML",
      "size": "12.34 KB",
      "create_time": "2024-06-22 10:30:00",
      "status": "published"
    }
  ]
}
```

#### POST /api/articles/publish

发布文章到指定平台。

**请求体：**

```json
{
  "article_paths": ["/app/output/article1.html", "/app/output/article2.html"],
  "account_indices": [0],
  "platform": "wechat"
}
```

**响应示例：**

```json
{
  "status": "success",
  "success_count": 2,
  "fail_count": 0,
  "warning_details": [],
  "error_details": []
}
```

---

### 内容生成 (`/api/generate`)

| 端点 | 方法 | 描述 |
|------|------|------|
| `/api/config/validate` | GET | 验证配置 |
| `/api/generate` | POST | 生成内容 |
| `/api/generate/stop` | POST | 停止生成 |
| `/api/generate/status` | GET | 获取生成状态 |
| `/api/hot-topics` | GET | 获取热搜话题 |
| `/api/logs/latest` | GET | 获取最新日志 |
| `/ws/generate/logs` | WebSocket | 日志流 |

#### POST /api/generate

启动内容生成任务。

**请求体：**

```json
{
  "topic": "人工智能的未来发展",
  "platform": "wechat",
  "reference": {
    "template_category": "科技",
    "template_name": "tech_template",
    "reference_urls": "https://example.com/article1|https://example.com/article2",
    "reference_ratio": 30
  }
}
```

**响应示例：**

```json
{
  "status": "success",
  "message": "正在生成内容，请耐心等待...",
  "mode": "reference",
  "topic": "人工智能的未来发展"
}
```

#### GET /api/generate/status

获取当前生成任务状态。

**响应示例：**

```json
{
  "status": "running",
  "error": null
}
```

可能的状态值：`idle`, `running`, `completed`, `failed`, `stopped`

---

### 模板管理 (`/api/templates`)

| 端点 | 方法 | 描述 |
|------|------|------|
| `/api/templates/categories` | GET | 获取分类列表 |
| `/api/templates/categories` | POST | 创建分类 |
| `/api/templates/categories/{category_name}` | PUT | 重命名分类 |
| `/api/templates/categories/{category_name}` | DELETE | 删除分类 |
| `/api/templates/default-template-categories` | GET | 获取默认分类 |
| `/api/templates` | GET | 获取模板列表 |
| `/api/templates` | POST | 创建模板 |
| `/api/templates/content/{template_path:path}` | GET | 获取模板内容 |
| `/api/templates/content/{template_path:path}` | PUT | 更新模板内容 |
| `/api/templates/preview/{template_path:path}` | GET | 预览模板 |
| `/api/templates/{template_path:path}` | DELETE | 删除模板 |
| `/api/templates/rename` | POST | 重命名模板 |
| `/api/templates/copy` | POST | 复制模板 |
| `/api/templates/move` | PUT | 移动模板 |

#### GET /api/templates/categories

获取所有模板分类。

**响应示例：**

```json
{
  "status": "success",
  "data": [
    {
      "name": "科技",
      "path": "/app/knowledge/templates/科技",
      "template_count": 5
    }
  ]
}
```

#### POST /api/templates

创建新模板。

**请求体：**

```json
{
  "name": "my_template",
  "category": "科技",
  "content": "<html>...</html>"
}
```

---

### 知识库管理 (`/api/knowledge`, `/api/text-knowledge`, `/api/images`)

#### 统一知识库 (`/api/knowledge`)

| 端点 | 方法 | 描述 |
|------|------|------|
| `/api/knowledge/stats` | GET | 获取知识库统计 |
| `/api/knowledge/refresh` | POST | 刷新知识库 |

**GET /api/knowledge/stats 响应示例：**

```json
{
  "status": "success",
  "data": {
    "text_knowledge_count": 42,
    "image_count": 128
  }
}
```

#### 文本知识 (`/api/text-knowledge`)

| 端点 | 方法 | 描述 |
|------|------|------|
| `/api/text-knowledge` | GET | 获取文本知识列表 |
| `/api/text-knowledge` | POST | 创建文本知识 |
| `/api/text-knowledge/{item_id}` | GET | 获取单个文本知识 |
| `/api/text-knowledge/{item_id}` | PATCH | 更新文本知识 |
| `/api/text-knowledge/{item_id}` | DELETE | 删除文本知识 |
| `/api/text-knowledge/categories` | GET | 获取分类列表 |
| `/api/text-knowledge/refresh-knowledge` | POST | 刷新知识库 |

**POST /api/text-knowledge 请求体：**

```json
{
  "title": "知识标题",
  "content": "知识内容",
  "summary": "摘要",
  "tags": ["标签1", "标签2"],
  "category": "分类",
  "source_type": "manual"
}
```

#### 图片知识 (`/api/images`)

| 端点 | 方法 | 描述 |
|------|------|------|
| `/api/images` | GET | 获取图片列表 |
| `/api/images` | POST | 上传图片 |
| `/api/images/{image_id}` | GET | 获取图片信息 |
| `/api/images/{image_id}/file` | GET | 获取图片文件 |
| `/api/images/{image_id}` | PATCH | 更新图片信息 |
| `/api/images/{image_id}` | DELETE | 删除图片 |
| `/api/images/refresh-knowledge` | POST | 刷新知识库 |

**POST /api/images 请求（multipart/form-data）：**

- `file`: 图片文件（必填）
- `description`: 图片描述
- `tags`: 标签（逗号分隔）
- `category`: 分类

---

### 定时任务 (`/api/scheduled-tasks`)

| 端点 | 方法 | 描述 |
|------|------|------|
| `/api/scheduled-tasks` | GET | 获取任务列表 |
| `/api/scheduled-tasks` | POST | 创建任务 |
| `/api/scheduled-tasks/{task_id}` | GET | 获取任务详情 |
| `/api/scheduled-tasks/{task_id}` | PUT | 更新任务 |
| `/api/scheduled-tasks/{task_id}` | DELETE | 删除任务 |
| `/api/scheduled-tasks/{task_id}/toggle` | POST | 启用/停用任务 |
| `/api/scheduled-tasks/{task_id}/run-now` | POST | 立即执行任务 |
| `/api/scheduled-tasks/{task_id}/records` | GET | 获取执行记录 |
| `/api/scheduled-tasks/runtime/status` | GET | 获取运行时状态 |

#### POST /api/scheduled-tasks

创建定时任务。

**请求体：**

```json
{
  "name": "每日科技文章",
  "topic": "最新人工智能进展",
  "schedule_type": "fixed_time",
  "time_of_day": "09:00",
  "enabled": true,
  "auto_publish": false,
  "max_retries": 3
}
```

或使用 Cron 表达式：

```json
{
  "name": "每周一任务",
  "topic": "周报主题",
  "schedule_type": "cron",
  "cron_expression": "0 9 * * 1",
  "enabled": true
}
```

**响应示例：**

```json
{
  "status": "success",
  "message": "定时任务创建成功",
  "data": {
    "task": {
      "id": "task_abc123",
      "name": "每日科技文章",
      "topic": "最新人工智能进展",
      "schedule_type": "fixed_time",
      "time_of_day": "09:00",
      "enabled": true,
      "auto_publish": false,
      "max_retries": 3
    }
  }
}
```

---

### 微信文章转换 (`/api/convert`)

| 端点 | 方法 | 描述 |
|------|------|------|
| `/api/convert/wechat` | POST | 转换微信文章 |
| `/api/convert/status` | GET | 获取转换状态 |

#### POST /api/convert/wechat

将微信公众号文章或本地 HTML 转换为自包含模板。

**请求体：**

```json
{
  "url": "https://mp.weixin.qq.com/s/xxx",
  "html": null,
  "output_type": "template",
  "category": "科技",
  "name": "my_article",
  "timeout": 30,
  "retries": 3
}
```

或直接传入 HTML 字符串：

```json
{
  "url": null,
  "html": "<html>...</html>",
  "output_type": "article",
  "name": "converted_article"
}
```

**响应示例：**

```json
{
  "task_id": "abc123def456",
  "status": "started",
  "output_type": "template",
  "output_dir": "/app/knowledge/templates/科技"
}
```

#### GET /api/convert/status

获取当前转换状态。

**响应示例（进行中）：**

```json
{
  "status": "running",
  "task_id": "abc123def456"
}
```

**响应示例（完成）：**

```json
{
  "status": "completed",
  "task_id": "abc123def456",
  "html_path": "/app/knowledge/templates/科技/my_article.html",
  "image_count": 3
}
```

**响应示例（失败）：**

```json
{
  "status": "failed",
  "task_id": "abc123def456",
  "error": "请求超时"
}
```

---

## 错误响应

所有错误响应遵循统一格式：

```json
{
  "detail": "错误描述信息"
}
```

常见 HTTP 状态码：

| 状态码 | 描述 |
|--------|------|
| 200 | 成功 |
| 400 | 请求参数错误 |
| 401 | 未授权（认证失败） |
| 404 | 资源不存在 |
| 409 | 资源冲突（如任务正在运行） |
| 500 | 服务器内部错误 |

---

## WebSocket 连接

### `/ws/generate/logs`

实时日志流，用于监控生成任务进度。

**连接示例：**

```javascript
const ws = new WebSocket('ws://localhost:8888/ws/generate/logs');

ws.onmessage = (event) => {
  const data = JSON.parse(event.data);
  console.log(`[${data.type}] ${data.message}`);
};
```

**消息格式：**

```json
{
  "type": "info|warning|error|completed|failed",
  "message": "日志内容",
  "timestamp": 1715423200.123
}
```
