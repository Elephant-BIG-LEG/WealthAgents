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

            # 检查文本内容
            if not text or (isinstance(text, str) and text.strip() == ""):
                return {
                    "status": "warning",
                    "parsed_data": {"title": "", "summary": "未获取到相关数据，无法进行解析"},
                    "original_text_length": 0,
                    "timestamp": __import__('time').time()
                }

            # 使用LangChainHelper解析文本 - 使用正确的方法名
            result = self.parser.get_response(text)

            return {
                "status": "success",
                "parsed_data": result,
                "original_text_length": len(text) if isinstance(text, str) else 0,
                "timestamp": __import__('time').time()
            }

        except Exception as e:
            self.logger.error(f"数据解析失败: {str(e)}")
            # 返回一个有意义的错误响应
            return {
                "status": "error",
                "error_message": str(e),
                "parsed_data": {"title": "", "summary": f"解析过程中出现错误: {str(e)}"},
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

    # 尝试从search_results参数获取知识库检索结果
    if not text_to_parse and 'search_results' in kwargs:
        search_results = kwargs.get('search_results', [])
        if search_results:
            # 提取检索结果中的文本内容
            text_items = []
            for result in search_results:
                if isinstance(result, tuple) and len(result) > 0:
                    # 知识库结果通常是(text, similarity, meta)格式
                    text_items.append(str(result[0]))
                elif isinstance(result, dict) and 'text' in result:
                    text_items.append(result['text'])
                else:
                    text_items.append(str(result))
            text_to_parse = '\n'.join(text_items)

    # 如果text为空，尝试从dependency_results中获取
    if not text_to_parse:
        dependency_results = kwargs.get('dependency_results', {})
        if dependency_results:
            # 获取第一个依赖结果的数据
            first_result = next(iter(dependency_results.values()), {})
            if isinstance(first_result, dict):
                # 尝试从结果中提取文本数据
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
                                        content = item.get(
                                            'content', item.get('summary', ''))
                                        if title or content:
                                            text_items.append(
                                                f"标题: {title}\n内容: {content}")
                                text_to_parse = '\n'.join(text_items)
                            else:
                                text_to_parse = str(first_result['data'])
                        else:
                            # 如果列表为空，使用查询关键词生成提示
                            query = first_result.get('query', '未知查询')
                            text_to_parse = f"在 '{query}' 方面未找到相关数据，请尝试其他关键词或稍后重试。"
                    else:
                        text_to_parse = str(first_result['data'])
                elif 'result' in first_result:
                    # 如果result是字典，需要先转换为字符串
                    result_val = first_result['result']
                    if isinstance(result_val, dict):
                        text_to_parse = str(result_val)
                    else:
                        text_to_parse = str(result_val)
                elif 'summary' in first_result:
                    summary_val = first_result['summary']
                    if isinstance(summary_val, dict):
                        text_to_parse = str(summary_val)
                    else:
                        text_to_parse = str(summary_val)
                elif first_result.get('status') == 'success' and first_result.get('count', 0) == 0:
                    # 如果采集结果为空，生成有意义的响应
                    query = first_result.get('query', '未知查询')
                    text_to_parse = f"在 '{query}' 方面未找到相关数据，请尝试其他关键词或稍后重试。"
                else:
                    # 如果依赖结果不是预期格式，使用查询关键词
                    query = first_result.get('query', '未知查询') if isinstance(
                        first_result, dict) else '未知查询'
                    text_to_parse = f"无法从之前的步骤中获取有效数据，查询关键词: {query}"

    tool = DataParsingTool()
    return tool.parse_financial_text(text_to_parse, **kwargs)

