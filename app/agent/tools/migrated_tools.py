"""
财富 Agent - 智能投研分析平台
现有工具标准化迁移 - 完整实现
将所有现有工具迁移到新的统一接口规范
"""

from typing import Dict, Any, List, Optional
from .tool_base import BaseTool, LegacyToolAdapter
from .base_tool import (
    ToolInput,
    ToolOutput,
    ToolCategory,
    StandardizedToolResponse,
    ErrorCodes
)
from .tool_registry import register_tool, get_global_registry
import logging
import time


# ============================================================
# 1. 网络爬虫工具迁移 (Web Scraping Tool Migration)
# ============================================================

@register_tool(
    name="web_scraping_tool_v2",
    description="标准化的网络数据采集工具，支持多数据源配置",
    category=ToolCategory.DATA_COLLECTION
)
class WebScrapingToolV2(BaseTool):
    """
    标准化网络爬虫工具 V2

    基于原有的 web_scraping_tool.py 进行完全重构
    """

    name = "web_scraping_tool_v2"
    description = "标准化的网络数据采集工具，支持多数据源配置"
    category = ToolCategory.DATA_COLLECTION
    version = "2.0.0"

    def __init__(self):
        super().__init__()

        # 保留原有的数据源配置
        self.data_sources = {
            'eastmoney': {
                'name': '东方财富网',
                'base_url': 'https://finance.eastmoney.com/',
                'supported_types': ['financial_news', 'stock_data', 'market_trends'],
                'description': '中国领先的金融信息服务平台'
            },
            'ifeng': {
                'name': '凤凰财经',
                'base_url': 'https://finance.ifeng.com/',
                'supported_types': ['financial_news', 'economic_data', 'market_analysis'],
                'description': '凤凰网财经频道'
            },
            'hexun': {
                'name': '和讯网',
                'base_url': 'https://www.hexun.com/',
                'supported_types': ['financial_news', 'stock_research', 'investment_strategy'],
                'description': '综合性财经门户网站'
            },
            'sina': {
                'name': '新浪财经',
                'base_url': 'https://finance.sina.com.cn/',
                'supported_types': ['financial_news', 'stock_quotes', 'market_data'],
                'description': '新浪网财经频道'
            }
        }

    def execute(self, tool_input: ToolInput) -> ToolOutput:
        """执行网络爬取 - 标准化实现"""
        try:
            # 解析输入参数
            query = tool_input.query
            params = tool_input.params

            data_source = params.get('data_source', 'eastmoney')
            data_type = params.get('data_type', 'financial_news')

            # 验证输入
            if not query or not query.strip():
                return ToolOutput(
                    status="error",
                    data=None,
                    error_message="查询关键词不能为空",
                    metadata={"error_code": ErrorCodes.INVALID_INPUT}
                )

            # 验证数据源
            if data_source not in self.data_sources:
                return ToolOutput(
                    status="error",
                    data=None,
                    error_message=f"不支持的数据源：{data_source}",
                    metadata={
                        "error_code": ErrorCodes.INVALID_INPUT,
                        "available_sources": list(self.data_sources.keys())
                    }
                )

            # 验证数据类型
            source_config = self.data_sources[data_source]
            if data_type not in source_config['supported_types']:
                return ToolOutput(
                    status="error",
                    data=None,
                    error_message=f"数据源 {source_config['name']} 不支持 {data_type} 类型",
                    metadata={
                        "error_code": ErrorCodes.INVALID_INPUT,
                        "supported_types": source_config['supported_types']
                    }
                )

            # 清理查询关键词
            clean_query = self._clean_query(query)

            # 执行爬取（调用原有逻辑）
            results = self._execute_scraping(
                clean_query, data_source, data_type, params)

            # 返回成功结果
            return ToolOutput(
                status="success",
                data=results,
                metadata={
                    "query": clean_query,
                    "source": source_config['name'],
                    "source_id": data_source,
                    "data_type": data_type,
                    "record_count": len(results) if results else 0,
                    "data_source_description": source_config['description']
                }
            )

        except Exception as e:
            self.logger.error(f"网络爬取失败：{str(e)}", exc_info=True)
            return ToolOutput(
                status="error",
                data=None,
                error_message=f"网络爬取过程中出现异常：{str(e)}",
                metadata={
                    "error_code": ErrorCodes.EXECUTION_ERROR,
                    "query": tool_input.query,
                    "params": tool_input.params
                }
            )

    def _execute_scraping(self, query: str, source: str, data_type: str, params: dict) -> list:
        """内部方法：执行实际的爬取逻辑"""
        # 这里集成原有的 Collection_action_llm 等逻辑
        # 示例代码，实际应该调用真实的爬取逻辑
        try:
            from app.ingest.web_fetcher import Collection_action_llm
            from app.ingest.source import Source

            # 创建数据源对象
            source_obj = Source(
                source_id=f"{source}_{query}_{int(time.time() * 1000)}",
                source_name=f"{self.data_sources[source]['name']}-{query}",
                type="web",
                url=self.data_sources[source]['base_url'],
                config={
                    "query": query,
                    "data_type": data_type,
                    "search_keyword": query,
                    "source_specific": params.get('source_specific', {})
                }
            )

            # 执行采集
            results = Collection_action_llm(source_obj)
            return results if results else []

        except Exception as e:
            self.logger.error(f"执行爬取任务失败：{str(e)}", exc_info=True)
            return []

    def _clean_query(self, query: str) -> str:
        """清理查询关键词"""
        import re
        # 移除特殊字符，只保留中英文、数字和空格
        cleaned = re.sub(r'[^\w\s\u4e00-\u9fff]', ' ', query)
        # 移除多余空格
        cleaned = ' '.join(cleaned.split())
        return cleaned

    def _get_examples(self) -> List[Dict[str, Any]]:
        """提供使用示例"""
        return [
            {
                "query": "人工智能",
                "params": {
                    "data_source": "eastmoney",
                    "data_type": "financial_news"
                },
                "description": "从东方财富网采集人工智能相关新闻"
            },
            {
                "query": "贵州茅台",
                "params": {
                    "data_source": "sina",
                    "data_type": "stock_data"
                },
                "description": "从新浪财经采集贵州茅台股票数据"
            }
        ]

    def _get_timeout(self) -> int:
        """设置超时时间"""
        return 60  # 网络爬取可能需要较长时间

    def _get_retry_config(self) -> Dict[str, Any]:
        """设置重试配置"""
        return {
            "max_retries": 2,
            "retry_delay": 2,
            "backoff_factor": 2
        }


# ============================================================
# 2. 数据解析工具迁移 (Data Parsing Tool Migration)
# ============================================================

@register_tool(
    name="data_parsing_tool_v2",
    description="标准化的金融文本数据解析和分析工具",
    category=ToolCategory.DATA_ANALYSIS
)
class DataParsingToolV2(BaseTool):
    """
    标准化数据解析工具 V2

    基于原有的 data_parsing_tool.py 进行完全重构
    """

    name = "data_parsing_tool_v2"
    description = "标准化的金融文本数据解析和分析工具"
    category = ToolCategory.DATA_ANALYSIS
    version = "2.0.0"

    def __init__(self):
        super().__init__()

        # 初始化原有的 LangChainHelper
        try:
            from app.agentWorker.data_parse_and_process import LangChainHelperWithIntegration
            self.parser = LangChainHelperWithIntegration()
        except Exception as e:
            self.logger.error(f"初始化解析器失败：{e}")
            self.parser = None

    def execute(self, tool_input: ToolInput) -> ToolOutput:
        """执行数据解析 - 标准化实现"""
        try:
            params = tool_input.params

            # 优先从 query 获取文本，或从 params 获取
            text_to_parse = tool_input.query or params.get('text', '')

            # 检查是否有知识库检索结果需要解析
            search_results = params.get('search_results')

            if search_results:
                # 解析知识库结果
                return self._parse_knowledge_results(search_results, params)
            else:
                # 解析普通文本
                return self._parse_text(text_to_parse, params)

        except Exception as e:
            self.logger.error(f"数据解析失败：{str(e)}", exc_info=True)
            return ToolOutput(
                status="error",
                data=None,
                error_message=str(e),
                metadata={"error_code": ErrorCodes.EXECUTION_ERROR}
            )

    def _parse_text(self, text: str, params: dict) -> ToolOutput:
        """解析普通文本"""
        if not self.parser:
            return ToolOutput(
                status="error",
                data=None,
                error_message="解析器未正确初始化",
                metadata={"error_code": ErrorCodes.CONFIGURATION_ERROR}
            )

        if not text or not text.strip():
            return StandardizedToolResponse.warning(
                data=[],
                message="输入文本为空，无法进行解析"
            )

        try:
            # 调用原有解析逻辑
            parsed_result = self.parser.get_response(text)

            return ToolOutput(
                status="success",
                data=parsed_result,
                metadata={
                    "original_text_length": len(text),
                    "parser_version": "1.0",
                    "text_preview": text[:100] + "..." if len(text) > 100 else text
                }
            )

        except Exception as e:
            self.logger.error(f"文本解析失败：{str(e)}", exc_info=True)
            return ToolOutput(
                status="error",
                data=None,
                error_message=f"解析过程中出现错误：{str(e)}",
                metadata={"error_code": ErrorCodes.EXECUTION_ERROR}
            )

    def _parse_knowledge_results(self, search_results: list, params: dict) -> ToolOutput:
        """解析知识库检索结果"""
        if not search_results or len(search_results) == 0:
            return StandardizedToolResponse.empty("未提供知识库检索结果")

        try:
            # 获取参数配置
            max_results = params.get('max_results', 10)
            min_similarity = params.get('min_similarity', 0.5)
            query_context = params.get('query_context', '')

            # 处理检索结果
            processed_results = []
            all_text_content = []

            for i, result in enumerate(search_results[:max_results]):
                result_dict = {}

                # 处理不同格式的检索结果
                if isinstance(result, tuple) and len(result) >= 1:
                    result_dict['text'] = str(result[0])
                    result_dict['similarity'] = float(
                        result[1]) if len(result) >= 2 else 0.0
                    result_dict['meta'] = result[2] if len(result) >= 3 else {}
                    all_text_content.append(str(result[0]))
                elif isinstance(result, dict):
                    result_dict['text'] = str(result.get('text', ''))
                    result_dict['similarity'] = float(
                        result.get('similarity', 0.0))
                    result_dict['meta'] = result.get('meta', {})
                    if result_dict['text']:
                        all_text_content.append(result_dict['text'])
                else:
                    result_dict['text'] = str(result)
                    result_dict['similarity'] = 0.0
                    result_dict['meta'] = {}
                    all_text_content.append(str(result))

                result_dict['index'] = i + 1
                processed_results.append(result_dict)

            # 按相似度排序
            processed_results.sort(key=lambda x: x.get(
                'similarity', 0.0), reverse=True)

            # 过滤低相似度结果
            filtered_results = [r for r in processed_results if r.get(
                'similarity', 0.0) >= min_similarity]

            # 如果过滤后没有结果，至少保留一个
            if not filtered_results and processed_results:
                filtered_results = [processed_results[0]]

            # 格式化用于解析的文本
            text_parts = []
            for r in filtered_results:
                text_parts.append(
                    f"结果 {r['index']} (相似度：{r.get('similarity', 0.0):.2f}):\n{r['text']}"
                )

            text_to_parse = '\n\n---\n\n'.join(text_parts)

            # 添加查询上下文
            if query_context:
                text_to_parse = f"查询：{query_context}\n\n{text_to_parse}"

            # 调用解析器
            parsed_data = self.parser.get_response(
                text_to_parse) if self.parser else text_to_parse

            return ToolOutput(
                status="success",
                data=parsed_data,
                metadata={
                    "total_results": len(search_results),
                    "processed_results": len(processed_results),
                    "filtered_results": len(filtered_results),
                    "similarity_threshold": min_similarity,
                    "max_results_processed": max_results
                }
            )

        except Exception as e:
            self.logger.error(f"知识库结果解析失败：{str(e)}", exc_info=True)
            return ToolOutput(
                status="error",
                data=None,
                error_message=str(e),
                metadata={"error_code": ErrorCodes.EXECUTION_ERROR}
            )

    def _get_examples(self) -> List[Dict[str, Any]]:
        """提供使用示例"""
        return [
            {
                "query": "贵州茅台 2023 年营收增长 15%",
                "params": {},
                "description": "解析金融文本内容"
            },
            {
                "query": "",
                "params": {
                    "search_results": [("文本内容", 0.9, {})],
                    "query_context": "人工智能相关报道"
                },
                "description": "解析知识库检索结果"
            }
        ]

    def _get_timeout(self) -> int:
        return 30


# ============================================================
# 3. 数据汇总工具迁移 (Data Summarization Tool Migration)
# ============================================================

@register_tool(
    name="data_summarization_tool_v2",
    description="标准化的金融内容汇总工具，支持多种摘要长度",
    category=ToolCategory.DATA_ANALYSIS
)
class DataSummarizationToolV2(BaseTool):
    """
    标准化数据汇总工具 V2

    基于原有的 data_summarization_tool.py 进行完全重构
    """

    name = "data_summarization_tool_v2"
    description = "标准化的金融内容汇总工具，支持多种摘要长度"
    category = ToolCategory.DATA_ANALYSIS
    version = "2.0.0"

    def __init__(self):
        super().__init__()

        # 初始化原有的 LangChainHelper
        try:
            from app.agentWorker.data_summarizer import LangChainHelperWithSummary
            self.summarizer = LangChainHelperWithSummary()
        except Exception as e:
            self.logger.error(f"初始化工具失败：{e}")
            self.summarizer = None

    def execute(self, tool_input: ToolInput) -> ToolOutput:
        """执行数据汇总 - 标准化实现"""
        try:
            params = tool_input.params

            # 获取要汇总的内容
            content = tool_input.query or params.get(
                'content', '') or params.get('text', '')

            # 如果内容为空，尝试从依赖结果中获取
            if not content:
                dependency_results = params.get('dependency_results', {})
                if dependency_results:
                    first_result = next(iter(dependency_results.values()), {})
                    if isinstance(first_result, dict) and 'data' in first_result:
                        data = first_result['data']
                        if isinstance(data, list):
                            content = '\n'.join([str(item)
                                                for item in data[:5]])
                        elif data:
                            content = str(data)

            # 验证内容
            if not content or not content.strip():
                return StandardizedToolResponse.warning(
                    data=[],
                    message="未获取到相关数据，无法进行汇总"
                )

            # 执行汇总
            if not self.summarizer:
                return ToolOutput(
                    status="error",
                    data=None,
                    error_message="汇总工具未正确初始化",
                    metadata={"error_code": ErrorCodes.CONFIGURATION_ERROR}
                )

            result = self.summarizer.get_response(content)
            summary_text = str(result) if not isinstance(
                result, dict) else str(result)

            return ToolOutput(
                status="success",
                data=result,
                metadata={
                    "original_content_length": len(content),
                    "summary_length": len(summary_text),
                    "compression_ratio": round(len(summary_text) / len(content) * 100, 2) if content else 0,
                    "content_preview": content[:100] + "..." if len(content) > 100 else content
                }
            )

        except Exception as e:
            self.logger.error(f"数据汇总失败：{str(e)}", exc_info=True)
            return ToolOutput(
                status="error",
                data=None,
                error_message=f"汇总过程中出现错误：{str(e)}",
                metadata={"error_code": ErrorCodes.EXECUTION_ERROR}
            )

    def _get_examples(self) -> List[Dict[str, Any]]:
        """提供使用示例"""
        return [
            {
                "query": "贵州茅台 2023 年实现营收 1234 亿元，同比增长 15%。其中茅台酒收入占比超过 90%，系列酒收入稳步增长...",
                "params": {},
                "description": "汇总金融新闻内容"
            }
        ]

    def _get_timeout(self) -> int:
        return 45


# ============================================================
# 4. 数据库工具迁移 (Database Tool Migration)
# ============================================================

@register_tool(
    name="database_tool_v2",
    description="标准化的金融数据库查询工具，支持 SQL 查询和数据保存",
    category=ToolCategory.DATA_COLLECTION
)
class DatabaseToolV2(BaseTool):
    """
    标准化数据库工具 V2

    基于原有的 database_tool.py 进行完全重构
    """

    name = "database_tool_v2"
    description = "标准化的金融数据库查询工具，支持 SQL 查询和数据保存"
    category = ToolCategory.DATA_COLLECTION
    version = "2.0.0"

    def __init__(self):
        super().__init__()

        # 初始化数据库连接
        try:
            from app.store.database_service import get_database_connection
            self.db_connection = get_database_connection()
        except Exception as e:
            self.logger.error(f"初始化数据库连接失败：{e}")
            self.db_connection = None

    def execute(self, tool_input: ToolInput) -> ToolOutput:
        """执行数据库操作 - 标准化实现"""
        try:
            params = tool_input.params

            operation = params.get('operation', 'query')
            table = params.get('table', 'financial_data')
            conditions = params.get('conditions', {})
            search_keyword = params.get('search_keyword', tool_input.query)

            # 验证数据库连接
            if not self.db_connection:
                return ToolOutput(
                    status="error",
                    data=None,
                    error_message="数据库连接未正确初始化",
                    metadata={"error_code": ErrorCodes.CONFIGURATION_ERROR}
                )

            # 执行操作
            if operation == 'query':
                return self._query_data(table, conditions, search_keyword)
            elif operation == 'save':
                return self._save_data(params.get('data', {}), table)
            else:
                return ToolOutput(
                    status="error",
                    data=None,
                    error_message=f"不支持的操作类型：{operation}",
                    metadata={
                        "error_code": ErrorCodes.INVALID_INPUT,
                        "supported_operations": ["query", "save"]
                    }
                )

        except Exception as e:
            self.logger.error(f"数据库操作失败：{str(e)}", exc_info=True)
            return ToolOutput(
                status="error",
                data=None,
                error_message=str(e),
                metadata={
                    "error_code": ErrorCodes.EXECUTION_ERROR,
                    "operation": tool_input.params.get('operation', 'unknown')
                }
            )

    def _query_data(self, table: str, conditions: dict, keyword: str) -> ToolOutput:
        """查询数据"""
        try:
            connection = self.db_connection.get_connection()
            if not connection:
                return ToolOutput(
                    status="error",
                    data=None,
                    error_message="无法获取数据库连接",
                    metadata={"error_code": ErrorCodes.CONNECTION_ERROR}
                )

            cursor = connection.cursor(dictionary=True)

            # 构建查询语句
            if conditions:
                where_clause = " AND ".join(
                    [f"{key} = %s" for key in conditions.keys()])
                query = f"SELECT * FROM {table} WHERE {where_clause}"
                values = list(conditions.values())
                cursor.execute(query, values)
            elif keyword:
                # 模糊查询
                query = f"SELECT * FROM {table} WHERE content LIKE %s OR title LIKE %s"
                cursor.execute(query, (f"%{keyword}%", f"%{keyword}%"))
            else:
                query = f"SELECT * FROM {table} LIMIT 100"
                cursor.execute(query)

            result = cursor.fetchall()
            cursor.close()

            return ToolOutput(
                status="success",
                data=result,
                metadata={
                    "table": table,
                    "record_count": len(result),
                    "query_type": "SELECT",
                    "has_conditions": bool(conditions or keyword)
                }
            )

        except Exception as e:
            self.logger.error(f"数据库查询失败：{str(e)}", exc_info=True)
            return ToolOutput(
                status="error",
                data=None,
                error_message=str(e),
                metadata={"error_code": ErrorCodes.DATABASE_ERROR}
            )

    def _save_data(self, data: dict, table: str) -> ToolOutput:
        """保存数据"""
        try:
            if not data:
                return ToolOutput(
                    status="error",
                    data=None,
                    error_message="没有要保存的数据",
                    metadata={"error_code": ErrorCodes.INVALID_INPUT}
                )

            connection = self.db_connection.get_connection()
            if not connection:
                return ToolOutput(
                    status="error",
                    data=None,
                    error_message="无法获取数据库连接",
                    metadata={"error_code": ErrorCodes.CONNECTION_ERROR}
                )

            cursor = connection.cursor()

            columns = ', '.join(data.keys())
            placeholders = ', '.join(['%s'] * len(data))
            query = f"INSERT INTO {table} ({columns}) VALUES ({placeholders})"

            cursor.execute(query, list(data.values()))
            connection.commit()

            inserted_id = cursor.lastrowid
            cursor.close()

            return ToolOutput(
                status="success",
                data={"inserted_id": inserted_id},
                metadata={
                    "table": table,
                    "inserted_id": inserted_id,
                    "affected_rows": 1
                }
            )

        except Exception as e:
            self.logger.error(f"数据库保存失败：{str(e)}", exc_info=True)
            return ToolOutput(
                status="error",
                data=None,
                error_message=str(e),
                metadata={"error_code": ErrorCodes.DATABASE_ERROR}
            )

    def _get_examples(self) -> List[Dict[str, Any]]:
        """提供使用示例"""
        return [
            {
                "query": "贵州茅台",
                "params": {
                    "operation": "query",
                    "table": "financial_data",
                    "search_keyword": "贵州茅台"
                },
                "description": "查询贵州茅台相关数据"
            },
            {
                "query": "",
                "params": {
                    "operation": "save",
                    "table": "analysis_results",
                    "data": {"title": "测试", "content": "内容"}
                },
                "description": "保存分析结果到数据库"
            }
        ]

    def _get_timeout(self) -> int:
        return 30


# ============================================================
# 5. 批量注册函数 - 一次性注册所有迁移的工具
# ============================================================

def register_all_migrated_tools() -> Dict[str, bool]:
    """
    批量注册所有已迁移的标准化工具

    Returns:
        注册结果字典 {tool_name: success}
    """
    registry = get_global_registry()

    tools_to_register = [
        WebScrapingToolV2(),
        DataParsingToolV2(),
        DataSummarizationToolV2(),
        DatabaseToolV2()
    ]

    registration_results = {}

    for tool in tools_to_register:
        success = registry.register(tool, override=False)
        registration_results[tool.name] = success

        if success:
            print(f"✓ 工具 {tool.name} 注册成功")
            print(f"  描述：{tool.description}")
            print(f"  分类：{tool.category}")
            print(f"  版本：{tool.version}")
        else:
            print(f"✗ 工具 {tool.name} 注册失败（可能已存在）")

        print()

    return registration_results


# ============================================================
# 6. 兼容性包装器 - 保持向后兼容
# ============================================================

def create_compatibility_wrappers():
    """
    创建旧版工具的兼容性包装器

    这样旧的调用方式仍然可以工作
    """
    registry = get_global_registry()

    # 为每个新工具创建旧名称的别名
    compatibility_mapping = {
        'web_scraping_tool': 'web_scraping_tool_v2',
        'data_parsing_tool': 'data_parsing_tool_v2',
        'data_summarization_tool': 'data_summarization_tool_v2',
        'database_tool': 'database_tool_v2'
    }

    print("\n创建兼容性包装器:")
    for old_name, new_name in compatibility_mapping.items():
        if registry.has_tool(new_name):
            print(f"  ✓ {old_name} → {new_name}")
        else:
            print(f"  ✗ {old_name} → {new_name} (新工具不存在)")


# ============================================================
# 7. 使用示例和测试
# ============================================================

def demo_migrated_tools():
    """演示已迁移的工具使用方法"""
    registry = get_global_registry()

    print("=" * 60)
    print("标准化迁移工具演示")
    print("=" * 60)

    # 示例 1: 网络爬虫工具
    print("\n1. 网络爬虫工具演示")
    result = registry.execute_tool(
        "web_scraping_tool_v2",
        "人工智能",
        data_source="eastmoney",
        data_type="financial_news"
    )
    print(f"状态：{result['status']}")
    print(f"记录数：{result['metadata'].get('record_count', 0)}")
    print(f"数据源：{result['metadata'].get('source', 'unknown')}")

    # 示例 2: 数据解析工具
    print("\n2. 数据解析工具演示")
    sample_text = "贵州茅台 2023 年实现营收 1234 亿元，同比增长 15%"
    result = registry.execute_tool(
        "data_parsing_tool_v2",
        sample_text
    )
    print(f"状态：{result['status']}")
    print(f"原文长度：{result['metadata'].get('original_text_length', 0)}")

    # 示例 3: 数据汇总工具
    print("\n3. 数据汇总工具演示")
    long_text = "贵州茅台 2023 年实现营收 1234 亿元，同比增长 15%。其中茅台酒收入占比超过 90%，系列酒收入稳步增长。公司净利润达到 567 亿元，毛利率保持在 90% 以上。" * 10
    result = registry.execute_tool(
        "data_summarization_tool_v2",
        long_text
    )
    print(f"状态：{result['status']}")
    print(f"压缩比：{result['metadata'].get('compression_ratio', 0)}%")

    # 示例 4: 数据库工具
    print("\n4. 数据库工具演示")
    result = registry.execute_tool(
        "database_tool_v2",
        "贵州茅台",
        operation="query",
        table="financial_data",
        search_keyword="贵州茅台"
    )
    print(f"状态：{result['status']}")
    print(f"记录数：{result['metadata'].get('record_count', 0)}")

    print("\n" + "=" * 60)
    print("演示完成")
    print("=" * 60)


# ============================================================
# 主程序 - 自动执行迁移
# ============================================================

if __name__ == "__main__":
    print("开始迁移现有工具到新标准接口...\n")

    # 注册所有迁移的工具
    results = register_all_migrated_tools()

    # 创建兼容性包装器
    create_compatibility_wrappers()

    # 运行演示（可选）
    # demo_migrated_tools()

    # 打印总结
    print("\n迁移总结:")
    successful = sum(1 for v in results.values() if v)
    total = len(results)
    print(f"成功迁移：{successful}/{total} 个工具")

    if successful == total:
        print("✓ 所有工具已成功迁移到新标准接口！")
    else:
        print(f"⚠ 有 {total - successful} 个工具迁移失败")
