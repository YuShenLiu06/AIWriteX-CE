# 微信文章模板提取器

将微信公众平台文章 URL 转换为自包含的 HTML 模板，保留文章原始 CSS 样式，去除外部 JS/CSS 依赖，下载图片到本地。

## 核心功能

- **体积压缩**：原始微信页面 ~6.5MB → 精简模板 ~15-20KB
- **保留样式**：提取文章内联 CSS 样式，压缩为 CSS class
- **本地图片**：自动下载远程图片到 `image/` 目录
- **纯净输出**：移除微信组件、广告、冗余 DOM 节点

## 使用方式

### 1. Python 脚本（直接调用）

```bash
# 转换微信文章到指定目录
python wechat_to_template.py "https://mp.weixin.qq.com/s/xxx" -o knowledge/templates/情感心理/

# 从本地 HTML 文件转换
python wechat_to_template.py "本地文件.html" -o ./output -l

# 显示详细日志
python wechat_to_template.py "URL" -o ./output -v

# 自定义超时和重试
python wechat_to_template.py "URL" -o ./output --timeout 60 --retries 5
```

### 2. REST API（服务器模式）

```bash
# 启动服务器（Docker 或本地）
python main.py

# 转换微信文章 URL 为模板
curl -u admin:password -X POST http://localhost:8888/api/convert/wechat \
  -H "Content-Type: application/json" \
  -d '{
    "url": "https://mp.weixin.qq.com/s/xxx",
    "output_type": "template",
    "category": "科技",
    "name": "my_article"
  }'

# 转换本地 HTML 为文章
curl -u admin:password -X POST http://localhost:8888/api/convert/wechat \
  -H "Content-Type: application/json" \
  -d '{
    "html": "<html>...</html>",
    "output_type": "article",
    "name": "converted_article"
  }'

# 查询转换状态
curl -u admin:password http://localhost:8888/api/convert/status
```

**API 响应示例：**

```json
// 启动转换
{
  "task_id": "abc123def456",
  "status": "started",
  "output_type": "template",
  "output_dir": "/app/knowledge/templates/科技"
}

// 转换中
{
  "status": "running",
  "task_id": "abc123def456"
}

// 转换完成
{
  "status": "completed",
  "task_id": "abc123def456",
  "html_path": "/app/knowledge/templates/科技/my_article.html",
  "image_count": 3
}

// 转换失败
{
  "status": "failed",
  "task_id": "abc123def456",
  "error": "请求超时"
}
```

### 3. CLI（命令行工具）

```bash
# 安装 CLI
cd client && pip install -e .

# 配置认证
export AIWRITEX_API_KEY="your_api_key"
export AIWRITEX_SERVER_URL="http://localhost:8888"

# 转换微信文章为模板
aiwritex convert wechat \
  --url "https://mp.weixin.qq.com/s/xxx" \
  --output-type template \
  --category 科技 \
  --name "my_article"

# 转换本地 HTML 为文章
aiwritex convert wechat \
  --html article.html \
  --output-type article \
  --name "my_article"

# 查询转换状态
aiwritex convert status
```

## 参数说明

| 参数 | 说明 | 默认值 |
|------|------|--------|
| `url` | 微信文章 URL 或本地 HTML 文件路径 | 必填 |
| `-o, --output` | 输出目录 | `./output` |
| `-l, --local` | 将 url 视为本地 HTML 文件路径 | False |
| `--timeout` | 请求超时秒数 | 30 |
| `--retries` | 最大重试次数 | 3 |
| `-v, --verbose` | 显示详细日志 | False |

## 输出结构

```
output/
├── 多少妈妈不知道的真相：把自己过好，孩子自然就学会了.html
└── image/
    ├── 1.jpg
    ├── 2.jpg
    ├── 3.jpg
    └── 4.jpg
```

## 技术实现

```
WeChat URL
    │
    ▼
┌────────────────────────────────────────┐
│  1. fetch_and_parse()                 │
│     - requests 获取原始 HTML           │
│     - BeautifulSoup 解析               │
│     - 提取 #js_content 内容区           │
│     - 移除 script/style/link 标签      │
└────────────────────────────────────────┘
    │
    ▼
┌────────────────────────────────────────┐
│  2. clean_wechat_content()             │
│     - 移除 mp-common-product 等组件    │
│     - 处理图片：data-src → data-origin │
│     - unwrap 纯布局 section            │
│     - 精简 inline style                │
└────────────────────────────────────────┘
    │
    ▼
┌────────────────────────────────────────┐
│  3. compress_inline_styles()           │
│     - 收集所有 unique inline style     │
│     - 转为 CSS class (.w0, .w1...)     │
│     - 替换 inline style 为 class       │
└────────────────────────────────────────┘
    │
    ▼
┌────────────────────────────────────────┐
│  4. download_images()                  │
│     - 遍历 img[data-origin]            │
│     - 下载到本地 image/ 目录            │
│     - 替换 src 为本地相对路径           │
└────────────────────────────────────────┘
    │
    ▼
    完整 HTML 模板
```

## 清洗规则

| 规则 | 说明 |
|------|------|
| 移除组件 | `mp-common-product`, `mp-common-product-iframe-wrp`, `template`, `button`, `dialog` |
| 移除广告 | 含 `product` 或 `ad` class 的 section |
| 移除图标 | `mmbiz.qpic.cn` 且无 `wx_fmt=` 的小图标 |
| 精简样式 | 移除 `visibility:visible`, `display:flex`, `box-sizing:border-box` 等默认值 |
| 压缩样式 | 重复 inline style 转为 CSS class |

## 相关文件

| 文件 | 说明 |
|------|------|
| `wechat_to_template.py` | CLI 命令行入口 |
| `src/ai_write_x/utils/article_template_converter.py` | 核心转换器类 |
| `src/ai_write_x/web/api/convert.py` | REST API 端点 |
| `client/aiwritex_cli/commands/convert.py` | CLI 命令实现 |

## API 字段说明

### POST /api/convert/wechat 请求字段

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `url` | string | 否* | 微信文章 URL |
| `html` | string | 否* | HTML 字符串 |
| `output_type` | string | 是 | 输出类型: `template`（模板）或 `article`（文章） |
| `category` | string | 条件 | 模板分类（output_type=template 时必填） |
| `name` | string | 否 | 输出文件名（不含扩展名） |
| `timeout` | number | 否 | 请求超时秒数（默认 30） |
| `retries` | number | 否 | 最大重试次数（默认 3） |

*注：`url` 和 `html` 至少提供一个

### GET /api/convert/status 响应字段

| 字段 | 说明 |
|------|------|
| `status` | 状态: `idle`, `running`, `completed`, `failed` |
| `task_id` | 任务 ID |
| `html_path` | 输出文件路径（仅 completed 时） |
| `image_count` | 迁移的图片数量（仅 completed 时） |
| `error` | 错误信息（仅 failed 时） |
