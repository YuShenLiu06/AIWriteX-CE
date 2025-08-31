from typing import Dict, Type, Optional, Any
from crewai import Agent, LLM
from .base_framework import AgentConfig
from ..config.config import Config


class AgentFactory:
    """智能体工厂类"""

    def __init__(self):
        self._agent_templates: Dict[str, Type] = {}
        self._tool_registry: Dict[str, Any] = {}
        self._llm_cache: Dict[str, LLM] = {}

    def register_agent_template(self, role: str, template_class: Type):
        """注册智能体模板"""
        self._agent_templates[role] = template_class

    def register_tool(self, name: str, tool_class):
        """注册工具类"""
        self._tool_registry[name] = tool_class

    def _get_llm(self, llm_config: Dict[str, Any] = None) -> Optional[LLM]:
        """获取LLM实例，支持缓存"""
        config = Config.get_instance()

        # 如果没有指定特殊配置，使用全局配置
        if not llm_config:
            cache_key = f"{config.api_type}_{config.api_model}"
            if cache_key not in self._llm_cache:
                if config.api_key:
                    self._llm_cache[cache_key] = LLM(
                        model=config.api_model, api_key=config.api_key, max_tokens=8192
                    )
                else:
                    return None
            return self._llm_cache.get(cache_key)

        # 使用自定义LLM配置
        cache_key = f"{llm_config.get('model', 'default')}_{llm_config.get('api_key', 'default')}"
        if cache_key not in self._llm_cache:
            self._llm_cache[cache_key] = LLM(**llm_config)
        return self._llm_cache[cache_key]

    def create_agent(self, config: AgentConfig, custom_llm: LLM = None) -> Agent:
        """创建智能体实例"""
        tools = []
        if config.tools:
            for tool_name in config.tools:
                if tool_name in self._tool_registry:
                    tools.append(self._tool_registry[tool_name]())
                else:
                    print(f"Warning: Tool {tool_name} not found in registry")

        agent_kwargs = {
            "role": config.role,
            "goal": config.goal,
            "backstory": config.backstory,
            "tools": tools,
            "allow_delegation": config.allow_delegation,
            "memory": config.memory,
            "max_rpm": config.max_rpm,
            "verbose": config.verbose,
        }

        # LLM优先级：自定义LLM > 配置中的LLM > 全局LLM
        llm = custom_llm or self._get_llm(config.llm_config)
        if llm:
            agent_kwargs["llm"] = llm

        return Agent(**agent_kwargs)

    def create_specialized_agent(self, role: str, **kwargs) -> Agent:
        """创建专门化智能体"""
        if role in self._agent_templates:
            template_class = self._agent_templates[role]
            return template_class(**kwargs)
        else:
            raise ValueError(f"Unknown agent role: {role}")
