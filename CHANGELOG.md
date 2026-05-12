# AIWriteX 暂存更新日志

> 生成时间：2026-05-11
> 范围：当前已暂存变更

---

## 本次更新概览

本次暂存改动围绕“知识库 + 图片资源库 + 向量嵌入配置”展开，目标是让 AIWriteX 在原有写作工作流基础上，具备图片资源沉淀、语义检索、知识库刷新与嵌入模型配置能力。

---

## 主要更新内容

### 1. 新增知识库配置

涉及文件：
- `src/ai_write_x/config/config.py`
- `src/ai_write_x/config/config.yaml`

新增 `knowledge` 配置块，用于控制知识库开关与向量嵌入模型参数：

- `knowledge.enabled`：是否启用知识库能力
- `knowledge.embedder.provider`：嵌入服务提供商
- `knowledge.embedder.api_key`：嵌入服务密钥
- `knowledge.embedder.model`：嵌入模型名称
- `knowledge.embedder.base_url`：自定义服务地址或本地服务地址

该配置为后续图片检索、知识向量化、语义召回提供统一入口。

### 2. 新增图片资源仓库

涉及文件：
- `src/ai_write_x/core/image_repository.py`

新增 `ImageRepository`，用于管理本地图片资源：

- 图片导入与复制存储
- JSON 索引维护
- 描述、标签、分类、使用次数管理
- 基于描述/标签/分类的关键词搜索
- 删除与更新能力

图片元数据通过 `ImageResource` 数据结构统一描述，便于后续 API 与工作流复用。

### 3. 新增知识库管理器

涉及文件：
- `src/ai_write_x/core/knowledge_manager.py`

新增 `KnowledgeManager`，对 CrewAI Knowledge 做封装：

- 从配置读取 embedder 参数
- 将图片描述构造成向量化知识源
- 使用 ChromaDB 作为底层知识存储目录
- 提供图片语义检索
- 支持刷新知识库

当前设计重点是“图片描述知识化”，为文章生成时插入相关图片提供召回基础。

### 4. 工作流接入图片检索与插图能力

涉及文件：
- `src/ai_write_x/core/system_init.py`
- `src/ai_write_x/core/unified_workflow.py`
- `src/ai_write_x/crew_main.py`

本次改动已把图片检索能力接入主工作流：

- 注册 `ImageSearchTool`
- 在生成正文前检索与主题相关的图片
- 在内容转换前尝试将图片插入文章内容
- 修复 `crew_main.py` 中话题模式判断使用 `config.platforms` 的问题

效果上，文章生成流程从“纯文本生成”扩展为“文本 + 图片资源检索协同”。

### 5. 新增图片管理 REST API

涉及文件：
- `src/ai_write_x/web/api/images.py`
- `src/ai_write_x/web/app.py`

新增 `/api/images` 路由，支持：

- 上传图片
- 获取图片列表
- 获取单张图片信息
- 获取图片文件内容
- 更新图片描述/标签/分类
- 删除图片
- 手动刷新知识库

该 API 为前端图片管理与知识库维护提供基础接口。

### 6. 新增向量嵌入设置面板

涉及文件：
- `src/ai_write_x/web/static/js/config-manager.js`
- `src/ai_write_x/web/templates/components/views/config-manager/config-manager.html`
- `src/ai_write_x/web/templates/components/views/config-manager/panels/knowledge_emdedder_config.html`

已在配置管理页面中接入新的“向量嵌入设置”面板，支持：

- 启用/关闭知识库
- 选择嵌入服务提供商
- 填写 API Key / 模型 / Base URL
- 手动刷新知识库
- 查看知识库统计信息
- 跳转图片管理入口

说明：实际暂存文件名为 `knowledge-embedder-config.html`，上述能力已对应到该模板文件。

---

## 架构收益

本次改动带来的直接收益包括：

1. 为图片资源建立可维护的本地仓库
2. 为图片描述建立可检索的向量知识层
3. 让文章工作流能够复用历史图片资源
4. 让知识库配置进入统一可视化管理
5. 为后续扩展“业务知识库 / 文本知识库 / 多模态检索”预留接口

---

## 当前限制与后续可继续完善点

### 当前限制

- 当前知识库主要面向图片描述，`business_knowledge` 尚未真正落地使用
- 图片更新/删除后通过 `refresh()` 重建知识库，批量操作时性能一般
- 插图逻辑目前为简单插入，尚未根据段落语义做精细化分配
- 前端“图片管理”完整入口与独立管理页仍需继续完善联动

### 建议后续完善

- 为文本资料建立独立知识源与业务知识库
- 增加批量导入、批量打标、批量刷新能力
- 优化图片插入策略，支持按段落或章节匹配
- 为 `/api/images` 增加更完整的分页、过滤与错误提示
- 将图片管理页与配置页形成完整双向入口

---

## 提交前检查建议

当前暂存中除功能变更外，还包含配置内容变更。提交前建议重点检查：

- `config.yaml` 中是否误提交真实密钥、公众号凭据或个人化默认值
- `knowledge_storage/latest_kickoff_task_outputs.db` 是否属于应入库的产物
- 端口从 `8000/8001` 调整到 `8888` 的变更是否为预期行为
- 向量嵌入面板的样式与现有配置页风格是否完全一致

---

## 配套文档

本次已补充：

- `docs/knowledge_management.md`
- `docs/image_management_api.md`

可结合这些文档查看本次暂存中知识库与图片资源库相关的设计和接口说明。
