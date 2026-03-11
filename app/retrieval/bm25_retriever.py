"""
BM25 关键词检索模块
用于混合检索中的稀疏检索部分
"""
import re
from typing import List, Dict, Tuple
from collections import Counter
import math
import logging

logger = logging.getLogger(__name__)


class BM25Retriever:
    """
    BM25 检索器 - 基于词频的关键词检索
    
    特性：
    1. 高效的关键词匹配
    2. 支持中文分词（使用 jieba）
    3. TF-IDF 加权
    4. 可配置参数优化
    """
    
    def __init__(self, k1: float = 1.5, b: float = 0.75):
        """
        初始化 BM25 检索器
        
        Args:
            k1: 控制词频饱和度的参数（通常 1.2-2.0）
            b: 控制文档长度归一化的参数（通常 0.5-0.8）
        """
        self.k1 = k1
        self.b = b
        
        # 文档集合
        self.documents = []  # (doc_id, text)
        self.doc_lengths = {}  # doc_id -> length
        self.avg_doc_length = 0
        
        # 词项统计
        self.doc_freq = Counter()  # term -> 包含该词的文档数
        self.doc_term_freqs = {}  # doc_id -> {term -> freq}
        
        # 是否已建立索引
        self.indexed = False
        
        # 尝试导入 jieba
        try:
            import jieba
            self.jieba = jieba
            self.use_jieba = True
            logger.info("jieba 分词可用")
        except ImportError:
            self.use_jieba = False
            logger.warning("未安装 jieba，将使用简单的字符级分词。建议安装：pip install jieba")
    
    def _tokenize(self, text: str) -> List[str]:
        """
        对文本进行分词
        
        Args:
            text: 输入文本
        
        Returns:
            分词后的词列表
        """
        if not text:
            return []
        
        # 转为小写
        text = text.lower()
        
        if self.use_jieba:
            # 使用 jieba 分词
            words = self.jieba.lcut(text)
            # 过滤停用词和单字符（标点等）
            stopwords = {'的', '了', '是', '在', '就', '都', '而', '及', '与', '着', '就', '那', '还是'}
            words = [w for w in words if w.strip() and w not in stopwords and len(w) > 1]
            return words
        else:
            # 简单分词：按标点和空格分割
            words = re.split(r'[^\w\u4e00-\u9fa5]+', text)
            words = [w for w in words if w.strip() and len(w) > 1]
            return words
    
    def add_documents(self, documents: List[Tuple[int, str]]):
        """
        添加文档到索引
        
        Args:
            documents: 文档列表 [(doc_id, text), ...]
        """
        if not documents:
            return
        
        logger.info(f"正在为 {len(documents)} 条文档建立 BM25 索引...")
        
        total_length = 0
        
        for doc_id, text in documents:
            self.documents.append((doc_id, text))
            
            # 分词
            tokens = self._tokenize(text)
            
            # 记录文档长度
            doc_length = len(tokens)
            self.doc_lengths[doc_id] = doc_length
            total_length += doc_length
            
            # 统计词频
            term_freq = Counter(tokens)
            self.doc_term_freqs[doc_id] = term_freq
            
            # 更新文档频率
            for term in set(term_freq.keys()):
                self.doc_freq[term] += 1
        
        # 计算平均文档长度
        self.avg_doc_length = total_length / len(documents)
        self.indexed = True
        
        logger.info(f"BM25 索引建立完成，平均文档长度：{self.avg_doc_length:.1f}")
    
    def search(self, query: str, top_k: int = 10) -> List[Tuple[int, str, float]]:
        """
        搜索与查询最相关的文档
        
        Args:
            query: 查询文本
            top_k: 返回结果数量
        
        Returns:
            [(doc_id, text, score), ...] 按分数降序排列
        """
        if not self.indexed or len(self.documents) == 0:
            logger.warning("BM25 索引为空，返回空结果")
            return []
        
        # 对查询分词
        query_tokens = self._tokenize(query)
        
        if not query_tokens:
            logger.warning("查询分词结果为空")
            return []
        
        # 计算每个文档的 BM25 分数
        scores = {}
        
        for doc_id, _ in self.documents:
            score = 0.0
            doc_length = self.doc_lengths.get(doc_id, 0)
            term_freqs = self.doc_term_freqs.get(doc_id, {})
            
            for token in query_tokens:
                # 词频
                tf = term_freqs.get(token, 0)
                if tf == 0:
                    continue
                
                # 文档频率
                df = self.doc_freq.get(token, 0)
                
                # IDF 计算
                idf = math.log((len(self.documents) - df + 0.5) / (df + 0.5) + 1)
                
                # BM25 公式
                numerator = tf * (self.k1 + 1)
                denominator = tf + self.k1 * (1 - self.b + self.b * doc_length / self.avg_doc_length)
                
                score += idf * numerator / denominator
            
            if score > 0:
                scores[doc_id] = score
        
        # 排序并返回 top_k
        sorted_docs = sorted(scores.items(), key=lambda x: x[1], reverse=True)
        
        # 构建完整结果
        results = []
        doc_dict = dict(self.documents)
        
        for doc_id, score in sorted_docs[:top_k]:
            text = doc_dict.get(doc_id, "")
            results.append((doc_id, text, score))
        
        logger.info(f"BM25 检索返回 {len(results)} 条结果")
        return results
    
    def batch_search(self, queries: List[str], top_k: int = 10) -> Dict[str, List[Tuple[int, str, float]]]:
        """
        批量搜索多个查询
        
        Args:
            queries: 查询列表
            top_k: 每个查询返回的结果数量
        
        Returns:
            {query: [(doc_id, text, score), ...]}
        """
        results = {}
        for query in queries:
            results[query] = self.search(query, top_k)
        return results
    
    def get_document_count(self) -> int:
        """获取索引中的文档数量"""
        return len(self.documents)
    
    def clear_index(self):
        """清空索引"""
        self.documents = []
        self.doc_lengths = {}
        self.doc_freq = Counter()
        self.doc_term_freqs = {}
        self.avg_doc_length = 0
        self.indexed = False
        logger.info("BM25 索引已清空")


# 创建全局 BM25 检索器实例
global_bm25_retriever = BM25Retriever(k1=1.5, b=0.75)


def create_bm25_retriever(k1: float = 1.5, b: float = 0.75) -> BM25Retriever:
    """
    创建 BM25 检索器实例
    
    Args:
        k1: 词频饱和度参数
        b: 长度归一化参数
    
    Returns:
        BM25Retriever 实例
    """
    return BM25Retriever(k1=k1, b=b)


def build_bm25_index(documents: List[Tuple[int, str]], 
                     k1: float = 1.5, b: float = 0.75) -> BM25Retriever:
    """
    建立 BM25 索引的主要接口函数
    
    Args:
        documents: 文档列表 [(doc_id, text), ...]
        k1: BM25 参数
        b: BM25 参数
    
    Returns:
        已建立索引的 BM25Retriever
    """
    retriever = BM25Retriever(k1=k1, b=b)
    retriever.add_documents(documents)
    return retriever


def bm25_search(query: str, top_k: int = 10) -> List[Tuple[int, str, float]]:
    """
    BM25 检索的便捷接口
    
    Args:
        query: 查询文本
        top_k: 返回结果数量
    
    Returns:
        [(doc_id, text, score), ...]
    """
    return global_bm25_retriever.search(query, top_k)
