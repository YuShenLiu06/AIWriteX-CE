# AIWriteX 图片管理 API 说明

> 对应当前暂存中的 `src/ai_write_x/web/api/images.py`

---

## 1. 概述

图片管理 API 为本地图片资源库提供统一的 Web 接口，服务于以下场景：

- 图片导入与管理
- 图片描述、标签、分类维护
- 图片文件预览或读取
- 知识库刷新
- 为后续前端图片管理页提供基础数据接口

基础路由前缀：

```text
/api/images
```

---

## 2. 数据模型

### 2.1 图片响应字段

| 字段 | 类型 | 说明 |
|------|------|------|
| `id` | string | 图片唯一 ID |
| `original_filename` | string | 原始文件名 |
| `stored_path` | string | 本地存储路径 |
| `description` | string | 图片描述 |
| `tags` | string[] | 标签列表 |
| `category` | string/null | 图片分类 |
| `usage_count` | number | 使用次数 |
| `created_at` | string | 创建时间 |
| `file_size` | number | 文件大小（部分接口返回） |
| `mime_type` | string | MIME 类型（部分接口返回） |

### 2.2 更新请求模型

```json
{
  "description": "适合健康养生文章的暖色调茶饮图",
  "tags": ["养生", "茶饮", "暖色调"],
  "category": "健康养生"
}
```

---

## 3. 接口清单

### 3.1 上传图片

**接口**

```http
POST /api/images/
Content-Type: multipart/form-data
```

**表单字段**

| 字段 | 必填 | 说明 |
|------|------|------|
| `file` | 是 | 图片文件 |
| `description` | 否 | 图片描述 |
| `tags` | 否 | 逗号分隔标签 |
| `category` | 否 | 图片分类 |

**说明**

上传成功后会：

1. 将文件保存到临时路径
2. 写入图片仓库
3. 删除临时文件
4. 尝试刷新知识库

**成功响应示例**

```json
{
  "status": "success",
  "data": {
    "id": "uuid",
    "original_filename": "tea.jpg",
    "stored_path": "...",
    "description": "健康养生茶饮图",
    "tags": ["养生", "茶饮"],
    "category": "健康养生",
    "usage_count": 0
  }
}
```

---

### 3.2 获取图片列表

**接口**

```http
GET /api/images?category=健康养生&search=茶饮&limit=50
```

**查询参数**

| 参数 | 必填 | 说明 |
|------|------|------|
| `category` | 否 | 分类过滤 |
| `search` | 否 | 搜索词，按描述/标签匹配 |
| `limit` | 否 | 返回数量上限，默认 50 |

**说明**

- 有 `search` 时走搜索逻辑
- 无 `search` 时走全量列表逻辑
- 返回结果会统一包装在 `data` 数组中

---

### 3.3 获取单张图片信息

**接口**

```http
GET /api/images/{image_id}
```

**用途**

用于查看某张图片的完整元信息，包括：

- 描述
- 标签
- 分类
- 大小
- MIME 类型
- 创建时间

当图片不存在时返回 `404`。

---

### 3.4 获取图片文件

**接口**

```http
GET /api/images/{image_id}/file
```

**说明**

直接返回图片文件内容，适合：

- 前端预览
- 下载原图
- 图片详情页展示

当图片或实际文件不存在时返回 `404`。

---

### 3.5 更新图片信息

**接口**

```http
PATCH /api/images/{image_id}
Content-Type: application/json
```

**可更新字段**

- `description`
- `tags`
- `category`

**行为说明**

- 若没有任何更新字段，返回 `400`
- 若图片不存在，返回 `404`
- 更新成功后会尝试刷新知识库

**成功响应示例**

```json
{
  "status": "success"
}
```

---

### 3.6 删除图片

**接口**

```http
DELETE /api/images/{image_id}
```

**行为说明**

- 删除图片索引
- 删除本地实际文件
- 删除成功后尝试刷新知识库

若图片不存在，返回 `404`。

---

### 3.7 手动刷新知识库

**接口**

```http
POST /api/images/refresh-knowledge
```

**用途**

用于以下场景：

- 批量导入后统一刷新
- 需要手动重建向量索引
- 前端配置页点击“刷新知识库”按钮时调用

**成功响应示例**

```json
{
  "status": "success"
}
```

---

## 4. 与知识库的关系

图片管理 API 本身不是向量检索接口，但它负责维护向量检索所需的底层数据。

关系如下：

```text
图片上传/更新/删除
  -> ImageRepository 更新索引
  -> KnowledgeManager refresh
  -> 图片描述重新进入知识库
  -> UnifiedContentWorkflow 可检索并插图
```

因此，这组 API 是知识库链路中的“数据维护入口”。

---

## 5. 当前接口特点

### 优点

- 接口职责清晰，贴合资源管理场景
- 上传、更新、删除后自动尝试刷新知识库
- 与图片仓库和知识库实现解耦
- 便于前端快速接入

### 当前不足

- 暂无分页字段与统一元信息返回
- 暂无文件类型、大小、内容合法性校验细则
- 暂无鉴权与访问控制
- 批量操作接口尚未提供
- 错误返回主要依赖 `detail` 文本

---

## 6. 前端接入建议

推荐的前端调用顺序：

### 图片列表页

1. 首次进入调用 `GET /api/images`
2. 搜索时附加 `search`
3. 分类筛选时附加 `category`

### 图片编辑弹窗

1. 调用 `GET /api/images/{image_id}` 获取详情
2. 保存时调用 `PATCH /api/images/{image_id}`

### 图片上传流程

1. 提交 `POST /api/images/`
2. 成功后重新拉取列表
3. 如需批量导入，可最后统一调用 `POST /api/images/refresh-knowledge`

---

## 7. 后续建议

1. 增加分页：`page`、`page_size`、`total`
2. 增加批量上传/批量删除/批量打标
3. 增加服务端文件校验与大小限制
4. 为返回结构增加统一 `message` 和 `meta`
5. 若后续开放远程访问，应补充鉴权与访问控制

---

## 8. 相关文件

- `src/ai_write_x/web/api/images.py`
- `src/ai_write_x/core/image_repository.py`
- `src/ai_write_x/core/knowledge_manager.py`
- `src/ai_write_x/core/unified_workflow.py`
- `src/ai_write_x/web/static/js/config-manager.js`
