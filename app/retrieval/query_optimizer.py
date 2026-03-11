"""
查询优化模块 - 查询改写、扩展和重写
提升检索效果的关键组件
"""
import re
from typing import List, Dict, Any
import logging

logger = logging.getLogger(__name__)


class QueryRewriter:
    """
    查询改写器 - 优化用户查询以提升检索质量
    
    功能：
    1. 查询扩展（同义词、相关词）
    2. 查询简化（去除冗余）
    3. 查询丰富化（添加上下文）
    4. 关键词提取
    """
    
    def __init__(self, llm_client=None):
        """
        初始化查询改写器
        
        Args:
            llm_client: LLM 客户端实例（用于智能改写）
        """
        self.llm_client = llm_client
        
        # 金融领域同义词典（简化版）
        self.synonym_dict = {
            '财报': ['财务报告', '年报', '季报', '财务报表'],
            '营收': ['营业收入', '收入', '销售额', '营业额'],
            '利润': ['净利润', '盈利', '收益', '纯利'],
            '风险': ['风险评估', '波动性', '波动率'],
            '股价': ['股票价格', '市值', '股价走势'],
            '分析': ['分析报告', '研究报告', '评估'],
            '预测': ['展望', '预期', '预估'],
            '增长': ['增长率', '增速', '上升'],
            '下降': ['下滑', '下跌', '减少'],
        }
        
        logger.info("查询改写器初始化完成")
    
    def expand_query(self, query: str, num_expansions: int = 3) -> List[str]:
        """
        查询扩展 - 生成多个相关查询版本
        
        Args:
            query: 原始查询
            num_expansions: 扩展数量
        
        Returns:
            扩展后的查询列表
        """
        expansions = [query]  # 包含原查询
        
        # 1. 基于同义词典扩展
        expanded_versions = self._synonym_expansion(query)
        expansions.extend(expanded_versions[:num_expansions])
        
        # 2. 如果配置了 LLM，使用 LLM 进行智能扩展
        if self.llm_client and len(expansions) < num_expansions + 1:
            llm_expansions = self._llm_expansion(query, num_expansions - len(expansions) + 1)
            expansions.extend(llm_expansions)
        
        logger.info(f"查询扩展：'{query}' -> {len(expansions)} 个版本")
        return expansions[:num_expansions + 1]
    
    def _synonym_expansion(self, query: str) -> List[str]:
        """
        基于同义词典的查询扩展
        
        Args:
            query: 原始查询
        
        Returns:
            扩展后的查询列表
        """
        expanded = []
        
        for keyword, synonyms in self.synonym_dict.items():
            if keyword in query:
                for synonym in synonyms[:2]:  # 每个关键词最多替换 2 次
                    new_query = query.replace(keyword, synonym)
                    if new_query != query:
                        expanded.append(new_query)
        
        return expanded
    
    def _llm_expansion(self, query: str, num_versions: int = 3) -> List[str]:
        """
        使用 LLM 进行智能查询扩展
        
        Args:
            query: 原始查询
            num_versions: 生成的版本数量
        
        Returns:
            扩展后的查询列表
        """
        if not self.llm_client:
            return []
        
        try:
            prompt = f"""
            请将以下金融领域的查询改写为 {num_versions} 个不同但语义相关的版本。
            要求：
            1. 保持原意
            2. 使用不同的表达方式
            3. 可以添加相关术语或背景信息
            
            原查询：{query}
            
            改写版本（每行一个）：
            """
            
            response = self.llm_client.generate(prompt)
            
            # 解析响应
            versions = [line.strip() for line in response.split('\n') if line.strip()]
            versions = [v for v in versions if v != query][:num_versions]
            
            logger.info(f"LLM 扩展成功，生成 {len(versions)} 个版本")
            return versions
            
        except Exception as e:
            logger.error(f"LLM 查询扩展失败：{e}")
            return []
    
    def simplify_query(self, query: str) -> str:
        """
        简化查询 - 去除冗余词汇
        
        Args:
            query: 原始查询
        
        Returns:
            简化后的查询
        """
        # 移除常见的冗余表达
        redundant_patterns = [
            r'请(问 | 帮我 | 给我).*',
            r'我想了解.*',
            r'我想知道.*',
            r'能不能告诉我.*',
            r'什么是.*',
        ]
        
        simplified = query
        for pattern in redundant_patterns:
            simplified = re.sub(pattern, '', simplified)
        
        # 移除语气词
        simplified = re.sub(r'[？!?！]+$', '', simplified)
        
        return simplified.strip()
    
    def enrich_query(self, query: str, context: str = None) -> str:
        """
        丰富查询 - 添加上下文信息
        
        Args:
            query: 原始查询
            context: 额外的上下文信息
        
        Returns:
            丰富后的查询
        """
        enriched_parts = [query]
        
        # 如果提供了上下文，添加到查询中
        if context:
            enriched_parts.append(f"在以下背景下：{context}")
        
        # 添加时间上下文（如果需要）
        from datetime import datetime
        current_year = datetime.now().year
        if '今年' in query or '最近' in query:
            enriched_parts.append(f"(时间范围：{current_year}年)")
        
        return ' '.join(enriched_parts)
    
    def extract_keywords(self, query: str, top_k: int = 5) -> List[str]:
        """
        提取查询关键词
        
        Args:
            query: 原始查询
            top_k: 返回的关键词数量
        
        Returns:
            关键词列表
        """
        # 尝试使用 jieba 分词
        try:
            import jieba.analyse
            
            # 使用 TF-IDF 提取关键词
            keywords = jieba.analyse.extract_tags(query, topK=top_k)
            return keywords
            
        except ImportError:
            # 简单回退方案：按长度过滤
            words = query.split()
            keywords = [w for w in words if len(w) > 1]
            return keywords[:top_k]
    
    def rewrite_query(self, query: str, mode: str = 'expand') -> List[str]:
        """
        综合查询改写接口
        
        Args:
            query: 原始查询
            mode: 改写模式
                - 'expand': 扩展模式（生成多个版本）
                - 'simplify': 简化模式
                - 'enrich': 丰富模式
                - 'hybrid': 混合模式（多种策略组合）
        
        Returns:
            改写后的查询列表
        """
        if mode == 'expand':
            return self.expand_query(query)
        
        elif mode == 'simplify':
            simplified = self.simplify_query(query)
            return [simplified]
        
        elif mode == 'enrich':
            enriched = self.enrich_query(query)
            return [enriched]
        
        elif mode == 'hybrid':
            # 混合模式：先简化，再扩展
            simplified = self.simplify_query(query)
            expanded = self.expand_query(simplified)
            return expanded
        
        else:
            logger.warning(f"未知的改写模式：{mode}，返回原查询")
            return [query]


# 查询改写的便捷接口
def rewrite_query_intelligently(query: str, 
                                llm_client=None,
                                mode: str = 'hybrid') -> List[str]:
    """
    智能查询改写的便捷接口
    
    Args:
        query: 原始查询
        llm_client: LLM 客户端
        mode: 改写模式
    
    Returns:
        改写后的查询列表
    """
    rewriter = QueryRewriter(llm_client=llm_client)
    return rewriter.rewrite_query(query, mode=mode)


def extract_query_keywords(query: str) -> List[str]:
    """
    提取查询关键词的便捷接口
    
    Args:
        query: 原始查询
    
    Returns:
        关键词列表
    """
    rewriter = QueryRewriter()
    return rewriter.extract_keywords(query)
