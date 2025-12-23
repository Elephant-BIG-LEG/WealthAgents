"""
财富Agent - 智能投研分析平台
私人Agent模块 - 数据解析工具
"""
from typing import Dict, Any, List
from ...agentWorker.data_parse_and_process import LangChainHelperWithIntegration
import logging


class DataParsingTool:
    """数据解析工具类"""

    def __init__(self):
        self.logger = logging.getLogger(__name__)
        try:
            self.parser = LangChainHelperWithIntegration()
        except Exception as e:
            self.logger.error(f"初始化LangChainHelper失败: {e}")
            self.parser = None

    def parse_financial_text(self, text: str, **kwargs) -> Dict[str, Any]:
        """
        解析金融文本数据

        Args:
            text: 要解析的文本
            **kwargs: 其他参数

        Returns:
            解析结果
        """
        try:
            if self.parser is None:
                return {
                    "status": "error",
                    "error_message": "LangChainHelper未正确初始化",
                    "timestamp": __import__('time').time()
                }

            # 使用LangChainHelper解析文本 - 使用正确的方法名
            result = self.parser.get_response(text)

            return {
                "status": "success",
                "parsed_data": result,
                "original_text_length": len(text),
                "timestamp": __import__('time').time()
            }

        except Exception as e:
            self.logger.error(f"数据解析失败: {str(e)}")
            return {
                "status": "error",
                "error_message": str(e),
                "timestamp": __import__('time').time()
            }


# 便捷函数，供Executor调用
def data_parsing_tool(text: str = "", **kwargs) -> Dict[str, Any]:
    """
    数据解析工具便捷函数

    Args:
        text: 要解析的文本
        **kwargs: 其他参数

    Returns:
        解析结果
    """
    # 优先使用参数中的text，如果不存在则尝试从kwargs中获取
    text_to_parse = text if text else kwargs.get(
        'text', kwargs.get('content', ''))

    # 如果text为空，尝试从dependency_results中获取
    if not text_to_parse:
        dependency_results = kwargs.get('dependency_results', {})
        if dependency_results:
            # 获取第一个依赖结果的数据
            first_result = next(iter(dependency_results.values()), {})
            if isinstance(first_result, dict):
                # 尝试从结果中提取文本数据
                text_to_parse = first_result.get('data', '')
                if not text_to_parse and 'result' in first_result:
                    text_to_parse = first_result['result']
                if not text_to_parse and 'summary' in first_result:
                    text_to_parse = first_result['summary']
                # 如果data是列表，转换为字符串
                if not text_to_parse and isinstance(first_result.get('data'), list):
                    text_to_parse = ' '.join(
                        [str(item) for item in first_result['data'] if item])

    tool = DataParsingTool()
    return tool.parse_financial_text(text_to_parse, **kwargs)
