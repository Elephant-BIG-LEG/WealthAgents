"""
财富 Agent - 智能投研分析平台
工具注册中心模块
统一管理所有工具的注册、发现和元数据查询
"""
from typing import Dict, Any, List, Optional, Callable, Type
import logging
from .base_tool import ToolCategory, ErrorCodes, StandardizedToolResponse
from .tool_base import BaseTool, LegacyToolAdapter


class ToolRegistry:
    """
    工具注册中心

    单例模式，管理所有已注册的工具
    """

    _instance = None
    _initialized = False

    def __new__(cls):
        """单例模式实现"""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        """初始化工具注册中心"""
        if not self._initialized:
            self.tools: Dict[str, BaseTool] = {}
            self.tool_metadata: Dict[str, Dict[str, Any]] = {}
            self.logger = logging.getLogger(__name__)
            self._initialized = True

    def register(self, tool: BaseTool, override: bool = False) -> bool:
        """
        注册工具

        Args:
            tool: 工具实例
            override: 是否允许覆盖已存在的工具

        Returns:
            注册是否成功
        """
        tool_name = tool.name

        # 检查是否已存在
        if tool_name in self.tools and not override:
            self.logger.warning(
                f"工具 {tool_name} 已存在，跳过注册（设置 override=True 可强制覆盖）")
            return False

        # 注册工具
        self.tools[tool_name] = tool
        self.tool_metadata[tool_name] = tool.get_definition()

        self.logger.info(f"工具 {tool_name} 注册成功")
        return True

    def register_function(self, func: Callable, name: str = None,
                          description: str = None, category: str = None,
                          override: bool = False) -> bool:
        """
        注册函数为工具（自动适配）

        Args:
            func: 函数对象
            name: 工具名称（可选，默认使用函数名）
            description: 工具描述（可选）
            category: 工具分类（可选）
            override: 是否允许覆盖

        Returns:
            注册是否成功
        """
        # 创建适配器
        adapter = LegacyToolAdapter(
            legacy_func=func,
            name=name,
            description=description
        )

        # 设置分类
        if category:
            adapter.category = category

        # 注册适配器
        return self.register(adapter, override)

    def unregister(self, tool_name: str) -> bool:
        """
        注销工具

        Args:
            tool_name: 工具名称

        Returns:
            注销是否成功
        """
        if tool_name not in self.tools:
            self.logger.warning(f"工具 {tool_name} 不存在，无法注销")
            return False

        del self.tools[tool_name]
        del self.tool_metadata[tool_name]

        self.logger.info(f"工具 {tool_name} 已注销")
        return True

    def get_tool(self, tool_name: str) -> Optional[BaseTool]:
        """
        获取工具实例

        Args:
            tool_name: 工具名称

        Returns:
            工具实例，不存在则返回 None
        """
        tool = self.tools.get(tool_name)

        if tool is None:
            self.logger.warning(f"工具 {tool_name} 未找到")

        return tool

    def get_tools_by_category(self, category: str) -> List[BaseTool]:
        """
        按分类获取工具列表

        Args:
            category: 工具分类

        Returns:
            工具实例列表
        """
        return [
            tool for tool in self.tools.values()
            if tool.category == category
        ]

    def list_tools(self) -> List[str]:
        """
        列出所有已注册的工具名称

        Returns:
            工具名称列表
        """
        return list(self.tools.keys())

    def list_metadata(self) -> Dict[str, Dict[str, Any]]:
        """
        列出所有工具的元数据

        Returns:
            工具元数据字典 {tool_name: metadata}
        """
        return self.tool_metadata.copy()

    def has_tool(self, tool_name: str) -> bool:
        """
        检查工具是否存在

        Args:
            tool_name: 工具名称

        Returns:
            是否存在
        """
        return tool_name in self.tools

    def get_tool_info(self, tool_name: str) -> Optional[Dict[str, Any]]:
        """
        获取工具详细信息

        Args:
            tool_name: 工具名称

        Returns:
            工具信息字典，不存在则返回 None
        """
        if tool_name not in self.tools:
            return None

        info = self.tool_metadata.get(tool_name, {})
        info["registered"] = True
        info["callable"] = True

        return info

    def search_tools(self, keyword: str) -> List[Dict[str, Any]]:
        """
        搜索工具（基于关键词匹配）

        Args:
            keyword: 搜索关键词

        Returns:
            匹配的工具信息列表
        """
        matched_tools = []
        keyword_lower = keyword.lower()

        for tool_name, metadata in self.tool_metadata.items():
            # 在名称和描述中搜索
            if (keyword_lower in tool_name.lower() or
                    keyword_lower in metadata.get("description", "").lower()):
                matched_tools.append({
                    "name": tool_name,
                    "description": metadata.get("description", ""),
                    "category": metadata.get("category", ""),
                    "version": metadata.get("version", "")
                })

        return matched_tools

    def clear(self):
        """清空所有注册的工具"""
        self.tools.clear()
        self.tool_metadata.clear()
        self.logger.info("工具注册中心已清空")

    def execute_tool(self, tool_name: str, query: str = "", **params) -> Dict[str, Any]:
        """
        执行工具的便捷方法

        Args:
            tool_name: 工具名称
            query: 查询关键词
            **params: 工具参数

        Returns:
            工具执行结果
        """
        tool = self.get_tool(tool_name)

        if tool is None:
            return StandardizedToolResponse.error(
                message=f"工具 {tool_name} 未找到",
                error_code=ErrorCodes.TOOL_NOT_FOUND
            )

        try:
            # 执行工具
            return tool.run(query, **params)
        except Exception as e:
            self.logger.error(f"执行工具 {tool_name} 失败：{str(e)}", exc_info=True)
            return StandardizedToolResponse.error(
                message=str(e),
                error_code=ErrorCodes.EXECUTION_ERROR,
                tool_name=tool_name
            )


# 全局工具注册中心实例
global_registry = ToolRegistry()


def get_global_registry() -> ToolRegistry:
    """获取全局工具注册中心实例"""
    return global_registry


# 便捷的装饰器，用于快速注册工具
def register_tool(name: str = None, description: str = None,
                  category: str = None, registry: ToolRegistry = None):
    """
    工具注册装饰器

    使用方式:
    @register_tool(name="my_tool", description="我的工具", category="data_analysis")
    class MyTool(BaseTool):
        def execute(self, tool_input: ToolInput) -> ToolOutput:
            pass

    Args:
        name: 工具名称
        description: 工具描述
        category: 工具分类
        registry: 指定的注册中心（默认使用全局注册中心）

    Returns:
        装饰器函数
    """
    def decorator(cls):
        # 创建工具实例
        tool_instance = cls()

        # 如果类中定义了 name 属性，使用它
        if hasattr(cls, 'name') and cls.name != "base_tool":
            tool_instance.name = cls.name

        # 如果提供了 name 参数，覆盖
        if name:
            tool_instance.name = name

        if description:
            tool_instance.description = description

        if category:
            tool_instance.category = category

        # 注册到注册中心
        target_registry = registry or global_registry
        target_registry.register(tool_instance)

        # 返回类本身而不是实例，以便后续可以再次实例化
        return cls

    return decorator


def register_function_as_tool(name: str = None, description: str = None,
                              category: str = None, registry: ToolRegistry = None):
    """
    函数注册为工具装饰器

    使用方式:
    @register_function_as_tool(name="my_func", description="我的函数", category="data_collection")
    def my_function(query: str, **kwargs) -> Dict[str, Any]:
        pass

    Args:
        name: 工具名称
        description: 工具描述
        category: 工具分类
        registry: 指定的注册中心（默认使用全局注册中心）

    Returns:
        装饰器函数
    """
    def decorator(func):
        # 使用全局注册中心或指定的注册中心
        target_registry = registry or global_registry

        # 注册函数
        target_registry.register_function(
            func=func,
            name=name,
            description=description,
            category=category
        )

        # 返回原函数
        return func

    return decorator
