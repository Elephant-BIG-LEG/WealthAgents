"""
智能上下文组装模块
根据检索结果的质量和相关性，智能地组织和呈现上下文信息
"""
from typing import List, Dict, Tuple, Any
import logging

logger = logging.getLogger(__name__)


class ContextAssembler:
    """
    智能上下文组装器 - 优化 RAG 检索结果的呈现
    
    功能：
    1. 分级处理（高相关性 vs 中低相关性）
    2. 去重和融合
    3. 摘要生成（对于低相关性内容）
    4. 格式化和结构化输出
    """
    
    def __init__(self, max_tokens: int = 2000, similarity_threshold: float = 0.5):
        """
        初始化上下文组装器
        
        Args:
            max_tokens: 最大 token 数（用于控制上下文长度）
            similarity_threshold: 相似度阈值，低于此值的内容将被摘要或丢弃
        """
        self.max_tokens = max_tokens
        self.similarity_threshold = similarity_threshold
        
        logger.info(f"上下文组装器初始化完成 - Max tokens: {max_tokens}, Threshold: {similarity_threshold}")
    
    def assemble(self, results: List[Tuple[str, float, Dict]], 
                 query: str = None) -> str:
        """
        智能组装上下文
        
        Args:
            results: 检索结果列表 [(text, score, metadata), ...]
            query: 原始查询（可选，用于优化）
        
        Returns:
            组装后的上下文字符串
        """
        if not results:
            return ""
        
        # 1. 按相关性分级
        high_relevance = []
        medium_relevance = []
        low_relevance = []
        
        for text, score, metadata in results:
            if score >= 0.8:
                high_relevance.append((text, score, metadata))
            elif score >= 0.5:
                medium_relevance.append((text, score, metadata))
            else:
                low_relevance.append((text, score, metadata))
        
        logger.info(f"分级结果 - 高相关：{len(high_relevance)}, 中相关：{len(medium_relevance)}, 低相关：{len(low_relevance)}")
        
        # 2. 去重
        high_relevance = self._deduplicate_results(high_relevance)
        medium_relevance = self._deduplicate_results(medium_relevance)
        
        # 3. 智能组装
        context_parts = []
        current_tokens = 0
        
        # 优先处理高相关性内容（保留完整文本）
        for text, score, metadata in high_relevance:
            tokens = self._estimate_tokens(text)
            if current_tokens + tokens <= self.max_tokens * 0.7:
                formatted_text = self._format_chunk(text, score, metadata, full=True)
                context_parts.append(formatted_text)
                current_tokens += tokens
        
        # 补充中等相关内容（可能进行摘要）
        for text, score, metadata in medium_relevance:
            if current_tokens >= self.max_tokens * 0.85:
                break
            
            tokens = self._estimate_tokens(text)
            
            # 如果空间不够，进行摘要
            if current_tokens + tokens > self.max_tokens * 0.85:
                summary = self._simple_summarize(text, max_length=100)
                formatted_text = self._format_chunk(summary, score, metadata, is_summary=True)
                context_parts.append(formatted_text)
                current_tokens += self._estimate_tokens(summary)
            else:
                formatted_text = self._format_chunk(text, score, metadata, full=False)
                context_parts.append(formatted_text)
                current_tokens += tokens
        
        # 低相关性内容通常不加入（除非空间非常充裕）
        if low_relevance and current_tokens < self.max_tokens * 0.5:
            # 只添加最高分的低相关性内容的摘要
            if low_relevance:
                text, score, metadata = low_relevance[0]
                summary = self._simple_summarize(text, max_length=80)
                formatted_text = self._format_chunk(summary, score, metadata, is_summary=True)
                context_parts.append(formatted_text)
        
        # 4. 合并所有部分
        context = "\n\n".join(context_parts)
        
        logger.info(f"上下文组装完成 - 总 token 数：{current_tokens}, 片段数：{len(context_parts)}")
        
        return context
    
    def _deduplicate_results(self, results: List[Tuple[str, float, Dict]]) -> List[Tuple[str, float, Dict]]:
        """
        去重 - 移除高度相似的结果
        
        Args:
            results: 结果列表
        
        Returns:
            去重后的结果列表
        """
        if len(results) <= 1:
            return results
        
        deduplicated = []
        seen_hashes = set()
        
        for text, score, metadata in results:
            # 使用文本前 100 个字符作为简单哈希
            text_hash = hash(text[:100])
            
            if text_hash not in seen_hashes:
                deduplicated.append((text, score, metadata))
                seen_hashes.add(text_hash)
        
        logger.debug(f"去重：{len(results)} -> {len(deduplicated)}")
        return deduplicated
    
    def _format_chunk(self, text: str, score: float, metadata: Dict, 
                     full: bool = False, is_summary: bool = False) -> str:
        """
        格式化文本块
        
        Args:
            text: 文本内容
            score: 相似度分数
            metadata: 元数据
            full: 是否完整格式
            is_summary: 是否为摘要
        
        Returns:
            格式化后的文本
        """
        prefix = "[摘要]" if is_summary else ""
        source = metadata.get('source', '未知来源')
        timestamp = metadata.get('timestamp', '')
        
        if full:
            # 完整格式（高相关性内容）
            formatted = f"{prefix}【相关度：{score:.2f} | 来源：{source}】\n{text}"
        else:
            # 简洁格式（中等相关性内容）
            formatted = f"{prefix}【相关度：{score:.2f} | 来源：{source}】{text[:200]}..."
        
        if timestamp:
            formatted += f"\n(时间：{timestamp})"
        
        return formatted
    
    def _simple_summarize(self, text: str, max_length: int = 100) -> str:
        """
        简单摘要 - 提取关键句子
        
        Args:
            text: 原文本
            max_length: 最大长度
        
        Returns:
            摘要文本
        """
        if len(text) <= max_length:
            return text
        
        # 尝试按句子分割
        sentences = text.split('.')
        summary_parts = []
        current_length = 0
        
        for sentence in sentences:
            sentence = sentence.strip()
            if not sentence:
                continue
            
            if current_length + len(sentence) + 2 <= max_length:
                summary_parts.append(sentence)
                current_length += len(sentence) + 2
            else:
                break
        
        summary = '. '.join(summary_parts)
        
        # 如果还是太长，直接截断
        if len(summary) > max_length:
            summary = summary[:max_length] + "..."
        
        return summary
    
    def _estimate_tokens(self, text: str) -> int:
        """
        估算 token 数量（简化版本）
        
        Args:
            text: 文本
        
        Returns:
            估算的 token 数
        """
        # 中文：每 4 个字符约 1 个 token
        # 英文：每 4 个字符约 1 个 token
        chinese_chars = sum(1 for c in text if '\u4e00' <= c <= '\u9fff')
        other_chars = len(text) - chinese_chars
        
        estimated_tokens = chinese_chars // 2 + other_chars // 4
        return estimated_tokens


def assemble_context_intelligently(results: List[Tuple[str, float, Dict]], 
                                   query: str = None,
                                   max_tokens: int = 2000) -> str:
    """
    智能组装上下文的便捷接口
    
    Args:
        results: 检索结果列表
        query: 原始查询
        max_tokens: 最大 token 数
    
    Returns:
        组装后的上下文
    """
    assembler = ContextAssembler(max_tokens=max_tokens)
    return assembler.assemble(results, query=query)


# 创建全局组装器实例
global_context_assembler = ContextAssembler(max_tokens=2000)
