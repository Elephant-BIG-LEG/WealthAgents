"""
增强版 RAG 检索接口
整合 SBERT 向量化、BM25 检索、混合检索、Re-ranking 和智能上下文组装
"""
from typing import List, Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)


class EnhancedRAGRetriever:
    """
    增强版 RAG 检索器 - 提供一站式检索服务
    
    功能整合：
    1. SBERT 语义向量化
    2. BM25 关键词检索
    3. 混合检索（RRF 融合）
    4. Re-ranking 重排序
    5. 查询改写和扩展
    6. 智能上下文组装
    """
    
    def __init__(self, 
                 vector_store=None,
                 model_name: str = 'shibing624/text2vec-base-chinese',
                 enable_hybrid: bool = True,
                 enable_rerank: bool = False,
                 enable_query_rewrite: bool = True,
                 dense_weight: float = 0.6,
                 sparse_weight: float = 0.4):
        """
        初始化增强版 RAG 检索器
        
        Args:
            vector_store: FAISS 向量存储实例
            model_name: SBERT 模型名称
            enable_hybrid: 是否启用混合检索
            enable_rerank: 是否启用 Re-ranking
            enable_query_rewrite: 是否启用查询改写
            dense_weight: 密集检索权重
            sparse_weight: 稀疏检索权重
        """
        self.vector_store = vector_store
        self.model_name = model_name
        self.enable_hybrid = enable_hybrid
        self.enable_rerank = enable_rerank
        self.enable_query_rewrite = enable_query_rewrite
        self.dense_weight = dense_weight
        self.sparse_weight = sparse_weight
        
        # 延迟加载组件
        self.vectorizer = None
        self.bm25_retriever = None
        self.hybrid_retriever = None
        self.query_rewriter = None
        self.reranker = None
        self.context_assembler = None
        
        logger.info("增强版 RAG 检索器初始化完成")
    
    def _lazy_init(self):
        """延迟加载各组件（避免首次调用时卡顿）"""
        if self.vectorizer is None:
            try:
                from app.Embedding.sbert_vectorization import SBertVectorizer
                self.vectorizer = SBertVectorizer(model_name=self.model_name)
                logger.info("SBERT 向量化器加载成功")
            except Exception as e:
                logger.error(f"SBERT 向量化器加载失败：{e}")
                raise
        
        if self.enable_hybrid and self.bm25_retriever is None:
            try:
                from app.retrieval.bm25_retriever import BM25Retriever
                from app.retrieval.hybrid_retriever import HybridRetriever
                
                # 从 vector_store 提取元数据建立 BM25 索引
                if hasattr(self.vector_store, 'metadata') and len(self.vector_store.metadata) > 0:
                    documents = [(i, meta['text']) for i, meta in enumerate(self.vector_store.metadata)]
                    self.bm25_retriever = BM25Retriever()
                    self.bm25_retriever.add_documents(documents)
                    logger.info(f"BM25 检索器加载成功，索引文档数：{len(documents)}")
                
                # 创建混合检索器
                self.hybrid_retriever = HybridRetriever(
                    vector_store=self.vector_store,
                    bm25_retriever=self.bm25_retriever,
                    vectorizer=self.vectorizer,
                    dense_weight=self.dense_weight,
                    sparse_weight=self.sparse_weight
                )
                logger.info("混合检索器创建成功")
            except Exception as e:
                logger.warning(f"BM25 或混合检索器加载失败：{e}，将只使用向量检索")
                self.enable_hybrid = False
        
        if self.enable_rerank and self.reranker is None:
            try:
                from sentence_transformers import CrossEncoder
                self.reranker = CrossEncoder('cross-encoder/ms-marco-TinyBERT-L-2-v2')
                logger.info("Re-ranker 加载成功")
            except Exception as e:
                logger.warning(f"Re-ranker 加载失败：{e}，将跳过 Re-ranking")
                self.enable_rerank = False
        
        if self.enable_query_rewrite and self.query_rewriter is None:
            try:
                from app.retrieval.query_optimizer import QueryRewriter
                self.query_rewriter = QueryRewriter()
                logger.info("查询改写器加载成功")
            except Exception as e:
                logger.warning(f"查询改写器加载失败：{e}")
                self.enable_query_rewrite = False
        
        if self.context_assembler is None:
            try:
                from app.retrieval.context_assembler import ContextAssembler
                self.context_assembler = ContextAssembler(max_tokens=2000)
                logger.info("上下文组装器加载成功")
            except Exception as e:
                logger.warning(f"上下文组装器加载失败：{e}")
    
    def _should_use_hybrid(self, query: str) -> bool:
        """混合检索触发：查询较长或含多词时使用 BM25+向量 RRF 融合。"""
        q = (query or "").strip()
        if len(q) <= 8:
            return False
        return len(q) > 25 or (q.count(" ") + q.count("，") + q.count("、")) >= 2
    
    def retrieve(self, query: str, top_k: int = 5, 
                 return_context: bool = True,
                 filters: Dict[str, Any] = None) -> Any:
        """
        执行 RAG 检索
        
        Args:
            query: 查询文本
            top_k: 返回结果数量
            return_context: 是否返回组装后的上下文（否则返回原始结果列表）
            filters: 过滤器字典
        
        Returns:
            如果 return_context=True: 组装后的上下文字符串
            否则：[(text, score, metadata), ...]
        """
        # 延迟加载组件
        self._lazy_init()
        
        # 0. 混合检索触发：查询较长或词数多时用混合检索
        use_hybrid_this_call = self.enable_hybrid and self._should_use_hybrid(query)
        
        # 1. 查询改写（可选）
        queries_to_search = [query]
        if self.enable_query_rewrite and self.query_rewriter:
            expanded_queries = self.query_rewriter.expand_query(query, num_expansions=2)
            queries_to_search = expanded_queries[:3]  # 最多 3 个查询版本
            logger.info(f"查询扩展：'{query}' -> {len(queries_to_search)} 个版本")
        
        # 2. 执行检索
        all_results = []
        
        for q in queries_to_search:
            if use_hybrid_this_call and self.hybrid_retriever:
                # 混合检索（BM25 + 向量 + RRF）
                results = self.hybrid_retriever.search(q, top_k=top_k * 2)
            else:
                # 纯向量检索
                query_vector = self.vectorizer.vectorize_text(q)
                results = self.vector_store.search_similar(query_vector, top_k * 2, filters=filters)
            
            all_results.extend(results)
        
        # 3. 去重和排序
        unique_results = self._deduplicate_and_sort(all_results, top_k)
        
        # 4. Re-ranking（可选）
        if self.enable_rerank and self.reranker and len(unique_results) > 0:
            unique_results = self._rerank(query, unique_results)
        
        # 5. 应用过滤器
        if filters:
            filtered_results = []
            for text, score, metadata in unique_results:
                # 使用 vector_store 的过滤方法
                if hasattr(self.vector_store, '_apply_filters'):
                    if self.vector_store._apply_filters(metadata, score, filters):
                        filtered_results.append((text, score, metadata))
                else:
                    filtered_results.append((text, score, metadata))
            unique_results = filtered_results[:top_k]
        
        # 6. 返回结果
        if return_context and self.context_assembler:
            context = self.context_assembler.assemble(unique_results, query=query)
            return context
        else:
            return unique_results[:top_k]
    
    def _deduplicate_and_sort(self, results: List[Tuple], top_k: int) -> List[Tuple]:
        """去重并排序"""
        seen_hashes = set()
        deduplicated = []
        
        # 按分数降序排序
        results.sort(key=lambda x: x[1], reverse=True)
        
        for text, score, metadata in results:
            text_hash = hash(text[:100])
            if text_hash not in seen_hashes:
                deduplicated.append((text, score, metadata))
                seen_hashes.add(text_hash)
        
        return deduplicated[:top_k * 3]  # 保留更多用于后续处理
    
    def _rerank(self, query: str, results: List[Tuple]) -> List[Tuple]:
        """使用 CrossEncoder 进行重排序"""
        try:
            pairs = [[query, text] for text, _, _ in results]
            scores = self.reranker.predict(pairs)
            
            reranked = []
            for (text, old_score, metadata), new_score in zip(results, scores):
                metadata['rerank_score'] = float(new_score)
                reranked.append((text, float(new_score), metadata))
            
            reranked.sort(key=lambda x: x[1], reverse=True)
            
            logger.info(f"Re-ranking 完成，最高分：{reranked[0][1] if reranked else 0:.4f}")
            return reranked
            
        except Exception as e:
            logger.error(f"Re-ranking 失败：{e}")
            return results
    
    def retrieve_with_metadata_filter(self, query: str, top_k: int = 5,
                                      source_filter: str = None,
                                      min_similarity: float = 0.3,
                                      date_range: tuple = None) -> Any:
        """
        带元数据过滤的检索便捷接口
        
        Args:
            query: 查询文本
            top_k: 返回结果数量
            source_filter: 来源过滤（可以是字符串或列表）
            min_similarity: 最小相似度阈值
            date_range: 日期范围 (start_date, end_date)
        
        Returns:
            检索结果
        """
        filters = {}
        
        if source_filter:
            filters['source'] = source_filter
        
        if min_similarity is not None:
            filters['min_similarity'] = min_similarity
        
        if date_range:
            filters['date_range'] = date_range
        
        return self.retrieve(query, top_k, filters=filters)


# 创建全局 RAG 检索器实例的工厂函数
def create_enhanced_rag_retriever(vector_store, **kwargs) -> EnhancedRAGRetriever:
    """
    创建增强版 RAG 检索器的工厂函数
    
    Args:
        vector_store: FAISS 向量存储实例
        **kwargs: 其他配置参数
    
    Returns:
        EnhancedRAGRetriever 实例
    """
    return EnhancedRAGRetriever(vector_store=vector_store, **kwargs)


# 便捷的检索接口
def enhanced_rag_search(query: str, 
                       vector_store=None,
                       top_k: int = 5,
                       return_context: bool = True,
                       **kwargs) -> Any:
    """
    增强版 RAG 检索的便捷接口
    
    Args:
        query: 查询文本
        vector_store: FAISS 向量存储
        top_k: 返回结果数量
        return_context: 是否返回上下文
        **kwargs: 其他配置参数
    
    Returns:
        检索结果或组装后的上下文
    """
    retriever = create_enhanced_rag_retriever(vector_store, **kwargs)
    return retriever.retrieve(query, top_k, return_context=return_context)
