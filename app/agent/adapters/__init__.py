"""
财富 Agent - 智能投研分析平台
Adapter 适配器层模块
负责工具能力抽象、数据格式转换、协议适配
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional, Union
import logging


class BaseToolAdapter(ABC):
    """
    工具适配器基类

    所有适配器必须继承此类并实现抽象方法

    Attributes:
        name: 适配器名称
        description: 适配器描述
        version: 版本号
        supported_protocols: 支持的协议列表
    """

    name: str = "base_adapter"
    description: str = "基础适配器"
    version: str = "1.0.0"
    supported_protocols: List[str] = []

    def __init__(self):
        """初始化适配器"""
        self.logger = logging.getLogger(
            f"{self.__class__.__module__}.{self.__class__.__name__}")

    @abstractmethod
    def connect(self, **kwargs) -> bool:
        """
        建立连接

        Args:
            **kwargs: 连接参数

        Returns:
            是否连接成功
        """
        pass

    @abstractmethod
    def disconnect(self):
        """断开连接"""
        pass

    @abstractmethod
    def fetch_data(self, query: str, **params) -> Dict[str, Any]:
        """
        获取数据

        Args:
            query: 查询关键词
            **params: 其他参数

        Returns:
            获取的数据
        """
        pass

    @abstractmethod
    def transform_data(self, raw_data: Any) -> Dict[str, Any]:
        """
        转换数据格式为标准格式

        Args:
            raw_data: 原始数据

        Returns:
            标准化后的数据
        """
        pass

    def validate_connection(self) -> bool:
        """
        验证连接是否有效

        Returns:
            连接是否有效
        """
        raise NotImplementedError("子类必须实现此方法")

    def get_status(self) -> Dict[str, Any]:
        """
        获取适配器状态信息

        Returns:
            状态信息字典
        """
        return {
            "name": self.name,
            "version": self.version,
            "connected": self.validate_connection(),
            "supported_protocols": self.supported_protocols
        }

    def _log_operation(self, operation: str, details: str = ""):
        """
        记录操作日志

        Args:
            operation: 操作名称
            details: 详细信息
        """
        self.logger.info(f"[{self.name}] {operation}: {details}")
