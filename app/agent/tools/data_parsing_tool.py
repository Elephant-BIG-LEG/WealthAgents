"""
财富Agent - 智能投研分析平台
私人Agent模块 - 数据解析工具
"""
from typing import Dict, Any, List, Tuple
from ...agentWorker.data_parse_and_process import LangChainHelperWithIntegration
import logging
import time


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
                    "timestamp": time.time()
                }

            # 检查文本内容
            if not text or (isinstance(text, str) and text.strip() == ""):
                return {
                    "status": "warning",
                    "parsed_data": {"title": "", "summary": "未获取到相关数据，无法进行解析"},
                    "original_text_length": 0,
                    "timestamp": time.time()
                }

            # 使用LangChainHelper解析文本 - 使用正确的方法名
            result = self.parser.get_response(text)

            return {
                "status": "success",
                "parsed_data": result,
                "original_text_length": len(text) if isinstance(text, str) else 0,
                "timestamp": time.time()
            }

        except Exception as e:
            self.logger.error(f"数据解析失败: {str(e)}")
            # 返回一个有意义的错误响应
            return {
                "status": "error",
                "error_message": str(e),
                "parsed_data": {"title": "", "summary": f"解析过程中出现错误: {str(e)}"},
                "timestamp": time.time()
            }
            
    def parse_knowledge_base_results(self, search_results: List[Any], **kwargs) -> Dict[str, Any]:
        """
        专门解析知识库检索结果的方法

        Args:
            search_results: 知识库检索结果列表
            **kwargs: 其他参数

        Returns:
            解析结果
        """
        try:
            if self.parser is None:
                return {
                    "status": "error",
                    "error_message": "LangChainHelper未正确初始化",
                    "timestamp": time.time()
                }

            # 检查搜索结果
            if not search_results or len(search_results) == 0:
                return {
                    "status": "warning",
                    "parsed_data": {"title": "", "summary": "未获取到相关知识库检索结果，无法进行解析"},
                    "search_results_count": 0,
                    "timestamp": time.time()
                }

            # 处理搜索结果，提取结构化信息
            processed_results = []
            all_text_content = []
            max_results = kwargs.get('max_results', 10)  # 默认最多处理10个结果
            min_similarity = kwargs.get('min_similarity', 0.5)  # 默认相似度阈值

            for i, result in enumerate(search_results):
                if i >= max_results:
                    break  # 达到最大处理数量
                
                result_dict = {}
                
                # 处理不同格式的检索结果
                if isinstance(result, tuple):
                    # 格式：(text, similarity, meta)
                    if len(result) >= 1:
                        result_dict['text'] = str(result[0])
                        all_text_content.append(str(result[0]))
                    if len(result) >= 2:
                        result_dict['similarity'] = float(result[1])
                    if len(result) >= 3:
                        result_dict['meta'] = result[2] if isinstance(result[2], dict) else {}
                elif isinstance(result, dict):
                    # 格式：{'text': '', 'similarity': 0.0, 'meta': {}}
                    result_dict['text'] = str(result.get('text', ''))
                    if result_dict['text']:
                        all_text_content.append(result_dict['text'])
                    result_dict['similarity'] = float(result.get('similarity', 0.0))
                    result_dict['meta'] = result.get('meta', {})
                else:
                    # 其他格式，转换为字符串
                    result_dict['text'] = str(result)
                    all_text_content.append(str(result))
                    result_dict['similarity'] = 0.0
                    result_dict['meta'] = {}
                
                # 添加结果索引
                result_dict['index'] = i + 1
                processed_results.append(result_dict)

            # 按相似度排序结果（如果有相似度信息）
            processed_results.sort(key=lambda x: x.get('similarity', 0.0), reverse=True)
            
            # 过滤低相似度结果
            filtered_results = [r for r in processed_results if r.get('similarity', 0.0) >= min_similarity]
            
            # 如果过滤后没有结果，至少保留一个
            if not filtered_results and processed_results:
                filtered_results = [processed_results[0]]
            
            # 准备要解析的文本内容
            text_to_parse = '\n\n---\n\n'.join([f"结果 {r['index']} (相似度: {r.get('similarity', 0.0):.2f}):\n{r['text']}" for r in filtered_results])
            
            # 添加查询上下文（如果有）
            query_context = kwargs.get('query_context', '')
            if query_context:
                text_to_parse = f"查询: {query_context}\n\n{text_to_parse}"
            
            # 使用LangChainHelper解析文本
            parsed_data = self.parser.get_response(text_to_parse)
            
            return {
                "status": "success",
                "parsed_data": parsed_data,
                "search_results_count": len(search_results),
                "processed_results_count": len(processed_results),
                "filtered_results_count": len(filtered_results),
                "similarity_threshold": min_similarity,
                "max_results_processed": max_results,
                "timestamp": time.time()
            }

        except Exception as e:
            self.logger.error(f"知识库检索结果解析失败: {str(e)}")
            return {
                "status": "error",
                "error_message": str(e),
                "parsed_data": {"title": "", "summary": f"解析知识库检索结果时出现错误: {str(e)}"},
                "search_results_count": len(search_results) if search_results else 0,
                "timestamp": time.time()
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
    # 添加调试信息
    print(f"data_parsing_tool调用参数:")
    print(f"  text: '{text}'")
    print(f"  kwargs包含的键: {list(kwargs.keys())}")
    print(f"  search_results存在: {'search_results' in kwargs}")
    
    if 'search_results' in kwargs:
        search_results = kwargs['search_results']
        print(f"  search_results类型: {type(search_results)}")
        print(f"  search_results长度: {len(search_results)}")
        if search_results:
            print(f"  search_results[0]: {search_results[0]}")
    
    # 优先使用参数中的text，如果不存在则尝试从kwargs中获取
    text_to_parse = text if text else kwargs.get(
        'text', kwargs.get('content', ''))
    
    print(f"  text_to_parse: '{text_to_parse}'")

    # 尝试从search_results参数获取知识库检索结果
    if not text_to_parse and 'search_results' in kwargs:
        search_results = kwargs.pop('search_results', [])  # 从kwargs中移除search_results，避免重复传递
        if search_results:
            print(f"  调用parse_knowledge_base_results")
            tool = DataParsingTool()
            # 使用专门的知识库结果解析方法
            return tool.parse_knowledge_base_results(search_results, **kwargs)
    
    print(f"  调用parse_financial_text")
    tool = DataParsingTool()
    return tool.parse_financial_text(text_to_parse, **kwargs)

# 知识库检索结果解析便捷函数
def knowledge_base_parser(search_results: List[Any], **kwargs) -> Dict[str, Any]:
    """
    知识库检索结果解析便捷函数

    Args:
        search_results: 知识库检索结果列表
        **kwargs: 其他参数

    Returns:
        解析结果
    """
    tool = DataParsingTool()
    return tool.parse_knowledge_base_results(search_results, **kwargs)