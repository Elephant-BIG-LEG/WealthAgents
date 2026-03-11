"""
财富 Agent - 智能投研分析平台
统一工具接口规范模块
定义标准化的工具输入输出 JSON Schema
"""
from typing import Dict, Any, List, Optional, Union
from dataclasses import dataclass, field
from datetime import datetime
import json


@dataclass
class ToolInput:
    """
    统一工具输入 Schema

    Attributes:
        query: 查询关键词或主要输入内容
        params: 工具特定参数（灵活扩展）
        context: 上下文信息（可选）
        metadata: 元数据（可选）
    """
    query: str = ""
    params: Dict[str, Any] = field(default_factory=dict)
    context: Optional[Dict[str, Any]] = None
    metadata: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            "query": self.query,
            "params": self.params,
            "context": self.context or {},
            "metadata": self.metadata or {}
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ToolInput':
        """从字典创建实例"""
        return cls(
            query=data.get('query', ''),
            params=data.get('params', {}),
            context=data.get('context'),
            metadata=data.get('metadata')
        )


@dataclass
class ToolOutput:
    """
    统一工具输出 Schema

    Attributes:
        status: 执行状态 (success/error/warning)
        data: 主要数据内容
        error_message: 错误信息（如果有）
        warning_message: 警告信息（如果有）
        metadata: 元数据（执行时间、记录数等）
    """
    status: str = "success"
    data: Any = None
    error_message: Optional[str] = None
    warning_message: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        output = {
            "status": self.status,
            "data": self.data,
            "metadata": self.metadata
        }

        # 只在有错误时添加错误信息
        if self.error_message:
            output["error_message"] = self.error_message

        # 只在有警告时添加警告信息
        if self.warning_message:
            output["warning_message"] = self.warning_message

        return output

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ToolOutput':
        """从字典创建实例"""
        return cls(
            status=data.get('status', 'success'),
            data=data.get('data'),
            error_message=data.get('error_message'),
            warning_message=data.get('warning_message'),
            metadata=data.get('metadata', {})
        )


@dataclass
class ToolDefinition:
    """
    工具元数据定义

    Attributes:
        name: 工具名称
        description: 工具描述
        version: 工具版本
        author: 工具作者
        category: 工具分类 (data_collection/data_analysis/risk_assessment/market_query/financial_report)
        input_schema: 输入参数 Schema 描述
        output_schema: 输出结果 Schema 描述
        examples: 使用示例
        dependencies: 依赖项
        timeout: 超时时间（秒）
        retry_config: 重试配置
    """
    name: str
    description: str
    version: str = "1.0.0"
    author: str = "WealthAgents Team"
    category: str = "general"
    input_schema: Dict[str, Any] = field(default_factory=dict)
    output_schema: Dict[str, Any] = field(default_factory=dict)
    examples: List[Dict[str, Any]] = field(default_factory=list)
    dependencies: List[str] = field(default_factory=list)
    timeout: int = 30
    retry_config: Dict[str, Any] = field(default_factory=lambda: {
        "max_retries": 3,
        "retry_delay": 1,
        "backoff_factor": 2
    })

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            "name": self.name,
            "description": self.description,
            "version": self.version,
            "author": self.author,
            "category": self.category,
            "input_schema": self.input_schema,
            "output_schema": self.output_schema,
            "examples": self.examples,
            "dependencies": self.dependencies,
            "timeout": self.timeout,
            "retry_config": self.retry_config
        }


@dataclass
class ToolCallRecord:
    """
    工具调用记录

    Attributes:
        tool_name: 工具名称
        input_data: 输入数据
        output_data: 输出数据
        start_time: 开始时间
        end_time: 结束时间
        duration: 执行时长（秒）
        status: 执行状态
        error_info: 错误信息（如果有）
    """
    tool_name: str
    input_data: ToolInput
    output_data: ToolOutput
    start_time: datetime
    end_time: Optional[datetime] = None
    duration: Optional[float] = None
    status: str = "running"
    error_info: Optional[str] = None

    def complete(self, success: bool = True):
        """标记调用完成"""
        self.end_time = datetime.now()
        self.duration = (self.end_time - self.start_time).total_seconds()
        self.status = "success" if success else "failed"

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            "tool_name": self.tool_name,
            "input_data": self.input_data.to_dict(),
            "output_data": self.output_data.to_dict(),
            "start_time": self.start_time.isoformat(),
            "end_time": self.end_time.isoformat() if self.end_time else None,
            "duration": self.duration,
            "status": self.status,
            "error_info": self.error_info
        }


class StandardizedToolResponse:
    """
    标准化工具响应构建器

    提供便捷的响应构建方法，确保所有工具返回统一格式
    """

    @staticmethod
    def success(data: Any, **metadata) -> Dict[str, Any]:
        """
        构建成功响应

        Args:
            data: 返回的数据
            **metadata: 额外的元数据

        Returns:
            标准化的成功响应字典
        """
        output = ToolOutput(
            status="success",
            data=data,
            metadata=metadata
        )
        return output.to_dict()

    @staticmethod
    def error(message: str, error_code: str = "TOOL_ERROR", **metadata) -> Dict[str, Any]:
        """
        构建错误响应

        Args:
            message: 错误信息
            error_code: 错误代码
            **metadata: 额外的元数据

        Returns:
            标准化的错误响应字典
        """
        output = ToolOutput(
            status="error",
            data=None,
            error_message=message,
            metadata={**metadata, "error_code": error_code}
        )
        return output.to_dict()

    @staticmethod
    def warning(data: Any, message: str, **metadata) -> Dict[str, Any]:
        """
        构建警告响应

        Args:
            data: 返回的数据（可能不完整）
            message: 警告信息
            **metadata: 额外的元数据

        Returns:
            标准化的警告响应字典
        """
        output = ToolOutput(
            status="warning",
            data=data,
            warning_message=message,
            metadata=metadata
        )
        return output.to_dict()

    @staticmethod
    def empty(message: str = "未找到相关数据") -> Dict[str, Any]:
        """
        构建空数据响应

        Args:
            message: 提示信息

        Returns:
            标准化的空数据响应字典
        """
        return StandardizedToolResponse.warning(
            data=[],
            message=message
        )


# 统一的错误代码定义
class ErrorCodes:
    """通用错误代码"""
    SUCCESS = "SUCCESS"
    TOOL_NOT_FOUND = "TOOL_NOT_FOUND"
    INVALID_INPUT = "INVALID_INPUT"
    EXECUTION_ERROR = "EXECUTION_ERROR"
    TIMEOUT_ERROR = "TIMEOUT_ERROR"
    DEPENDENCY_ERROR = "DEPENDENCY_ERROR"
    CONFIGURATION_ERROR = "CONFIGURATION_ERROR"
    DATA_NOT_FOUND = "DATA_NOT_FOUND"
    PERMISSION_DENIED = "PERMISSION_DENIED"
    RATE_LIMIT_EXCEEDED = "RATE_LIMIT_EXCEEDED"
    INTERNAL_ERROR = "INTERNAL_ERROR"


# 工具分类枚举
class ToolCategory:
    """工具分类常量"""
    DATA_COLLECTION = "data_collection"  # 数据采集
    DATA_ANALYSIS = "data_analysis"      # 数据分析
    RISK_ASSESSMENT = "risk_assessment"  # 风险评估
    MARKET_QUERY = "market_query"        # 行情查询
    FINANCIAL_REPORT = "financial_report"  # 财报查询
    TECHNICAL_ANALYSIS = "technical_analysis"  # 技术分析
    FUNDAMENTAL_ANALYSIS = "fundamental_analysis"  # 基本面分析
    GENERAL = "general"  # 通用工具


# 示例：标准的工具输入输出格式示例
EXAMPLE_TOOL_USAGE = {
    "input_example": {
        "query": "贵州茅台 2023 年财报",
        "params": {
            "year": 2023,
            "report_type": "annual",
            "include_charts": True
        },
        "context": {
            "session_id": "abc123",
            "user_preferences": {"language": "zh-CN"}
        }
    },
    "output_example": {
        "status": "success",
        "data": {
            "company_name": "贵州茅台",
            "revenue": 12345678900,
            "net_profit": 5678901234,
            "growth_rate": 0.15
        },
        "metadata": {
            "execution_time": 2.5,
            "data_source": "上交所公告",
            "record_count": 1,
            "timestamp": 1234567890.123
        }
    }
}


def validate_tool_response(response: Dict[str, Any]) -> bool:
    """
    验证工具响应是否符合标准格式

    Args:
        response: 待验证的响应字典

    Returns:
        是否符合标准格式
    """
    # 必须包含 status 字段
    if "status" not in response:
        return False

    # status 必须是预定义的值
    valid_statuses = ["success", "error", "warning"]
    if response["status"] not in valid_statuses:
        return False

    # 如果是 error 状态，必须有 error_message
    if response["status"] == "error" and "error_message" not in response:
        return False

    # 应该有 data 字段（可以是 None）
    if "data" not in response:
        return False

    # 应该有 metadata 字段
    if "metadata" not in response:
        return False

    return True


def normalize_legacy_response(response: Dict[str, Any]) -> Dict[str, Any]:
    """
    将旧格式的工具响应转换为新标准格式

    Args:
        response: 旧格式的响应字典

    Returns:
        新标准化的响应字典
    """
    # 如果已经是标准格式，直接返回
    if validate_tool_response(response):
        return response

    # 处理旧格式
    normalized = {
        "status": "success",
        "data": None,
        "metadata": {}
    }

    # 提取主要数据
    if "data" in response:
        normalized["data"] = response["data"]
    elif "parsed_data" in response:
        normalized["data"] = response["parsed_data"]
    elif "result" in response:
        normalized["data"] = response["result"]
    elif "content" in response:
        normalized["data"] = response["content"]

    # 提取错误信息
    if response.get("status") == "error" or "error_message" in response:
        normalized["status"] = "error"
        normalized["error_message"] = response.get("error_message", "未知错误")

    # 提取警告信息
    if response.get("status") == "warning" or "warning_message" in response:
        normalized["status"] = "warning"
        normalized["warning_message"] = response.get("warning_message", "")

    # 迁移元数据
    metadata_fields = ["execution_time", "timestamp", "count", "record_count",
                       "source", "query", "tool_name", "task_id"]
    for field in metadata_fields:
        if field in response:
            normalized["metadata"][field] = response[field]

    return normalized
