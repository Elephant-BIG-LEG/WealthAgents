"""
财富Agent - 智能投研分析平台
私人Agent模块 - 网络采集工具
"""
from typing import Dict, Any, List
from ...ingest.web_fetcher import Collection_action_llm
from ...ingest.source import Source
import logging
import re


class WebScrapingTool:
    """网络采集工具类"""

    def __init__(self):
        self.logger = logging.getLogger(__name__)

    def scrape_financial_data(self, query: str, **kwargs) -> Dict[str, Any]:
        """
        采集金融数据

        Args:
            query: 查询关键词
            **kwargs: 其他参数

        Returns:
            采集结果
        """
        try:
            # 清理查询关键词，移除不合适的字符
            clean_query = self._clean_query(query)

            # 创建数据源对象 - 使用更通用的URL模式
            source = Source(
                source_id=f"web_{clean_query}_{__import__('time').time_ns()}",
                source_name=f"财经资讯-{clean_query}",
                type="web",
                url="https://finance.eastmoney.com/",  # 使用基础URL
                config={"query": clean_query, "data_type": "financial_news",
                        "search_keyword": clean_query}
            )

            # 执行采集动作
            results = Collection_action_llm(source)

            return {
                "status": "success",
                "data": results,
                "count": len(results) if results else 0,
                "query": clean_query,
                "source": "东方财富网",
                "timestamp": __import__('time').time()
            }

        except Exception as e:
            self.logger.error(f"网络采集失败: {str(e)}")
            return {
                "status": "error",
                "error_message": str(e),
                "query": query,
                "timestamp": __import__('time').time()
            }

    def _clean_query(self, query: str) -> str:
        """
        清理查询关键词

        Args:
            query: 原始查询关键词

        Returns:
            清理后的查询关键词
        """
        # 移除特殊字符，只保留中英文、数字和空格
        cleaned = re.sub(r'[^\w\s\u4e00-\u9fff]', ' ', query)
        # 移除多余空格
        cleaned = ' '.join(cleaned.split())
        return cleaned


# 便捷函数，供Executor调用
def web_scraping_tool(query: str, **kwargs) -> Dict[str, Any]:
    """
    网络采集工具便捷函数

    Args:
        query: 查询关键词
        **kwargs: 其他参数

    Returns:
        采集结果
    """
    tool = WebScrapingTool()
    return tool.scrape_financial_data(query, **kwargs)
