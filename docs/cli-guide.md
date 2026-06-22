# AIWriteX CLI 使用指南

AIWriteX 命令行工具（CLI）提供与服务器交互的便捷方式。

---

## 安装

### 从源码安装

```bash
cd client
pip install -e .
```

### 验证安装

```bash
aiwritex --help
```

---

## 配置

CLI 从环境变量读取服务器配置：

```bash
# 服务器地址
export AIWRITEX_SERVER_URL="http://localhost:8888"

# 认证信息（二选一）
export AIWRITEX_API_KEY="your_api_key"
# 或 Basic Auth
export AIWRITEX_AUTH_USER="admin"
export AIWRITEX_AUTH_PASSWORD="your_password"
```

或使用 `.env` 文件：

```bash
# 在项目根目录创建 .env
AIWRITEX_SERVER_URL=http://localhost:8888
AIWRITEX_API_KEY=your_api_key
```

---

## 命令速查

| 命令 | 描述 |
|------|------|
| `aiwritex config` | 配置管理 |
| `aiwritex template` | 模板管理 |
| `aiwritex article` | 文章管理 |
| `aiwritex generate` | 内容生成 |
| `aiwritex knowledge` | 知识库管理 |
| `aiwritex task` | 定时任务 |
| `aiwritex convert` | 文章转换 |

---

## 命令详解

### config - 配置管理

```bash
# 获取当前配置
aiwritex config get

# 获取默认配置
aiwritex config default

# 更新配置（从 JSON 文件）
aiwritex config update config.json

# 保存内存配置到文件
aiwritex config save

# 获取模板分类
aiwritex config categories

# 获取支持的平台
aiwritex config platforms
```

### template - 模板管理

```bash
# 列出所有模板
aiwritex template list

# 列出指定分类的模板
aiwritex template list --category 科技

# 获取模板内容
aiwritex template get /path/to/template.html

# 创建新模板
aiwritex template create my_template --category 科技 --content template.html

# 复制模板
aiwritex template copy /source/template.html --target-category 科技 --new-name new_template

# 删除模板
aiwritex template delete /path/to/template.html
```

### article - 文章管理

```bash
# 列出所有文章
aiwritex article list

# 获取文章内容
aiwritex article get /path/to/article.html

# 更新文章内容
aiwritex article update /path/to/article.html --content new_content.html

# 删除文章
aiwritex article delete /path/to/article.html

# 发布文章
aiwritex article publish /path/to/article1.html /path/to/article2.html --accounts 0 --platform wechat

# 获取发布历史
aiwritex article history /path/to/article.html

# 获取支持的平台
aiwritex article platforms
```

### generate - 内容生成

```bash
# 生成内容（热搜模式）
aiwritex generate run --topic "人工智能的未来"

# 生成内容（借鉴模式）
aiwritex generate run \
  --topic "AI发展" \
  --template-category 科技 \
  --template-name tech_template \
  --reference-urls "https://example.com/article1|https://example.com/article2" \
  --reference-ratio 30

# 停止生成
aiwritex generate stop

# 查看状态
aiwritex generate status

# 获取热搜话题
aiwritex generate hot-topic

# 验证配置
aiwritex generate validate
```

### knowledge - 知识库管理

#### 文本知识

```bash
# 列出文本知识
aiwritex knowledge text list

# 搜索文本知识
aiwritex knowledge text list --search "AI"

# 获取单个文本知识
aiwritex knowledge text get <item_id>

# 添加文本知识
aiwritex knowledge text add \
  --title "AI 基础" \
  --content "人工智能是..." \
  --summary "简介" \
  --tags "AI,技术" \
  --category "科技"

# 更新文本知识
aiwritex knowledge text update <item_id> --description "新描述"

# 删除文本知识
aiwritex knowledge text delete <item_id>

# 获取分类列表
aiwritex knowledge text categories

# 刷新知识库
aiwritex knowledge text refresh
```

#### 图片知识

```bash
# 列出图片
aiwritex knowledge image list

# 搜索图片
aiwritex knowledge image list --search "科技"

# 上传图片
aiwritex knowledge image upload image.jpg \
  --description "AI 芯片" \
  --tags "AI,硬件" \
  --category "科技"

# 获取图片信息
aiwritex knowledge image get <image_id>

# 下载图片
aiwritex knowledge image download <image_id> --output ./download.jpg

# 更新图片信息
aiwritex knowledge image update <image_id> --description "新描述"

# 删除图片
aiwritex knowledge image delete <image_id>

# 刷新图片知识库
aiwritex knowledge image refresh
```

#### 统一知识库

```bash
# 获取统计信息
aiwritex knowledge stats

# 刷新全部知识库
aiwritex knowledge refresh
```

### task - 定时任务

```bash
# 列出所有任务
aiwritex task list

# 创建任务（固定时间）
aiwritex task create \
  --name "每日科技文章" \
  --topic "最新 AI 进展" \
  --schedule-type fixed_time \
  --time-of-day "09:00" \
  --enabled

# 创建任务（Cron 表达式）
aiwritex task create \
  --name "每周一任务" \
  --topic "周报" \
  --schedule-type cron \
  --cron-expression "0 9 * * 1" \
  --enabled

# 获取任务详情
aiwritex task get <task_id>

# 更新任务
aiwritex task update <task_id> --topic "新话题"

# 启用/停用任务
aiwritex task toggle <task_id> --enabled
aiwritex task toggle <task_id> --disabled

# 删除任务
aiwritex task delete <task_id>

# 立即执行任务
aiwritex task run <task_id>

# 获取执行记录
aiwritex task records <task_id>

# 获取运行时状态
aiwritex task runtime
```

### convert - 文章转换

```bash
# 转换微信文章（URL）为模板
aiwritex convert wechat \
  --url "https://mp.weixin.qq.com/s/xxx" \
  --output-type template \
  --category 科技 \
  --name "converted_article"

# 转换本地 HTML 为文章
aiwritex convert wechat \
  --html article.html \
  --output-type article \
  --name "my_article"

# 获取转换状态
aiwritex convert status
```

---

## 工作流示例

### 创建模板并生成文章

```bash
# 1. 创建模板
aiwritex template create tech_template --category 科技 --content template.html

# 2. 生成文章
aiwritex generate run \
  --topic "量子计算最新进展" \
  --template-category 科技 \
  --template-name tech_template

# 3. 轮询状态
aiwritex generate status

# 4. 查看生成的文章
aiwritex article list
```

### 设置定时任务

```bash
# 1. 创建定时任务
aiwritex task create \
  --name "每日科技新闻" \
  --topic "科技新闻汇总" \
  --schedule-type fixed_time \
  --time-of-day "08:00" \
  --auto-publish \
  --enabled

# 2. 查看任务状态
aiwritex task runtime

# 3. 查看执行记录
aiwritex task records <task_id>
```

---

## 错误排查

### 401 Unauthorized

认证失败，检查环境变量：

```bash
echo $AIWRITEX_API_KEY
# 或
echo $AIWRITEX_AUTH_USER
echo $AIWRITEX_AUTH_PASSWORD
```

### ConnectionError

服务器连接失败，检查：

```bash
echo $AIWRITEX_SERVER_URL
curl http://localhost:8888/health
```

### 任务执行失败

查看日志：

```bash
aiwritex generate status
```

### 转换任务卡住

检查转换状态：

```bash
aiwritex convert status
```
