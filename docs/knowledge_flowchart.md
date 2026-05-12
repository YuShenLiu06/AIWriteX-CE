# 知识库调用流程图

> 本文档使用 Mermaid 图表说明 AIWriteX 知识库的整体架构和调用链。

---

## 1. 知识库整体架构图

```mermaid
flowchart TB
    subgraph 前端["前端 (Web UI)"]
        KMJS[knowledge-manager.js<br/>知识库管理交互]
        KMTpls[HTML Templates<br/>knowledge-manager.html]
    end

    subgraph API层["FastAPI Layer (api/)"]
        text_knowledge_api[text_knowledge.py<br/>文本知识 CRUD]
        knowledge_api[knowledge.py<br/>知识库统计/刷新]
    end

    subgraph Core层["Core Module (core/)"]
        KM[KnowledgeManager<br/>单例模式 - CrewAI封装]
        TR[TextKnowledgeRepository<br/>单例模式 - JSON存储]
        IR[ImageRepository<br/>单例模式 - JSON存储]
    end

    subgraph Storage层["Storage Layer"]
        JSON_TEXT[text_knowledge_index.json<br/>文本知识索引]
        JSON_IMAGE[image_index.json<br/>图片知识索引]
        CREWAI_STORAGE[(CrewAI Storage<br/>向量数据库)]
    end

    subgraph CrewAI层["CrewAI Knowledge"]
        CK[CrewAI Knowledge<br/>向量检索]
        SS[StringKnowledgeSource<br/>字符串知识源]
    end

    subgraph Workflow层["Workflow Execution"]
        UW[UnifiedWorkflow<br/>统一内容工作流]
        CGE[ContentGenerationEngine<br/>内容生成引擎]
    end

    %% 前端交互
    KMJS --> |POST/GET /api/text-knowledge| text_knowledge_api
    KMJS --> |POST /api/knowledge/refresh| knowledge_api

    %% API层处理
    text_knowledge_api --> TR
    text_knowledge_api --> KM
    knowledge_api --> KM

    %% 知识仓库
    TR --> JSON_TEXT
    IR --> JSON_IMAGE

    %% CrewAI集成
    KM --> |initialize| CK
    CK --> SS
    SS --> TR
    KM --> |get_all_knowledge_sources| CREWAI_STORAGE

    %% 工作流调用
    UW --> |get_base_content_config| KM
    KM --> |knowledge_sources| CGE
    CGE --> |Crew.kickoff| CREWAI_STORAGE
```

---

## 2. 新增文本知识时序图

```mermaid
sequenceDiagram
    participant U as 用户
    participant JS as knowledge-manager.js
    participant API as text_knowledge API
    participant Repo as TextKnowledgeRepository
    participant KM as KnowledgeManager
    participant JSON as JSON文件
    participant CREWAI as CrewAI Knowledge

    U->>JS: 点击"新增文本"按钮
    JS->>JS: showAddModal() → showTextModal()
    JS->>U: 显示新增Modal

    U->>JS: 填写表单（标题、内容、摘要、标签等）
    U->>JS: 点击确认保存
    JS->>JS: saveTextItem() 收集表单数据

    JS->>API: POST /api/text-knowledge
    Note over API: Content-Type: application/json<br/>{title, content, summary, tags, ...}

    API->>Repo: repo.add_item(title, content, ...)
    Repo->>JSON: 序列化并写入<br/>text_knowledge_index.json
    JSON-->>Repo: 保存成功
    Repo-->>API: 返回 TextKnowledgeItem

    API->>KM: refresh_texts()
    KM->>KM: initialize() 重新初始化
    KM->>CREWAI: 重建文本知识库
    CREWAI-->>KM: 初始化完成
    KM-->>API: 刷新完成

    API-->>JS: 200 OK {status:"success", data:{...}}
    JS->>U: showNotification('文本知识已新增')
    JS->>JS: hideTextModal()
    JS->>JS: loadTextKnowledge() 刷新列表
```

---

## 3. AI/Agent 调用知识库流程

### 3.1 初始化阶段

```mermaid
flowchart TB
    subgraph Init["初始化阶段"]
        direction TB
        A1[Config加载<br/>config.yaml] --> A2[UnifiedWorkflow实例化]
        A2 --> A3[get_base_content_config()]
        A3 --> A4[KnowledgeManager.get_all_knowledge_sources()]
        A4 --> A5[返回 List&lt;BaseKnowledgeSource&gt;]
    end

    subgraph Setup["CrewAI Crew 构建"]
        direction TB
        B1[ContentGenerationEngine初始化] --> B2[传入 knowledge_sources]
        B2 --> B3[传入 embedder 配置]
        B3 --> B4[Crew(agents, tasks, knowledge_sources...)]
    end

    A5 --> B4
```

### 3.2 执行阶段时序图

```mermaid
sequenceDiagram
    participant WF as UnifiedWorkflow
    participant KM as KnowledgeManager
    participant CK as CrewAI Knowledge
    participant CGE as ContentGenerationEngine
    participant CREW as CrewAI Crew
    participant AGENT as Agent
    participant VDB as 向量数据库

    WF->>KM: get_all_knowledge_sources()
    KM->>CK: initialize()
    Note over CK: 从JSON读取所有文本/图片<br/>构建 StringKnowledgeSource

    WF->>CGE: execute(input_data)

    CGE->>CREW: Crew(knowledge_sources=...)
    CREW->>AGENT: Agent 开始执行 Task

    AGENT->>CK: 查询相关知识
    CK->>VDB: 向量相似度搜索
    VDB-->>CK: 返回 Top-K 相关知识块
    CK-->>AGENT: 返回相关上下文

    AGENT-->>CREW: Task 完成
    CREW-->>CGE: CrewResult
    CGE-->>WF: 最终内容结果
```

---

## 4. 关键文件索引

| 层次 | 文件路径 | 说明 |
|------|----------|------|
| 前端 | `src/ai_write_x/web/static/js/knowledge-manager.js` | 知识库管理交互逻辑 |
| 前端 | `src/ai_write_x/web/templates/components/views/knowledge-manager.html` | 知识库页面模板 |
| API | `src/ai_write_x/web/api/text_knowledge.py` | 文本知识 REST API |
| API | `src/ai_write_x/web/api/knowledge.py` | 统一知识统计/刷新 API |
| Core | `src/ai_write_x/core/knowledge_manager.py` | CrewAI Knowledge 封装 |
| Core | `src/ai_write_x/core/text_knowledge_repository.py` | 文本知识存储 (JSON) |
| Core | `src/ai_write_x/core/image_repository.py` | 图片知识存储 (JSON) |
| Workflow | `src/ai_write_x/core/unified_workflow.py` | 工作流编排器 |
| Workflow | `src/ai_write_x/core/content_generation.py` | 内容生成引擎 |

---

## 5. 配置说明

知识库 embedder 配置位于 `config.yaml`:

```yaml
knowledge:
  embedder:
    provider: openai        # openai / ollama / deepseek 等
    api_key: sk-xxx        # API密钥
    model: text-embedding-3-small  # 嵌入模型
    base_url: https://api.openai.com/v1  # API地址
```

CrewAI 存储目录: `{app_data_dir}/knowledge_storage/`