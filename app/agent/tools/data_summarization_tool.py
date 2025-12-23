"""
财富Agent - 智能投研分析平台
私人Agent模块 - 数据汇总工具
"""
from typing import Dict, Any, List
from ...agentWorker.data_summarizer import LangChainHelperWithSummary
import logging


class DataSummarizationTool:
    """数据汇总工具类"""

    def __init__(self):
        self.logger = logging.getLogger(__name__)
        try:
            self.summarizer = LangChainHelperWithSummary()
        except Exception as e:
            self.logger.error(f"初始化LangChainHelperWithSummary失败: {e}")
            self.summarizer = None

    def summarize_financial_content(self, content: str, **kwargs) -> Dict[str, Any]:
        """
        汇总金融内容

        Args:
            content: 要汇总的内容
            **kwargs: 其他参数

        Returns:
            汇总结果
        """
        try:
            if self.summarizer is None:
                return {
                    "status": "error",
                    "error_message": "LangChainHelperWithSummary未正确初始化",
                    "timestamp": __import__('time').time()
                }

            # 使用LangChainHelper汇总内容 - 使用正确的方法名
            result = self.summarizer.get_response(content)

            return {
                "status": "success",
                "summary": result,
                "original_content_length": len(content),
                "summary_length": len(result) if result else 0,
                "timestamp": __import__('time').time()
            }

        except Exception as e:
            self.logger.error(f"数据汇总失败: {str(e)}")
            return {
                "status": "error",
                "error_message": str(e),
                "timestamp": __import__('time').time()
            }


# 便捷函数，供Executor调用
def data_summarization_tool(content: str = "", **kwargs) -> Dict[str, Any]:
    """
    数据汇总工具便捷函数

    Args:
        content: 要汇总的内容
        **kwargs: 其他参数

    Returns:
        汇总结果
    """
    # 优先使用参数中的content，如果不存在则尝试从kwargs中获取
    content_to_summarize = content if content else kwargs.get(
        'content', kwargs.get('text', ''))

    # 如果content为空，尝试从dependency_results中获取
    if not content_to_summarize:
        dependency_results = kwargs.get('dependency_results', {})
        if dependency_results:
            # 获取第一个依赖结果的数据
            first_result = next(iter(dependency_results.values()), {})
            if isinstance(first_result, dict):
                # 尝试从结果中提取内容数据
                content_to_summarize = first_result.get('data', '')
                if not content_to_summarize and 'result' in first_result:
                    content_to_summarize = first_result['result']
                if not content_to_summarize and 'parsed_data' in first_result:
                    content_to_summarize = first_result['parsed_data']
                # 如果data是列表，转换为字符串
                if not content_to_summarize and isinstance(first_result.get('data'), list):
                    content_to_summarize = ' '.join(
                        [str(item) for item in first_result['data'] if item])

    tool = DataSummarizationTool()
    return tool.summarize_financial_content(content_to_summarize, **kwargs)
