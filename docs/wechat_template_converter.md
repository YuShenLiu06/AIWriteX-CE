# 微信文章模板提取器

将微信公众平台文章 URL 转换为自包含的 HTML 模板，保留文章原始 CSS 样式，去除外部 JS/CSS 依赖，下载图片到本地。

## 核心功能

- **体积压缩**：原始微信页面 ~6.5MB → 精简模板 ~15-20KB
- **保留样式**：提取文章内联 CSS 样式，压缩为 CSS class
- **本地图片**：自动下载远程图片到 `image/` 目录
- **纯净输出**：移除微信组件、广告、冗余 DOM 节点

## 使用方式

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
