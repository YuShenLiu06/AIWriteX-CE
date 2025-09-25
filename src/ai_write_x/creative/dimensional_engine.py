# -*- coding: utf-8 -*-
"""
维度化创意引擎
实现基于多维度组合的创意生成机制
"""

import random
from typing import Dict, List, Any, Tuple

# 移除了从 dimensional_config.py 导入的代码


class DimensionalCreativeEngine:
    """
    维度化创意引擎
    支持基于多个维度的创意组合和生成
    """

    def __init__(self, config: Dict[str, Any]):
        """
        初始化维度化创意引擎

        Args:
            config: 维度化创意配置
        """
        self.config = config
        # 从配置中获取维度选项配置，而不是从硬编码的代码中获取
        self.dimension_config = config.get("dimension_options", {})

    def get_available_dimensions(self) -> List[str]:
        """
        获取可用的维度分类列表

        Returns:
            可用维度分类列表
        """
        # 获取所有可用维度
        all_dimensions = self.config.get("available_categories", [])

        # 获取启用的维度
        enabled_dimensions = self.config.get("enabled_dimensions", {})

        # 过滤出启用的维度
        available_dimensions = [
            dim for dim in all_dimensions if enabled_dimensions.get(dim, True)  # 默认启用
        ]

        return available_dimensions

    def get_dimension_options(self, dimension: str) -> List[Dict[str, Any]]:
        """
        获取指定维度的选项列表

        Args:
            dimension: 维度分类

        Returns:
            该维度的选项列表
        """
        # 检查维度是否启用
        enabled_dimensions = self.config.get("enabled_dimensions", {})
        if not enabled_dimensions.get(dimension, True):
            return []  # 如果维度未启用，返回空列表

        if dimension in self.dimension_config:
            options = self.dimension_config[dimension].get("preset_options", []).copy()
            # 检查是否有自定义选项
            custom_input = self.dimension_config[dimension].get("custom_input", "")
            if custom_input:
                # 添加自定义选项
                custom_option = {
                    "name": "custom",
                    "value": custom_input,
                    "weight": 1.0,
                    "description": "用户自定义",
                }
                options.append(custom_option)
            return options
        return []

    def get_custom_dimensions(self) -> List[str]:
        """
        获取用户自定义维度

        Returns:
            用户自定义维度列表
        """
        # 根据新设计，不再支持用户自定义维度库
        return []

    def parse_custom_dimension(self, custom_dim_str: str) -> Dict[str, str]:
        """
        解析自定义维度字符串

        Args:
            custom_dim_str: 自定义维度字符串，格式为"维度分类:维度名称:描述"

        Returns:
            解析后的维度字典
        """
        # 根据新设计，不再支持用户自定义维度库
        return {}

    def get_all_dimension_options(self, dimension: str) -> List[Dict[str, Any]]:
        """
        获取指定维度的所有选项（包括预设选项和自定义选项）

        Args:
            dimension: 维度分类

        Returns:
            该维度的所有选项列表
        """
        # 获取预设选项
        preset_options = self.get_dimension_options(dimension)
        return preset_options

    def select_dimensions(
        self, auto_selection: bool = True, max_dimensions: int = 5
    ) -> List[Tuple[str, Dict[str, Any]]]:
        """
        选择维度组合

        Args:
            auto_selection: 是否自动选择
            max_dimensions: 最大维度数量

        Returns:
            选中的维度组合列表，每个元素为(维度分类, 选项)
        """
        selected_dimensions = []
        available_categories = self.get_available_dimensions()

        if auto_selection:
            # 自动选择维度
            # 根据优先级选择维度
            priority_categories = self.config.get("priority_categories", [])

            # 收集候选维度组合
            candidate_dimensions = []

            # 首先从优先维度中选择
            for category in priority_categories:
                if category in available_categories:
                    options = self.get_all_dimension_options(category)
                    if options:
                        for option in options:
                            candidate_dimensions.append((category, option))

            # 如果还需要更多维度，从其他可用维度中选择
            remaining_categories = [
                cat for cat in available_categories if cat not in priority_categories
            ]

            for category in remaining_categories:
                options = self.get_all_dimension_options(category)
                if options:
                    for option in options:
                        candidate_dimensions.append((category, option))

            # 使用兼容性阈值过滤候选维度组合
            compatibility_threshold = self.config.get("compatibility_threshold", 0.6)

            # 随机选择维度组合并检查兼容性
            random.shuffle(candidate_dimensions)

            selected_count = 0
            for category, option in candidate_dimensions:
                # 创建临时维度组合来测试兼容性
                temp_dimensions = selected_dimensions + [(category, option)]
                compatibility_score = self.validate_dimension_compatibility(temp_dimensions)

                # 如果兼容性分数满足阈值要求，则添加到选中列表
                if compatibility_score >= compatibility_threshold:
                    selected_dimensions.append((category, option))
                    selected_count += 1
                    if selected_count >= max_dimensions:
                        break
        else:
            # 手动选择维度（从配置中获取用户选择的维度）
            selected_dims = self.config.get("selected_dimensions", [])
            compatibility_threshold = self.config.get("compatibility_threshold", 0.6)

            # 先收集所有手动选择的维度
            candidate_dimensions = []
            for dim_info in selected_dims:
                category = dim_info.get("category")
                option_name = dim_info.get("option")
                # 检查维度是否启用
                enabled_dimensions = self.config.get("enabled_dimensions", {})
                if category and option_name and enabled_dimensions.get(category, True):
                    # 特殊处理自定义选项
                    if option_name == "custom":
                        # 获取自定义输入
                        dimension_config = self.dimension_config.get(category, {})
                        custom_input = dimension_config.get("custom_input", "")
                        if custom_input:
                            custom_option = {
                                "name": "custom",
                                "value": custom_input,
                                "weight": 1.0,
                                "description": "用户自定义",
                            }
                            candidate_dimensions.append((category, custom_option))
                    else:
                        options = self.get_all_dimension_options(category)
                        for option in options:
                            if option.get("name") == option_name:
                                candidate_dimensions.append((category, option))
                                break

            # 按照兼容性阈值过滤维度组合
            # 逐个添加维度并检查兼容性
            for category, option in candidate_dimensions:
                # 创建临时维度组合来测试兼容性
                temp_dimensions = selected_dimensions + [(category, option)]
                compatibility_score = self.validate_dimension_compatibility(temp_dimensions)

                # 如果兼容性分数满足阈值要求，则添加到选中列表
                # 注意：这里使用 > 而不是 >=，确保不兼容的组合被过滤掉
                if compatibility_score > compatibility_threshold:
                    selected_dimensions.append((category, option))
                # 如果不满足兼容性要求，则跳过该维度（不添加到选中列表）

        return selected_dimensions

    def generate_creative_prompt(
        self, base_content: str, selected_dimensions: List[Tuple[str, Dict[str, Any]]]
    ) -> str:
        """
        根据选中的维度生成创意提示

        Args:
            base_content: 基础内容
            selected_dimensions: 选中的维度组合

        Returns:
            创意提示文本
        """
        prompt_parts = []

        # 添加基础内容
        prompt_parts.append(f"基础内容：{base_content}")

        # 添加维度信息
        prompt_parts.append("\n创意维度要求：")
        for category, option in selected_dimensions:
            # 从配置中获取维度的显示名称
            category_name = self.dimension_config.get(category, {}).get("name", category)
            # 特殊处理自定义选项
            if option.get("name") == "custom":
                prompt_parts.append(f"- {category_name}：{option['value']} (用户自定义)")
            else:
                description = option["description"]
                prompt_parts.append(f"- {category_name}：{option['value']} ({description})")

        # 添加创意强度信息
        creative_intensity = self.config.get("creative_intensity", 1.0)
        intensity_desc = self._get_intensity_description(creative_intensity)
        prompt_parts.append(f"\n创意强度：{intensity_desc} ({creative_intensity})")

        # 添加其他配置信息
        if self.config.get("preserve_core_info"):
            prompt_parts.append("\n要求：在创意变换中保持文章核心信息不变")

        if self.config.get("allow_experimental"):
            prompt_parts.append("\n允许：使用实验性的维度组合")

        prompt_parts.append("\n请根据以上要求对基础内容进行创意变换，生成富有创意的文章。")

        return "\n".join(prompt_parts)

    def _get_intensity_description(self, intensity: float) -> str:
        """
        根据创意强度值获取描述

        Args:
            intensity: 创意强度值

        Returns:
            强度描述
        """
        if intensity < 0.8:
            return "保守"
        elif intensity < 1.0:
            return "适中"
        elif intensity < 1.2:
            return "激进"
        else:
            return "非常激进"

    def apply_dimensional_creative(self, content: str) -> str:
        """
        应用维度化创意到内容

        Args:
            content: 原始内容

        Returns:
            应用维度化创意后的内容
        """
        # 检查是否启用维度化创意
        if not self.config.get("enabled", False):
            return content

        # 选择维度组合
        auto_selection = self.config.get("auto_dimension_selection", True)
        max_dimensions = self.config.get("max_dimensions", 5)
        selected_dimensions = self.select_dimensions(auto_selection, max_dimensions)

        # 生成创意提示
        creative_prompt = self.generate_creative_prompt(content, selected_dimensions)

        # 这里应该调用AI模型来生成创意内容
        # 为了演示，我们返回创意提示
        return creative_prompt

    def validate_dimension_compatibility(
        self, dimensions: List[Tuple[str, Dict[str, Any]]]
    ) -> float:
        """
        验证维度组合的兼容性

        Args:
            dimensions: 维度组合

        Returns:
            兼容性分数 (0-1)
        """
        # 简单的兼容性检查实现
        # 在实际应用中，这里可以实现更复杂的兼容性逻辑

        # 检查是否有冲突的维度组合
        categories = [dim[0] for dim in dimensions]

        # 某些维度组合可能不兼容
        incompatible_pairs = [
            ("style", "format"),  # 文体风格和表达格式可能冲突
            ("time", "scene"),  # 时空背景和场景环境可能冲突
        ]

        conflicts = 0
        for cat1, cat2 in incompatible_pairs:
            if cat1 in categories and cat2 in categories:
                conflicts += 1

        # 计算兼容性分数
        if conflicts == 0:
            return 1.0
        else:
            return max(0.0, 1.0 - conflicts * 0.5)  # 每个冲突降低0.5分，使不兼容组合更容易被过滤
