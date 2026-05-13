# AIWriteX-CE

**AIWriteX Community Edition** — 基于 CrewAI 多智能体框架的 AI 写作助手，专注微信公众号内容创作。

> 本项目是基于 [AIWriteX](https://github.com/iniwap/AIWriteX)（版权所有 © iniwap）的社区驱动衍生版本。
> 原项目代码版本至 V2.3.3，本社区版在此基础之上进行了底层架构重构与功能增强。

## 社区版变更

基于原版 V2.3.3，社区版进行了以下重构和增强：

- **底层架构重构**：知识库/图库 Repository 模式、配置管理单例优化
- **知识库管理系统**：新增文本知识库（向量检索 + 关键词回退）和图片知识库双面板管理界面
- **知识库 REST API**：完整的 CRUD 接口，支持分类、标签、语义搜索
- **CrewAI Knowledge 集成**：TextKnowledgeSearchTool 作为 CrewAI BaseTool 接入工作流
- **前端 UI 重构**：知识库管理界面、知识嵌入器配置面板
- **文章模板转换器**：支持 HTML 模板到微信文章格式的自动转换

## 技术栈

| 组件 | 技术 |
|------|------|
| 语言 | Python 3.10+ |
| 多智能体 | CrewAI |
| Web 框架 | FastAPI |
| GUI | PyWebView |
| 向量数据库 | ChromaDB |
| 前端 | 原生 JS + CSS |

## 快速开始

### 1. 克隆仓库

```bash
git clone https://github.com/YOUR_USERNAME/AIWriteX-CE.git
cd AIWriteX-CE
```

### 2. 安装依赖

```bash
pip install uv
uv venv
uv pip install -r requirements.txt
```

### 3. 配置

编辑 `src/ai_write_x/config/config.yaml`，填写必填项：

- **微信公众号**：AppID / AppSecret / Author
- **大模型 API**：api_type / api_key / model

### 4. 运行

```bash
# GUI 模式（推荐）
python main.py

# 无 UI 模式
python -m src.ai_write_x.crew_main
```

## 项目结构

```
src/ai_write_x/
├── core/           # 核心框架（工作流编排、Agent工厂、知识库管理）
├── tools/          # CrewAI 工具（知识搜索、图片搜索、热搜获取）
├── adapters/       # 平台适配器（微信公众号、小红书、抖音等 7 平台）
├── creative/       # 维度化创意引擎（16 个创意维度）
├── web/            # Web 层（FastAPI + 前端静态资源）
├── config/         # 配置管理（单例模式，线程安全）
├── utils/          # 工具函数（日志、路径、通信）
└── license/        # 许可证模块
```

## 核心功能

- 全网热点自动抓取 + AI 选题推荐
- CrewAI 多智能体协作（研究员 → 作家 → 审核员 → 设计师）
- AIForge 实时搜索 + 竞品借鉴
- 16 维度创意变换引擎
- 微信公众号一键发布（支持多账号、定时、批量）
- 可视化知识库管理（文本 + 图片双面板）
- 去 AI 味 + 对抗检测优化
- 资源图库 + AI 自动配图

## 许可证

本仓库包含 [AIWriteX](https://github.com/iniwap/AIWriteX) 的原始代码及其社区修改版本。

- 原始代码版权所有 © 2025 iniwap，遵循 [AIWriteX 许可证](./docs/license.txt)
- 社区修改部分同样受原许可证条款约束
- 非商业使用可自由修改，须保留原始版权声明和许可证文件
- 分发或商业使用需获得原作者书面授权

## 致谢

- [AIWriteX](https://github.com/iniwap/AIWriteX) — 原始项目，由 iniwap 开发
- [CrewAI](https://github.com/crewAIInc/crewAI) — 多智能体框架
- [FastAPI](https://github.com/tiangolo/fastapi) — Web 框架
