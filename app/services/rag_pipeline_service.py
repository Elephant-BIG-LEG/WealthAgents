"""
完整 RAG 流程服务：文档接入 → 递归/语义分块 → 768 维向量化 → 写入 FAISS → 查询检索 → 上下文生成
"""
from typing import List, Dict, Any, Optional, Tuple
import logging
import os

logger = logging.getLogger(__name__)

try:
    from app.config.config import (
        RAG_EMBEDDING_MODEL,
        RAG_EMBEDDING_DIM,
        RAG_CHUNK_SIZE,
        RAG_CHUNK_OVERLAP,
        RAG_TOP_K,
        RAG_USE_HYBRID,
        RAG_HYBRID_DENSE_WEIGHT,
        RAG_HYBRID_SPARSE_WEIGHT,
    )
except ImportError:
    RAG_EMBEDDING_MODEL = "shibing624/text2vec-base-chinese"
    RAG_EMBEDDING_DIM = 768
    RAG_CHUNK_SIZE = 600
    RAG_CHUNK_OVERLAP = 90
    RAG_TOP_K = 5
    RAG_USE_HYBRID = True
    RAG_HYBRID_DENSE_WEIGHT = 0.6
    RAG_HYBRID_SPARSE_WEIGHT = 0.4


class RAGPipelineService:
    """
    一站式 RAG：支持递归分块、语义分块、768 维 SBert、FAISS 存储、混合检索与上下文组装。
    """

    def __init__(
        self,
        dimension: int = RAG_EMBEDDING_DIM,
        embedding_model: str = RAG_EMBEDDING_MODEL,
        chunk_size: int = RAG_CHUNK_SIZE,
        chunk_overlap: int = RAG_CHUNK_OVERLAP,
        use_semantic_chunk: bool = True,
        storage_path: str = "faiss_database",
    ):
        self.dimension = dimension
        self.embedding_model = embedding_model
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.use_semantic_chunk = use_semantic_chunk
        self.storage_path = storage_path
        self._vector_store = None
        self._vectorizer = None
        self._splitter = None
        self._rag_retriever = None
        self._bm25_retriever = None

    def _get_vector_store(self):
        if self._vector_store is None:
            from app.store.faiss_store import FaissVectorStore
            self._vector_store = FaissVectorStore(
                dimension=self.dimension,
                storage_path=self.storage_path,
            )
        return self._vector_store

    def _get_vectorizer(self):
        if self._vectorizer is None:
            from app.Embedding.sbert_vectorization import SBertVectorizer
            self._vectorizer = SBertVectorizer(model_name=self.embedding_model)
        return self._vectorizer

    def _get_splitter(self):
        if self._splitter is None:
            if self.use_semantic_chunk:
                from app.chunk.semantic_splitter import SemanticRecursiveSplitter
                self._splitter = SemanticRecursiveSplitter(
                    chunk_size=self.chunk_size,
                    chunk_overlap=self.chunk_overlap,
                    use_embedding=True,
                    embedding_model=self.embedding_model,
                )
            else:
                from app.chunk.splitter import FinancialTextSplitter
                self._splitter = FinancialTextSplitter(
                    chunk_size=self.chunk_size,
                    chunk_overlap=self.chunk_overlap,
                )
        return self._splitter

    def ingest_documents(
        self,
        documents: List[Dict[str, Any]],
        text_key: str = "text",
        source_key: str = "source",
    ) -> Dict[str, Any]:
        """
        接入文档：分块 → 768 维向量化 → 写入 FAISS。
        documents: [{"text": "...", "source": "optional"}, ...]
        """
        store = self._get_vector_store()
        vectorizer = self._get_vectorizer()
        splitter = self._get_splitter()
        all_texts: List[str] = []
        all_meta: List[Dict[str, Any]] = []
        for doc in documents:
            text = doc.get(text_key) or doc.get("content", "")
            if not text or not str(text).strip():
                continue
            source = doc.get(source_key, "unknown")
            chunks = splitter.split_text(text, metadata={"source": source})
            for c in chunks:
                txt = c.text if hasattr(c, "text") else str(c)
                meta = c.metadata if hasattr(c, "metadata") else {"source": source}
                all_texts.append(txt)
                all_meta.append(meta)
        if not all_texts:
            return {"status": "success", "chunks_added": 0, "message": "无有效文本"}
        vectors = vectorizer.vectorize_texts(all_texts, normalize=True)
        store.add_vectors(all_texts, vectors, source="rag_pipeline")
        logger.info(f"RAG 接入完成：{len(all_texts)} 块已写入向量库")
        return {"status": "success", "chunks_added": len(all_texts)}

    def query(
        self,
        query: str,
        top_k: int = RAG_TOP_K,
        return_context: bool = True,
        use_hybrid: Optional[bool] = None,
    ) -> Any:
        """
        查询：向量/混合检索 → 可选返回组装后的上下文字符串。
        use_hybrid: None 时根据配置与查询长度自动决定是否使用混合检索。
        """
        store = self._get_vector_store()
        if use_hybrid is None:
            use_hybrid = RAG_USE_HYBRID and self._should_use_hybrid(query)
        if use_hybrid:
            retriever = self._get_enhanced_rag_retriever()
            if retriever:
                return retriever.retrieve(query, top_k=top_k, return_context=return_context)
        vectorizer = self._get_vectorizer()
        qv = vectorizer.vectorize_text(query)
        results = store.search_similar(qv, top_k)
        if return_context:
            from app.retrieval.context_assembler import ContextAssembler
            assembler = ContextAssembler(max_tokens=2000)
            return assembler.assemble(results, query=query)
        return results

    def _should_use_hybrid(self, query: str) -> bool:
        """混合检索触发：查询较长或包含多个词时倾向使用混合检索。"""
        q = (query or "").strip()
        if len(q) <= 10:
            return False
        token_count = len(q) + sum(1 for c in q if c in " \t\n，。！？")
        return token_count >= 15 or len(q) > 30

    def _get_enhanced_rag_retriever(self):
        if self._rag_retriever is None:
            try:
                from app.retrieval.enhanced_rag_retriever import EnhancedRAGRetriever
                store = self._get_vector_store()
                self._rag_retriever = EnhancedRAGRetriever(
                    vector_store=store,
                    model_name=self.embedding_model,
                    enable_hybrid=True,
                    dense_weight=RAG_HYBRID_DENSE_WEIGHT,
                    sparse_weight=RAG_HYBRID_SPARSE_WEIGHT,
                )
            except Exception as e:
                logger.warning(f"EnhancedRAGRetriever 初始化失败: {e}")
        return self._rag_retriever


def get_default_rag_pipeline(
    use_semantic_chunk: bool = True,
) -> RAGPipelineService:
    """获取默认 RAG 流水线（768 维 + 可选语义分块）。"""
    return RAGPipelineService(
        dimension=RAG_EMBEDDING_DIM,
        embedding_model=RAG_EMBEDDING_MODEL,
        chunk_size=RAG_CHUNK_SIZE,
        chunk_overlap=RAG_CHUNK_OVERLAP,
        use_semantic_chunk=use_semantic_chunk,
    )
