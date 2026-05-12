# AIWriteX 关键函数入口

> 最后更新: 2026-05-12

---

## 1. 应用入口

### 1.1 GUI模式入口 (main.py)

```python
# main.py
def run():
    """启动GUI应用程序"""
    from src.ai_write_x.license import check_license_and_start
    check_license_and_start()

if __name__ == "__main__":
    multiprocessing.freeze_support()
    multiprocessing.set_start_method("spawn", force=True)

    if AIForgeEngine.handle_sandbox_subprocess(...):
        sys.exit(0)
    else:
        run()
```

**启动流程**:
1. `check_license_and_start()` - 许可证检查与启动
2. `WebViewGUI` - 初始化pywebview GUI
3. `app.py` - 启动FastAPI服务器 (端口8000)
4. 创建pywebview窗口显示Web UI

### 1.2 无UI模式入口 (crew_main.py)

```bash
python -m src.ai_write_x.crew_main
```

核心函数:
- `ai_write_x_main()` - 主入口函数
- `ai_write_x_run()` - 执行写作任务
- `run_crew_in_process()` - 在独立进程中运行CrewAI工作流

---

## 2. 许可证检查

**位置**: `src/ai_write_x/license/__init__.py`

```python
def check_license_and_start():
    """检查许可证并启动应用"""
    # 验证许可证
    # 启动WebViewGUI
```

---

## 3. Web API入口

**位置**: `src/ai_write_x/web/app.py`

```python
from fastapi import FastAPI

app = FastAPI(title="AIWriteX API")

# 挂载子路由
app.include_router(articles.router, prefix="/api/articles")
app.include_router(config.router, prefix="/api/config")
app.include_router(templates.router, prefix="/api/templates")
app.include_router(generate.router, prefix="/api/generate")
```

### 3.1 API路由

| 路由 | 文件 | 说明 |
|------|------|------|
| `/api/articles/*` | web/api/articles.py | 文章管理 (列表/删除/发布记录) |
| `/api/config/*` | web/api/config.py | 配置读取/保存 |
| `/api/templates/*` | web/api/templates.py | 模板读取 |
| `/api/generate/*` | web/api/generate.py | 文章生成 (核心API) |

### 3.2 核心生成API

**位置**: `src/ai_write_x/web/api/generate.py`

```python
@router.post("/start")
async def start_generation(request: GenerationRequest):
    """开始文章生成"""
    # 验证配置
    # 调用 UnifiedContentWorkflow.execute()
    # 返回生成结果
```

---

## 4. 核心工作流入口

### 4.1 UnifiedContentWorkflow.execute()

**位置**: `src/ai_write_x/core/unified_workflow.py`

```python
def execute(self, topic: str, **kwargs) -> Dict[str, Any]:
    """统一执行流程：输入 -> 内容生成 -> 格式处理 -> 保存 -> 发布"""
    start_time = time.time()
    success = False

    try:
        # 1. 生成基础内容
        base_content = self._generate_base_content(topic, publish_platform=publish_platform, **kwargs)

        # 2. 维度化创意变换
        final_content = self._apply_dimensional_creative_transformation(base_content, **kwargs)

        # 3. 内容转换 (Template/Design)
        transform_content = self._transform_content(final_content, publish_platform, **kwargs)

        # 4. 保存
        save_result = self._save_content(transform_content, title)

        # 5. 可选发布
        if self._should_publish():
            publish_result = self._publish_content(transform_content, publish_platform, **kwargs)

        return {
            "base_content": base_content,
            "final_content": final_content,
            "formatted_content": transform_content.content,
            "save_result": save_result,
            "publish_result": publish_result,
            "success": True,
        }
    finally:
        duration = time.time() - start_time
        self.monitor.track_execution("unified_workflow", duration, success, {"topic": topic})
```

### 4.2 ContentGenerationEngine.execute_workflow()

**位置**: `src/ai_write_x/core/content_generation.py`

```python
def execute_workflow(self, input_data: Dict[str, Any]) -> ContentResult:
    """执行工作流并记录监控数据"""
    start_time = time.time()
    success = False

    try:
        self.validate_config()
        self.agents = self.setup_agents()
        self.tasks = self.setup_tasks()

        crew = Crew(
            agents=list(self.agents.values()),
            tasks=list(self.tasks.values()),
            process=Process.sequential,
            verbose=True,
        )

        result = crew.kickoff(inputs=input_data)
        result = utils.remove_code_blocks(str(result))

        # 解析结果
        if input_data.get("parse_result", True):
            parsed = ContentParser.parse_generation_result(result)
            return ContentResult(
                title=parsed.get("title", ""),
                content=parsed.get("content", ""),
                summary=parsed.get("summary", ""),
                content_format="markdown",
            )
        ...
```

---

## 5. 工具入口

### 5.1 AIForgeSearchTool

**位置**: `src/ai_write_x/tools/search_template.py`

```python
class AIForgeSearchTool(BaseTool):
    name = "AIForgeSearchTool"
    description = "使用AIForge引擎搜索最新信息..."

    def _run(self, topic: str, urls: List[str] = None, reference_ratio: float = 0.0):
        """执行搜索"""
        # 调用AIForgeEngine获取搜索结果
```

### 5.2 TextKnowledgeSearchTool

**位置**: `src/ai_write_x/tools/text_knowledge_search_tool.py`

```python
class TextKnowledgeSearchTool(BaseTool):
    name = "text_knowledge_search"
    description = "搜索文本知识库，根据关键词找到相关参考资料..."

    def _run(self, query: str, limit: int = 3):
        """执行搜索: 向量检索 → 关键词双向匹配回退"""
        # 1. KnowledgeManager.search_texts() - ChromaDB 向量检索
        # 2. TextKnowledgeRepository.search() - 关键词双向匹配回退
        # 3. 返回完整正文 (JSON: [{title, summary, tags, category, content}])
```

**调用者**: `researcher` Agent (CrewAI Task: `search_knowledge`)

### 5.3 ImageSearchTool

**位置**: `src/ai_write_x/tools/image_search_tool.py`

```python
class ImageSearchTool(BaseTool):
    name = "image_search"
    description = "搜索图片库，根据文章主题找到相关图片路径..."

    def _run(self, query: str, category=None, limit=3):
        """执行搜索: 向量检索 → ImageRepository关键词回退"""
```

**调用者**: `writer` Agent (CrewAI Task: `write_content`)

### 5.4 ReadTemplateTool

**位置**: `src/ai_write_x/tools/custom_tool.py`

```python
class ReadTemplateTool(BaseTool):
    name = "ReadTemplateTool"
    description = "读取本地HTML模板..."

    def _run(self, **kwargs):
        """读取并返回模板内容"""
```

### 5.3 WxPublisher

**位置**: `src/ai_write_x/tools/wx_publisher.py`

```python
def pub2wx(content, title, cover_path=None, **kwargs):
    """发布到微信公众号"""
    # 获取access_token
    # 上传封面图
    # 创建草稿
    # 发布
```

---

## 6. 平台发布入口

**位置**: `src/ai_write_x/adapters/platform_adapters.py`

```python
class WeChatAdapter(PlatformAdapter):
    def publish_content(self, content_result: ContentResult, **kwargs) -> PublishResult:
        """发布到微信公众号"""
        from src.ai_write_x.tools.wx_publisher import pub2wx
        result = pub2wx(
            content=content_result.content,
            title=content_result.title,
            cover_path=kwargs.get("cover_path"),
            ...
        )
        return PublishResult(success=result.get("success", False), message=result.get("message", ""))
```

---

## 7. 配置入口

### 7.1 Config

**位置**: `src/ai_write_x/config/config.py`

```python
class Config:
    @classmethod
    def get_instance(cls):
        """获取单例实例"""

    def load_config(self):
        """加载配置"""

    def save_config(self, config, aiforge_config=None):
        """保存配置"""

    def validate_config(self):
        """验证配置，仅在CrewAI执行时调用"""

    def merge_with_user_config(self, user_config: dict) -> dict:
        """智能合并用户配置"""
```

---

## 8. 关键调用链

```
用户点击生成
    ↓
POST /api/generate/start
    ↓
generate.py::start_generation()
    ↓
Config.get_instance().validate_config()  # 验证配置
    ↓
UnifiedContentWorkflow().execute(topic, **kwargs)
    ├→ _generate_base_content()
    │   └→ ContentGenerationEngine().execute_workflow()
    │       └→ CrewAI Crew.kickoff()  [Sequential Tasks]
    │           ├→ Task 1: search_knowledge (Agent: researcher)
    │           │   └→ TextKnowledgeSearchTool  # 知识库搜索
    │           └→ Task 2: write_content (Agent: writer)
    │               └→ AIForgeSearchTool + ImageSearchTool  # 网络搜索+图片
    │
    ├→ _apply_dimensional_creative_transformation()
    │   └→ DimensionalCreativeEngine.apply_dimensional_creative()
    │
    ├→ _transform_content()  # Template/Design路径
    │   └→ ContentGenerationEngine().execute_workflow()
    │
    ├→ _save_content()  # 保存到output/
    │
    └→ _publish_content()  # 调用平台适配器
        └→ WeChatAdapter.publish_content()
            └→ pub2wx()
```