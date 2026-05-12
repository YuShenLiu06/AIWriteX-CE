# AIWriteX 知识库管理说明

> 面向当前暂存中的“知识库 + 图片资源库 + 向量嵌入配置”改动

---

## 1. 功能目标

本次知识库能力的目标，不是单独做一个脱离工作流的向量模块，而是把“图片资源沉淀、描述向量化、语义检索、文章插图”串成一条可复用链路。

核心价值：

- 把本地图片变成可管理资源
- 把图片描述变成可检索知识
- 把知识检索结果复用到文章生成流程
- 把向量嵌入参数暴露到前端配置管理页面

---

## 2. 当前组成

### 2.1 配置层

涉及文件：
- `src/ai_write_x/config/config.py`
- `src/ai_write_x/config/config.yaml`

新增配置结构：

```yaml
knowledge:
  enabled: true
  embedder:
    provider: openai
    api_key: ""
    model: text-embedding-3-small
    base_url: ""
```

字段说明：

| 字段 | 说明 |
|------|------|
| `knowledge.enabled` | 是否启用知识库检索能力 |
| `provider` | 嵌入服务提供商，如 `openai` / `voyageai` / `ollama` |
| `api_key` | 嵌入服务密钥 |
| `model` | 向量嵌入模型名 |
| `base_url` | 自定义 API 地址或本地地址 |

---

### 2.2 图片资源层

涉及文件：
- `src/ai_write_x/core/image_repository.py`

`ImageRepository` 负责图片资源的本地持久化管理，主要能力包括：

- 存储图片文件到资源目录
- 用 JSON 维护图片索引
- 管理图片描述、标签、分类、MIME、使用次数
- 提供简单关键词搜索
- 支持更新与删除

资源数据结构：

```python
ImageResource
- id
- original_filename
- stored_path
- description
- tags
- category
- file_size
- mime_type
- metadata
- usage_count
- created_at
```

这层更像“图片资产仓库”，负责把文件和元信息稳定存下来。

---

### 2.3 知识库层

涉及文件：
- `src/ai_write_x/core/knowledge_manager.py`

`KnowledgeManager` 负责把图片描述转为向量知识源，当前实现特点：

- 读取 `knowledge.embedder` 配置
- 将图片描述、标签、分类拼装成知识文本
- 基于 CrewAI Knowledge 创建向量知识集合
- 使用 `CREWAI_STORAGE_DIR` 指向项目数据目录
- 提供 `search_images()` 做语义召回
- 提供 `refresh()` 重建知识库

当前知识源示意：

```text
图片描述: xxx | 标签: a,b,c | 分类: 健康养生
```

也就是说，目前的知识库核心不是“原图视觉向量”，而是“图片语义描述向量化”。

---

### 2.4 工作流接入层

涉及文件：
- `src/ai_write_x/core/system_init.py`
- `src/ai_write_x/core/unified_workflow.py`

当前工作流接入逻辑：

1. 启动时注册 `ImageSearchTool`
2. 执行文章生成前，根据话题搜索相关图片
3. 生成正文后，把命中的图片插入内容中
4. 再进入原有模板/设计转换流程

简化流程如下：

```text
话题输入
  -> 检索相关图片
  -> 生成基础内容
  -> 创意变换
  -> 插入图片
  -> 模板/设计转换
  -> 保存/发布
```

这样做的好处是：图片知识能力复用原有主工作流，而不是额外分叉出一条独立流程。

---

## 3. 前端配置入口

涉及文件：
- `src/ai_write_x/web/static/js/config-manager.js`
- `src/ai_write_x/web/templates/components/views/config-manager/config-manager.html`
- `src/ai_write_x/web/templates/components/views/config-manager/panels/knowledge-embedder-config.html`

已增加“向量嵌入设置”配置面板，当前支持：

- 启用/关闭知识库
- 切换嵌入服务提供商
- 配置模型名
- 配置 API Key
- 配置 Base URL
- 手动刷新知识库
- 显示图片数与知识条目数
- 打开图片管理入口

其中：

- `ollama` 场景通常更依赖 `base_url`
- 云端 provider 更依赖 `api_key`

---

## 4. 与图片管理 API 的关系

涉及文件：
- `src/ai_write_x/web/api/images.py`

图片上传、更新、删除后，都会尝试刷新知识库，因此形成了下面的闭环：

```text
上传/修改图片
  -> 更新图片仓库
  -> 刷新知识库
  -> 新描述可被语义检索
  -> 工作流可复用该图片
```

这使得“资源维护”和“生成复用”不再割裂。

---

## 5. 当前限制

### 5.1 主要面向图片描述

当前知识库实际落地的是图片描述知识，而不是通用业务文档知识库。虽然类中预留了 `business_knowledge`，但本次暂存还未真正接入业务文本资料。

### 5.2 刷新策略较重

`KnowledgeManager.refresh()` 的本质是重建知识库。对于单次上传/删除问题不大，但批量导入时会有额外成本。

### 5.3 插图策略偏简单

现在的插图逻辑是把结果插入到首个段落或 section 后，属于“先可用”的实现，后续可以继续细化为：

- 按段落主题分配图片
- 按分类限制候选图片
- 按相似度阈值决定是否插图

---

## 6. 使用建议

### 6.1 配置建议

- 默认快速接入：`openai + text-embedding-3-small`
- Claude 生态偏好：可尝试 `voyageai`
- 本地离线部署：`ollama + base_url`

### 6.2 资源维护建议

为了提高召回质量，建议为每张图片填写：

- 清晰的中文描述
- 2~5 个稳定标签
- 明确分类

例如：

- 描述：`中式养生茶饮，木质桌面，暖色调，适合健康类公众号配图`
- 标签：`养生, 茶饮, 暖色调, 公众号`
- 分类：`健康养生`

### 6.3 提交建议

提交前应检查：

- `config.yaml` 是否包含真实密钥
- 知识库存储产物是否应纳入版本控制
- 端口调整是否与桌面端启动逻辑一致

---

## 7. 后续扩展方向

1. 增加文本资料型知识库
2. 支持批量导入并延迟统一刷新
3. 增加更细的检索排序与召回策略
4. 为知识库增加状态页与重建进度提示
5. 打通“图片管理页 -> 配置页 -> 生成页”的完整前端链路

---

## 8. 相关文件清单

### 后端核心
- `src/ai_write_x/core/image_repository.py`
- `src/ai_write_x/core/knowledge_manager.py`
- `src/ai_write_x/core/unified_workflow.py`
- `src/ai_write_x/core/system_init.py`

### 配置
- `src/ai_write_x/config/config.py`
- `src/ai_write_x/config/config.yaml`

### Web/API
- `src/ai_write_x/web/api/images.py`
- `src/ai_write_x/web/static/js/config-manager.js`
- `src/ai_write_x/web/templates/components/views/config-manager/config-manager.html`
- `src/ai_write_x/web/templates/components/views/config-manager/panels/knowledge-embedder-config.html`
