"""
财富Agent - 智能投研分析平台
错误处理工具模块
"""
from typing import Dict, Any, Optional
import time


# 标准化错误码定义
class ErrorCodes:
    """标准化错误码类"""
    # 通用错误
    SUCCESS = 0
    GENERIC_ERROR = 1000
    INVALID_PARAMETER = 1001
    NOT_FOUND = 1002
    UNAUTHORIZED = 1003
    FORBIDDEN = 1004
    
    # 工具相关错误
    TOOL_NOT_FOUND = 2000
    TOOL_EXECUTION_ERROR = 2001
    TOOL_INIT_ERROR = 2002
    
    # 数据相关错误
    DATA_PARSE_ERROR = 3000
    DATA_NOT_AVAILABLE = 3001
    DATA_VALIDATION_ERROR = 3002
    
    # 网络相关错误
    NETWORK_ERROR = 4000
    API_CALL_ERROR = 4001
    
    # 知识库相关错误
    KB_SEARCH_ERROR = 5000
    KB_INDEX_ERROR = 5001
    KB_NOT_FOUND = 5002
    
    # Agent流程相关错误
    PLANNING_ERROR = 6000
    EXECUTION_ERROR = 6001
    REFLECTION_ERROR = 6002
    CONTEXT_ERROR = 6003


# 错误码到消息的映射
ERROR_MESSAGES = {
    # 通用错误
    ErrorCodes.SUCCESS: "操作成功",
    ErrorCodes.GENERIC_ERROR: "操作失败",
    ErrorCodes.INVALID_PARAMETER: "无效的参数",
    ErrorCodes.NOT_FOUND: "资源未找到",
    ErrorCodes.UNAUTHORIZED: "未授权的访问",
    ErrorCodes.FORBIDDEN: "禁止访问",
    
    # 工具相关错误
    ErrorCodes.TOOL_NOT_FOUND: "工具未找到",
    ErrorCodes.TOOL_EXECUTION_ERROR: "工具执行失败",
    ErrorCodes.TOOL_INIT_ERROR: "工具初始化失败",
    
    # 数据相关错误
    ErrorCodes.DATA_PARSE_ERROR: "数据解析失败",
    ErrorCodes.DATA_NOT_AVAILABLE: "数据不可用",
    ErrorCodes.DATA_VALIDATION_ERROR: "数据验证失败",
    
    # 网络相关错误
    ErrorCodes.NETWORK_ERROR: "网络连接失败",
    ErrorCodes.API_CALL_ERROR: "API调用失败",
    
    # 知识库相关错误
    ErrorCodes.KB_SEARCH_ERROR: "知识库检索失败",
    ErrorCodes.KB_INDEX_ERROR: "知识库索引错误",
    ErrorCodes.KB_NOT_FOUND: "知识库未找到",
    
    # Agent流程相关错误
    ErrorCodes.PLANNING_ERROR: "任务规划失败",
    ErrorCodes.EXECUTION_ERROR: "任务执行失败",
    ErrorCodes.REFLECTION_ERROR: "反思分析失败",
    ErrorCodes.CONTEXT_ERROR: "上下文处理错误",
}


class ErrorHandler:
    """统一错误处理类"""
    
    @staticmethod
    def create_error_response(
            error_code: int,
            error_message: Optional[str] = None,
            additional_info: Optional[Dict[str, Any]] = None,
            **kwargs
    ) -> Dict[str, Any]:
        """
        创建标准化的错误响应

        Args:
            error_code: 错误码
            error_message: 错误消息，如果不提供则使用默认消息
            additional_info: 额外的错误信息
            **kwargs: 其他参数

        Returns:
            标准化的错误响应
        """
        # 获取默认错误消息
        default_message = ERROR_MESSAGES.get(error_code, "未知错误")
        
        # 构建基本错误响应
        error_response = {
            "status": "error",
            "error_code": error_code,
            "error_message": error_message or default_message,
            "timestamp": time.time(),
        }
        
        # 添加额外信息
        if additional_info:
            error_response.update(additional_info)
        
        # 添加其他参数
        if kwargs:
            error_response.update(kwargs)
        
        return error_response
    
    @staticmethod
    def create_success_response(
            data: Optional[Dict[str, Any]] = None,
            message: str = "操作成功",
            **kwargs
    ) -> Dict[str, Any]:
        """
        创建标准化的成功响应

        Args:
            data: 响应数据
            message: 成功消息
            **kwargs: 其他参数

        Returns:
            标准化的成功响应
        """
        success_response = {
            "status": "success",
            "error_code": ErrorCodes.SUCCESS,
            "message": message,
            "timestamp": time.time(),
        }
        
        if data:
            success_response["data"] = data
        
        if kwargs:
            success_response.update(kwargs)
        
        return success_response
    
    @staticmethod
    def create_warning_response(
            message: str = "操作有警告",
            data: Optional[Dict[str, Any]] = None,
            **kwargs
    ) -> Dict[str, Any]:
        """
        创建标准化的警告响应

        Args:
            message: 警告消息
            data: 响应数据
            **kwargs: 其他参数

        Returns:
            标准化的警告响应
        """
        warning_response = {
            "status": "warning",
            "error_code": ErrorCodes.SUCCESS,  # 警告不视为错误
            "message": message,
            "timestamp": time.time(),
        }
        
        if data:
            warning_response["data"] = data
        
        if kwargs:
            warning_response.update(kwargs)
        
        return warning_response
    
    @staticmethod
    def get_error_message(error_code: int) -> str:
        """
        根据错误码获取错误消息

        Args:
            error_code: 错误码

        Returns:
            错误消息
        """
        return ERROR_MESSAGES.get(error_code, "未知错误")


# 便捷函数
def create_error(error_code: int, 
                error_message: Optional[str] = None, 
                additional_info: Optional[Dict[str, Any]] = None, 
                **kwargs) -> Dict[str, Any]:
    """创建错误响应的便捷函数"""
    return ErrorHandler.create_error_response(error_code, error_message, additional_info, **kwargs)


def create_success(data: Optional[Dict[str, Any]] = None, 
                   message: str = "操作成功", 
                   **kwargs) -> Dict[str, Any]:
    """创建成功响应的便捷函数"""
    return ErrorHandler.create_success_response(data, message, **kwargs)


def create_warning(message: str = "操作有警告", 
                   data: Optional[Dict[str, Any]] = None, 
                   **kwargs) -> Dict[str, Any]:
    """创建警告响应的便捷函数"""
    return ErrorHandler.create_warning_response(message, data, **kwargs)