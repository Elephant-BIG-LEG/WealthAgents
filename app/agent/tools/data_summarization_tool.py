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

            # 检查内容
            if not content or (isinstance(content, str) and content.strip() == ""):
                return {
                    "status": "warning",
                    "summary": "未获取到相关数据，无法进行汇总",
                    "original_content_length": 0,
                    "summary_length": 0,
                    "timestamp": __import__('time').time()
                }

            # 使用LangChainHelper汇总内容 - 使用正确的方法名
            result = self.summarizer.get_response(content)

            summary_text = str(result) if not isinstance(
                result, dict) else str(result)

            return {
                "status": "success",
                "summary": result,
                "original_content_length": len(content) if isinstance(content, str) else 0,
                "summary_length": len(summary_text),
                "timestamp": __import__('time').time()
            }

        except Exception as e:
            self.logger.error(f"数据汇总失败: {str(e)}")
            return {
                "status": "error",
                "error_message": str(e),
                "summary": {"date": "", "topic": "数据处理异常", "market_trend": f"汇总过程中出现错误: {str(e)}", "investment_advice": "", "hotspot_summary": ""},
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
                if 'data' in first_result and first_result['data']:
                    # 如果data是列表，将其转换为字符串
                    if isinstance(first_result['data'], list):
                        if len(first_result['data']) > 0:
                            # 尝试将列表中的数据转换为文本
                            if isinstance(first_result['data'][0], dict):
                                # 如果是字典列表，提取关键信息
                                text_items = []
                                for item in first_result['data']:
                                    if isinstance(item, dict):
                                        title = item.get('title', '')
                                        content_item = item.get(
                                            'content', item.get('summary', ''))
                                        if title or content_item:
                                            text_items.append(
                                                f"标题: {title}\n内容: {content_item}")
                                content_to_summarize = '\n'.join(text_items)
                            else:
                                content_to_summarize = str(
                                    first_result['data'])
                        else:
                            # 如果列表为空，使用查询关键词生成提示
                            query = first_result.get('query', '未知查询')
                            content_to_summarize = f"在 '{query}' 方面未找到相关数据，请尝试其他关键词或稍后重试。"
                    else:
                        content_to_summarize = str(first_result['data'])
                elif 'result' in first_result:
                    # 如果result是字典，需要先转换为字符串
                    result_val = first_result['result']
                    if isinstance(result_val, dict):
                        content_to_summarize = str(result_val)
                    else:
                        content_to_summarize = str(result_val)
                elif 'parsed_data' in first_result:
                    parsed_val = first_result['parsed_data']
                    if isinstance(parsed_val, dict):
                        content_to_summarize = str(parsed_val)
                    else:
                        content_to_summarize = str(parsed_val)
                elif first_result.get('status') == 'success' and first_result.get('count', 0) == 0:
                    # 如果采集结果为空，生成有意义的响应
                    query = first_result.get('query', '未知查询')
                    content_to_summarize = f"在 '{query}' 方面未找到相关数据，请尝试其他关键词或稍后重试。"
                else:
                    # 如果依赖结果不是预期格式，使用查询关键词
                    query = first_result.get('query', '未知查询') if isinstance(
                        first_result, dict) else '未知查询'
                    content_to_summarize = f"无法从之前的步骤中获取有效数据，查询关键词: {query}"

    tool = DataSummarizationTool()
    return tool.summarize_financial_content(content_to_summarize, **kwargs)
