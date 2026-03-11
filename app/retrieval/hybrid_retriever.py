"""
混合检索模块 - 结合 Dense（向量）和 Sparse（BM25）检索
使用 Reciprocal Rank Fusion (RRF) 进行结果融合
"""
import numpy as np
from typing import List, Dict, Tuple, Any
import logging
from collections import defaultdict

logger = logging.getLogger(__name__)


class HybridRetriever:
    """
    混合检索器 - 结合语义检索和关键词检索
    
    特性：
    1. Dense Retrieval（SBERT 语义向量）
    2. Sparse Retrieval（BM25 关键词）
    3. RRF 融合算法
    4. 可配置权重
    """
    
    def __init__(self, 
                 vector_store=None,
                 bm25_retriever=None,
                 vectorizer=None,
                 dense_weight: float = 0.6,
                 sparse_weight: float = 0.4,
                 k: int = 60):
        """
        初始化混合检索器
        
        Args:
            vector_store: FAISS 向量存储实例
            bm25_retriever: BM25 检索器实例
            vectorizer: 文本向量化器实例
            dense_weight: 密集检索权重（默认 0.6）
            sparse_weight: 稀疏检索权重（默认 0.4）
            k: RRF 融合参数（通常 60）
        """
        self.vector_store = vector_store
        self.bm25_retriever = bm25_retriever
        self.vectorizer = vectorizer
        
        self.dense_weight = dense_weight
        self.sparse_weight = sparse_weight
        self.k = k  # RRF 参数，用于控制排名的影响
        
        logger.info(f"混合检索器初始化完成 - Dense 权重：{dense_weight}, Sparse 权重：{sparse_weight}")
    
    def set_weights(self, dense_weight: float, sparse_weight: float):
        """动态调整权重"""
        self.dense_weight = dense_weight
        self.sparse_weight = sparse_weight
        logger.info(f"权重已更新 - Dense: {dense_weight}, Sparse: {sparse_weight}")
    
    def search(self, query: str, top_k: int = 5, 
               return_scores: bool = True) -> List[Tuple[Any, float, Dict]]:
        """
        执行混合检索
        
        Args:
            query: 查询文本
            top_k: 返回结果数量
            return_scores: 是否返回分数
        
        Returns:
            [(text, score, metadata), ...] 按综合分数降序排列
        """
        if not self.vector_store and not self.bm25_retriever:
            logger.error("向量存储和 BM25 检索器都为空")
            return []
        
        # 1. 稠密检索（语义向量）
        dense_results = []
        if self.vector_store and self.vectorizer:
            try:
                query_vector = self.vectorizer.vectorize_text(query)
                dense_results = self.vector_store.search_similar(query_vector, top_k * 2)
                logger.info(f"Dense 检索返回 {len(dense_results)} 条结果")
            except Exception as e:
                logger.error(f"Dense 检索失败：{e}")
        
        # 2. 稀疏检索（BM25 关键词）
        sparse_results = []
        if self.bm25_retriever:
            try:
                bm25_raw = self.bm25_retriever.search(query, top_k * 2)
                # 转换为统一格式：(text, score, metadata)
                for doc_id, text, score in bm25_raw:
                    sparse_results.append((text, score, {"doc_id": doc_id}))
                logger.info(f"Sparse 检索返回 {len(sparse_results)} 条结果")
            except Exception as e:
                logger.error(f"Sparse 检索失败：{e}")
        
        # 3. RRF 融合
        fused_results = self._reciprocal_rank_fusion(
            dense_results, 
            sparse_results, 
            top_k
        )
        
        logger.info(f"RRF 融合后返回 {len(fused_results)} 条结果")
        
        if not return_scores:
            # 移除分数，只保留文本和元数据
            return [(text, meta) for text, _, meta in fused_results]
        
        return fused_results
    
    def _reciprocal_rank_fusion(self, 
                                 dense_results: List[Tuple], 
                                 sparse_results: List[Tuple],
                                 top_k: int) -> List[Tuple[Any, float, Dict]]:
        """
        使用 RRF 算法融合两个结果列表
        
        RRF 公式：
        Score(d) = Σ 1 / (k + rank_i(d))
        
        Args:
            dense_results: 稠密检索结果 [(text, dense_score, metadata), ...]
            sparse_results: 稀疏检索结果 [(text, sparse_score, metadata), ...]
            top_k: 返回结果数量
        
        Returns:
            融合后的结果 [(text, fused_score, metadata), ...]
        """
        # 为每个文档计算 RRF 分数
        rrf_scores = defaultdict(float)
        doc_info = {}  # 保存文档的完整信息
        
        # 处理稠密结果
        for rank, (text, score, metadata) in enumerate(dense_results, start=1):
            # 使用加权 RRF
            rrf_score = self.dense_weight / (self.k + rank)
            rrf_scores[text] += rrf_score
            
            # 保存文档信息（优先保留 dense 的元数据）
            if text not in doc_info:
                doc_info[text] = (score, metadata)
        
        # 处理稀疏结果
        for rank, (text, score, metadata) in enumerate(sparse_results, start=1):
            # 使用加权 RRF
            rrf_score = self.sparse_weight / (self.k + rank)
            rrf_scores[text] += rrf_score
            
            # 如果是新的文档，保存信息
            if text not in doc_info:
                doc_info[text] = (score, metadata)
            else:
                # 合并元数据
                existing_meta = doc_info[text][1]
                existing_meta.update(metadata)
                doc_info[text] = (doc_info[text][0], existing_meta)
        
        # 排序并返回 top_k
        sorted_docs = sorted(rrf_scores.items(), key=lambda x: x[1], reverse=True)
        
        results = []
        for text, fused_score in sorted_docs[:top_k]:
            original_score, metadata = doc_info.get(text, (0.0, {}))
            # 将 RRF 分数也加入元数据
            metadata['rrf_score'] = fused_score
            metadata['original_score'] = original_score
            results.append((text, fused_score, metadata))
        
        logger.debug(f"RRF 融合完成，最高分：{sorted_docs[0][1] if sorted_docs else 0:.4f}")
        return results
    
    def search_with_rerank(self, query: str, top_k: int = 5,
                           reranker=None) -> List[Tuple[Any, float, Dict]]:
        """
        带 Re-ranking 的混合检索
        
        Args:
            query: 查询文本
            top_k: 返回结果数量
            reranker: Re-ranker 实例（CrossEncoder）
        
        Returns:
            重排序后的结果
        """
        # 1. 先做混合检索（获取更多的候选）
        candidates = self.search(query, top_k=top_k * 3, return_scores=True)
        
        if not candidates or not reranker:
            # 如果没有重排序器，直接返回
            return candidates[:top_k]
        
        # 2. 使用 CrossEncoder 重排序
        try:
            from sentence_transformers import CrossEncoder
            
            # 准备输入对
            pairs = [[query, cand[0]] for cand in candidates]
            
            # 预测分数
            scores = reranker.predict(pairs)
            
            # 附加分数到结果
            reranked_results = []
            for (text, _, metadata), score in zip(candidates, scores):
                metadata['rerank_score'] = float(score)
                reranked_results.append((text, float(score), metadata))
            
            # 按新分数排序
            reranked_results.sort(key=lambda x: x[1], reverse=True)
            
            logger.info(f"Re-ranking 完成，返回前 {top_k} 条结果")
            return reranked_results[:top_k]
            
        except ImportError:
            logger.warning("未安装 CrossEncoder，跳过 Re-ranking。请安装：pip install sentence-transformers")
            return candidates[:top_k]
        except Exception as e:
            logger.error(f"Re-ranking 失败：{e}")
            return candidates[:top_k]


def create_hybrid_retriever(vector_store, bm25_retriever, vectorizer,
                           dense_weight: float = 0.6, 
                           sparse_weight: float = 0.4) -> HybridRetriever:
    """
    创建混合检索器的工厂函数
    
    Args:
        vector_store: FAISS 向量存储
        bm25_retriever: BM25 检索器
        vectorizer: 文本向量化器
        dense_weight: 密集检索权重
        sparse_weight: 稀疏检索权重
    
    Returns:
        HybridRetriever 实例
    """
    return HybridRetriever(
        vector_store=vector_store,
        bm25_retriever=bm25_retriever,
        vectorizer=vectorizer,
        dense_weight=dense_weight,
        sparse_weight=sparse_weight
    )


# 便捷的混合检索接口
def hybrid_search(query: str, 
                  vector_store=None,
                  bm25_retriever=None,
                  vectorizer=None,
                  top_k: int = 5,
                  use_rrf: bool = True) -> List[Tuple[str, float, Dict]]:
    """
    混合检索的便捷接口
    
    Args:
        query: 查询文本
        vector_store: FAISS 向量存储
        bm25_retriever: BM25 检索器
        vectorizer: 文本向量化器
        top_k: 返回结果数量
        use_rrf: 是否使用 RRF 融合
    
    Returns:
        [(text, score, metadata), ...]
    """
    if not use_rrf:
        # 只用向量检索
        if vector_store and vectorizer:
            query_vector = vectorizer.vectorize_text(query)
            return vector_store.search_similar(query_vector, top_k)
        else:
            return []
    
    # 使用混合检索
    retriever = create_hybrid_retriever(
        vector_store=vector_store,
        bm25_retriever=bm25_retriever,
        vectorizer=vectorizer
    )
    
    return retriever.search(query, top_k)
