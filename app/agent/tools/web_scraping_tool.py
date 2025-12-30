"""
财富Agent - 智能投研分析平台
私人Agent模块 - 网络采集工具
"""
from typing import Dict, Any, List, Optional
from ...ingest.web_fetcher import Collection_action_llm
from ...ingest.source import Source
import logging
import re
import time


class WebScrapingTool:
    """网络采集工具类"""

    def __init__(self):
        self.logger = logging.getLogger(__name__)
        
        # 定义支持的数据源配置
        self.data_sources = {
            'eastmoney': {
                'name': '东方财富网',
                'base_url': 'https://finance.eastmoney.com/',
                'supported_types': ['financial_news', 'stock_data', 'market_trends'],
                'description': '中国领先的金融信息服务平台，提供全面的财经资讯和数据'
            },
            'ifeng': {
                'name': '凤凰财经',
                'base_url': 'https://finance.ifeng.com/',
                'supported_types': ['financial_news', 'economic_data', 'market_analysis'],
                'description': '凤凰网财经频道，提供国内外财经新闻和深度分析'
            },
            'hexun': {
                'name': '和讯网',
                'base_url': 'https://www.hexun.com/',
                'supported_types': ['financial_news', 'stock_research', 'investment_strategy'],
                'description': '综合性财经门户网站，提供专业的金融资讯和研究报告'
            },
            'sina': {
                'name': '新浪财经',
                'base_url': 'https://finance.sina.com.cn/',
                'supported_types': ['financial_news', 'stock_quotes', 'market_data'],
                'description': '新浪网财经频道，提供实时财经资讯和股票行情'
            }
        }

    def scrape_data(self, query: str, data_source: str = 'eastmoney', 
                   data_type: str = 'financial_news', **kwargs) -> Dict[str, Any]:
        """
        通用数据采集方法，支持多种数据源和数据类型

        Args:
            query: 查询关键词
            data_source: 数据源名称，默认东方财富网
            data_type: 数据类型，默认财经新闻
            **kwargs: 其他参数

        Returns:
            采集结果
        """
        try:
            # 验证数据源
            if data_source not in self.data_sources:
                return {
                    "status": "error",
                    "error_message": f"不支持的数据源: {data_source}，支持的数据源: {list(self.data_sources.keys())}",
                    "query": query,
                    "timestamp": time.time()
                }
            
            source_config = self.data_sources[data_source]
            
            # 验证数据类型
            if data_type not in source_config['supported_types']:
                return {
                    "status": "error",
                    "error_message": f"数据源 {source_config['name']} 不支持 {data_type} 类型，支持的类型: {source_config['supported_types']}",
                    "query": query,
                    "timestamp": time.time()
                }

            # 清理查询关键词
            clean_query = self._clean_query(query)

            # 创建数据源对象
            source = Source(
                source_id=f"{data_source}_{clean_query}_{time.time_ns()}",
                source_name=f"{source_config['name']}-{clean_query}",
                type="web",
                url=source_config['base_url'],
                config={
                    "query": clean_query, 
                    "data_type": data_type,
                    "search_keyword": clean_query,
                    "source_specific": kwargs.get('source_specific', {})
                }
            )

            # 执行采集动作
            results = Collection_action_llm(source)

            return {
                "status": "success",
                "data": results,
                "count": len(results) if results else 0,
                "query": clean_query,
                "source": source_config['name'],
                "source_id": data_source,
                "data_type": data_type,
                "timestamp": time.time()
            }

        except Exception as e:
            self.logger.error(f"网络采集失败: {str(e)}")
            return {
                "status": "error",
                "error_message": str(e),
                "query": query,
                "source": data_source,
                "data_type": data_type,
                "timestamp": time.time()
            }

    def scrape_financial_data(self, query: str, **kwargs) -> Dict[str, Any]:
        """
        采集金融数据（兼容旧接口）

        Args:
            query: 查询关键词
            **kwargs: 其他参数

        Returns:
            采集结果
        """
        # 兼容旧接口，默认使用东方财富网采集财经新闻
        return self.scrape_data(query, 
                               data_source=kwargs.get('data_source', 'eastmoney'),
                               data_type=kwargs.get('data_type', 'financial_news'),
                               **kwargs)
                                
    def scrape_stock_data(self, query: str, data_source: str = 'eastmoney', **kwargs) -> Dict[str, Any]:
        """
        采集股票数据

        Args:
            query: 查询关键词
            data_source: 数据源名称
            **kwargs: 其他参数

        Returns:
            采集结果
        """
        return self.scrape_data(query, data_source=data_source, data_type='stock_data', **kwargs)
        
    def scrape_market_trends(self, query: str, data_source: str = 'eastmoney', **kwargs) -> Dict[str, Any]:
        """
        采集市场趋势数据

        Args:
            query: 查询关键词
            data_source: 数据源名称
            **kwargs: 其他参数

        Returns:
            采集结果
        """
        return self.scrape_data(query, data_source=data_source, data_type='market_trends', **kwargs)
        
    def get_supported_sources(self) -> Dict[str, Any]:
        """
        获取支持的数据源列表

        Returns:
            数据源配置字典
        """
        return self.data_sources

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
    return tool.scrape_data(query, **kwargs)
    
def financial_data_scraper(query: str, **kwargs) -> Dict[str, Any]:
    """
    金融数据采集便捷函数

    Args:
        query: 查询关键词
        **kwargs: 其他参数

    Returns:
        采集结果
    """
    tool = WebScrapingTool()
    return tool.scrape_financial_data(query, **kwargs)
    
def stock_data_scraper(query: str, **kwargs) -> Dict[str, Any]:
    """
    股票数据采集便捷函数

    Args:
        query: 查询关键词
        **kwargs: 其他参数

    Returns:
        采集结果
    """
    tool = WebScrapingTool()
    return tool.scrape_stock_data(query, **kwargs)