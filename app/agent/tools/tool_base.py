"""
财富 Agent - 智能投研分析平台
基础工具抽象类模块
所有工具必须继承此基类以确保接口统一
"""
from typing import Dict, Any, Optional, List
from abc import ABC, abstractmethod
import time
import logging
from .base_tool import (
    ToolInput,
    ToolOutput,
    ToolDefinition,
    ToolCallRecord,
    StandardizedToolResponse,
    ErrorCodes,
    ToolCategory,
    validate_tool_response,
    normalize_legacy_response
)


class BaseTool(ABC):
    """
    基础工具抽象类

    所有工具必须继承此类并实现抽象方法

    Attributes:
        name: 工具名称
        description: 工具描述
        category: 工具分类
        version: 工具版本
        logger: 日志记录器
    """

    name: str = "base_tool"
    description: str = "基础工具"
    category: str = ToolCategory.GENERAL
    version: str = "1.0.0"

    def __init__(self):
        """初始化工具"""
        self.logger = logging.getLogger(
            f"{self.__class__.__module__}.{self.__class__.__name__}")
        self._definition = self._create_definition()

    @abstractmethod
    def execute(self, tool_input: ToolInput) -> ToolOutput:
        """
        执行工具的抽象方法（必须实现）

        Args:
            tool_input: 标准化的工具输入对象

        Returns:
            标准化的工具输出对象
        """
        pass

    def run(self, query: str = "", **params) -> Dict[str, Any]:
        """
        运行工具的便捷方法（推荐使用）

        Args:
            query: 查询关键词
            **params: 工具特定参数

        Returns:
            标准化的响应字典
        """
        # 构建标准输入
        input_obj = ToolInput(
            query=query,
            params=params
        )

        # 记录调用开始
        start_time = time.time()
        self.logger.info(f"开始执行工具 {self.name}, query: {query}")

        try:
            # 执行工具逻辑
            output_obj = self.execute(input_obj)

            # 计算执行时间
            execution_time = time.time() - start_time
            output_obj.metadata["execution_time"] = execution_time
            output_obj.metadata["tool_name"] = self.name

            # 验证响应格式
            result = output_obj.to_dict()
            if not validate_tool_response(result):
                self.logger.warning(f"工具 {self.name} 返回的响应不符合标准格式")

            self.logger.info(f"工具 {self.name} 执行完成，耗时：{execution_time:.2f}s")
            return result

        except Exception as e:
            # 异常处理
            execution_time = time.time() - start_time
            self.logger.error(f"工具 {self.name} 执行失败：{str(e)}", exc_info=True)

            return StandardizedToolResponse.error(
                message=str(e),
                error_code=ErrorCodes.EXECUTION_ERROR,
                tool_name=self.name,
                execution_time=execution_time
            )

    def _create_definition(self) -> ToolDefinition:
        """
        创建工具元数据定义

        Returns:
            工具定义对象
        """
        return ToolDefinition(
            name=self.name,
            description=self.description,
            version=self.version,
            category=self.category,
            input_schema=self._get_input_schema(),
            output_schema=self._get_output_schema(),
            examples=self._get_examples(),
            timeout=self._get_timeout(),
            retry_config=self._get_retry_config()
        )

    def _get_input_schema(self) -> Dict[str, Any]:
        """
        获取输入参数 Schema（可重写）

        Returns:
            JSON Schema 格式的输入描述
        """
        return {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "查询关键词或主要输入内容"
                },
                "params": {
                    "type": "object",
                    "description": "工具特定参数"
                }
            },
            "required": ["query"]
        }

    def _get_output_schema(self) -> Dict[str, Any]:
        """
        获取输出结果 Schema（可重写）

        Returns:
            JSON Schema 格式的输出描述
        """
        return {
            "type": "object",
            "properties": {
                "status": {
                    "type": "string",
                    "enum": ["success", "error", "warning"],
                    "description": "执行状态"
                },
                "data": {
                    "type": ["object", "array", "null"],
                    "description": "返回的数据"
                },
                "metadata": {
                    "type": "object",
                    "description": "元数据信息"
                }
            },
            "required": ["status", "data", "metadata"]
        }

    def _get_examples(self) -> List[Dict[str, Any]]:
        """
        获取使用示例（可重写）

        Returns:
            示例列表
        """
        return []

    def _get_timeout(self) -> int:
        """
        获取超时时间（秒）（可重写）

        Returns:
            超时时间
        """
        return 30

    def _get_retry_config(self) -> Dict[str, Any]:
        """
        获取重试配置（可重写）

        Returns:
            重试配置字典
        """
        return {
            "max_retries": 3,
            "retry_delay": 1,
            "backoff_factor": 2
        }

    def get_definition(self) -> Dict[str, Any]:
        """
        获取工具定义信息

        Returns:
            工具定义的字典表示
        """
        return self._definition.to_dict()

    def validate_input(self, tool_input: ToolInput) -> tuple[bool, Optional[str]]:
        """
        验证输入参数（可选重写）

        Args:
            tool_input: 工具输入对象

        Returns:
            (是否有效，错误信息)
        """
        # 默认实现：总是有效
        return True, None

    def preprocess(self, tool_input: ToolInput) -> ToolInput:
        """
        输入预处理（可选重写）

        Args:
            tool_input: 工具输入对象

        Returns:
            预处理后的输入对象
        """
        return tool_input

    def postprocess(self, output: ToolOutput) -> ToolOutput:
        """
        输出后处理（可选重写）

        Args:
            output: 工具输出对象

        Returns:
            后处理后的输出对象
        """
        return output


class LegacyToolAdapter(BaseTool):
    """
    旧工具适配器

    用于将旧格式的函数式工具适配到新标准接口
    """

    def __init__(self, legacy_func, name: str = None, description: str = None):
        """
        初始化旧工具适配器

        Args:
            legacy_func: 旧的函数式工具
            name: 工具名称（可选）
            description: 工具描述（可选）
        """
        self.legacy_func = legacy_func

        # 如果未提供名称和描述，尝试从函数中获取
        if name is None:
            name = getattr(legacy_func, '__name__', 'unknown_tool')
        if description is None:
            description = getattr(legacy_func, '__doc__', '旧工具函数')

        # 设置工具属性
        self.name = name
        self.description = description

        super().__init__()

    def execute(self, tool_input: ToolInput) -> ToolOutput:
        """
        执行旧工具函数并适配为标准格式

        Args:
            tool_input: 标准化的工具输入

        Returns:
            标准化的工具输出
        """
        try:
            # 调用旧工具函数
            # 兼容不同的参数传递方式
            if tool_input.query and not tool_input.params:
                # 只有 query 参数
                raw_result = self.legacy_func(tool_input.query)
            elif tool_input.params and not tool_input.query:
                # 只有 params 参数
                raw_result = self.legacy_func(**tool_input.params)
            elif tool_input.query and tool_input.params:
                # 同时有 query 和 params
                raw_result = self.legacy_func(
                    tool_input.query, **tool_input.params)
            else:
                # 都没有，无参数调用
                raw_result = self.legacy_func()

            # 标准化响应格式
            normalized_result = normalize_legacy_response(raw_result)

            # 确保包含必要的字段
            if "metadata" not in normalized_result:
                normalized_result["metadata"] = {}

            normalized_result["metadata"]["tool_name"] = self.name

            # 转换为 ToolOutput 对象
            return ToolOutput.from_dict(normalized_result)

        except Exception as e:
            self.logger.error(f"旧工具 {self.name} 执行失败：{str(e)}", exc_info=True)
            return ToolOutput(
                status="error",
                data=None,
                error_message=str(e),
                metadata={"tool_name": self.name,
                          "error_code": ErrorCodes.EXECUTION_ERROR}
            )


# 便捷的装饰器，用于快速将函数转换为标准化工具
def standardize_tool(name: str = None, description: str = None, category: str = None):
    """
    工具标准化装饰器

    使用方式:
    @standardize_tool(name="my_tool", description="我的工具")
    def my_tool(query: str, **kwargs) -> Dict[str, Any]:
        # 工具实现
        pass

    Args:
        name: 工具名称
        description: 工具描述
        category: 工具分类

    Returns:
        装饰器函数
    """
    def decorator(func):
        # 创建适配器实例
        adapter = LegacyToolAdapter(
            legacy_func=func,
            name=name or func.__name__,
            description=description or (func.__doc__ or "标准化工具")
        )

        # 设置分类
        if category:
            adapter.category = category

        # 返回适配器实例而不是原函数
        return adapter

    return decorator
