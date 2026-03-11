"""
增强版文本向量化模块
基于 Sentence-BERT 的语义向量化，支持中文金融领域
"""
import numpy as np
from typing import List, Union, Optional
import logging
import os

logger = logging.getLogger(__name__)

class SBertVectorizer:
    """
    基于 Sentence-BERT 的文本向量化器
    
    特性：
    1. 语义理解能力强，能捕捉上下文关系
    2. 支持多语言（中文优化）
    3. 768 维丰富语义表达
    4. 缓存机制避免重复计算
    """
    
    def __init__(self, model_name: str = 'shibing624/text2vec-base-chinese', cache_enabled: bool = True):
        """
        初始化 SBERT 向量化器
        
        Args:
            model_name: Sentence-BERT 模型名称
                可选：
                - 'shibing624/text2vec-base-chinese': 中文通用（推荐）
                - 'GanymedeNil/text2vec-large-chinese': 中文大型模型
                - 'paraphrase-multilingual-MiniLM-L12-v2': 多语言
            cache_enabled: 是否启用缓存
        """
        self.model_name = model_name
        self.cache_enabled = cache_enabled
        self.cache_file = "sbert_vector_cache.pkl"
        self.vector_cache = {}
        
        # 延迟加载模型
        self.model = None
    
    def _load_model(self):
        """加载 Sentence-BERT 模型"""
        if self.model is None:
            try:
                from sentence_transformers import SentenceTransformer
                logger.info(f"正在加载 Sentence-BERT 模型：{self.model_name}")
                self.model = SentenceTransformer(self.model_name)
                logger.info("模型加载成功")
            except ImportError:
                logger.error("未安装 sentence-transformers，请运行：pip install sentence-transformers")
                raise
            except Exception as e:
                logger.error(f"加载模型失败：{e}")
                raise
        
        return self.model
    
    def _load_cache(self):
        """加载向量缓存"""
        import pickle
        if os.path.exists(self.cache_file):
            try:
                with open(self.cache_file, 'rb') as f:
                    self.vector_cache = pickle.load(f)
                logger.info(f"加载了 {len(self.vector_cache)} 条向量缓存")
            except Exception as e:
                logger.warning(f"加载缓存失败：{e}")
                self.vector_cache = {}
    
    def _save_cache(self):
        """保存向量缓存"""
        import pickle
        if not self.cache_enabled:
            return
        
        try:
            with open(self.cache_file, 'wb') as f:
                pickle.dump(self.vector_cache, f)
            logger.info(f"已保存 {len(self.vector_cache)} 条向量到缓存")
        except Exception as e:
            logger.warning(f"保存缓存失败：{e}")
    
    def vectorize_text(self, text: str, normalize: bool = True) -> np.ndarray:
        """
        将单个文本转换为向量
        
        Args:
            text: 输入文本
            normalize: 是否归一化向量（用于余弦相似度）
        
        Returns:
            文本的向量表示 (768 维)
        """
        if not text or len(text.strip()) == 0:
            return np.zeros(768)
        
        # 检查缓存
        if self.cache_enabled and text in self.vector_cache:
            logger.debug(f"使用缓存向量：{text[:50]}...")
            return self.vector_cache[text]
        
        # 加载模型（首次调用时）
        model = self._load_model()
        
        # 生成向量
        try:
            embedding = model.encode(text, convert_to_numpy=True, show_progress_bar=False)
            
            # 归一化（用于余弦相似度计算）
            if normalize:
                norm = np.linalg.norm(embedding)
                if norm > 0:
                    embedding = embedding / norm
            
            # 缓存结果
            if self.cache_enabled:
                self.vector_cache[text] = embedding
                self._save_cache()
            
            return embedding
            
        except Exception as e:
            logger.error(f"向量化失败：{e}")
            return np.zeros(768)
    
    def vectorize_texts(self, texts: List[str], normalize: bool = True, 
                       batch_size: int = 32, show_progress: bool = False) -> List[np.ndarray]:
        """
        批量向量化文本
        
        Args:
            texts: 文本列表
            normalize: 是否归一化
            batch_size: 批次大小
            show_progress: 是否显示进度条
        
        Returns:
            向量列表
        """
        if not texts:
            return []
        
        # 分离已缓存和未缓存的文本
        cached_vectors = []
        texts_to_process = []
        indices_map = []  # 记录原始索引
        
        for i, text in enumerate(texts):
            if self.cache_enabled and text in self.vector_cache:
                cached_vectors.append((i, self.vector_cache[text]))
            else:
                texts_to_process.append(text)
                indices_map.append(i)
        
        logger.info(f"总共 {len(texts)} 条文本，{len(cached_vectors)} 条来自缓存，{len(texts_to_process)} 条需要处理")
        
        # 批量处理未缓存的文本
        processed_vectors = []
        if texts_to_process:
            model = self._load_model()
            
            # 分批处理以节省内存
            for i in range(0, len(texts_to_process), batch_size):
                batch = texts_to_process[i:i + batch_size]
                batch_embeddings = model.encode(
                    batch, 
                    convert_to_numpy=True,
                    show_progress_bar=show_progress and (i == 0)
                )
                
                # 归一化
                if normalize:
                    norms = np.linalg.norm(batch_embeddings, axis=1, keepdims=True)
                    norms[norms == 0] = 1  # 避免除零
                    batch_embeddings = batch_embeddings / norms
                
                processed_vectors.extend(batch_embeddings)
                
                # 添加到缓存
                if self.cache_enabled:
                    for j, text in enumerate(batch):
                        self.vector_cache[text] = processed_vectors[-(len(batch) - j)]
                    self._save_cache()
        
        # 合并结果（保持原始顺序）
        final_vectors = [None] * len(texts)
        
        # 填充缓存的结果
        for idx, vector in cached_vectors:
            final_vectors[idx] = vector
        
        # 填充新处理的结果
        for idx, vector in zip(indices_map, processed_vectors):
            final_vectors[idx] = vector
        
        return final_vectors
    
    def similarity(self, vec1: np.ndarray, vec2: np.ndarray) -> float:
        """
        计算两个向量之间的余弦相似度
        
        Args:
            vec1: 第一个向量
            vec2: 第二个向量
        
        Returns:
            相似度值 (-1 到 1 之间，归一化后为 0 到 1)
        """
        try:
            # 如果未归一化，先归一化
            if np.linalg.norm(vec1) > 1.01:  # 允许小的浮点误差
                vec1 = vec1 / np.linalg.norm(vec1)
            if np.linalg.norm(vec2) > 1.01:
                vec2 = vec2 / np.linalg.norm(vec2)
            
            # 计算余弦相似度
            sim = float(np.dot(vec1, vec2))
            
            # 限制在 [-1, 1] 范围内
            sim = max(-1.0, min(1.0, sim))
            
            return sim
            
        except Exception as e:
            logger.error(f"计算相似度失败：{e}")
            return 0.0
    
    def find_similar_texts(self, query_text: str, candidate_texts: List[str], 
                          top_k: int = 5) -> List[tuple]:
        """
        在候选文本中查找与查询文本最相似的文本
        
        Args:
            query_text: 查询文本
            candidate_texts: 候选文本列表
            top_k: 返回最相似的前 k 个结果
        
        Returns:
            (文本，相似度，索引) 的元组列表
        """
        try:
            # 向量化查询文本
            query_vector = self.vectorize_text(query_text)
            
            # 批量向量化候选文本
            candidate_vectors = self.vectorize_texts(candidate_texts)
            
            # 计算相似度
            similarities = []
            for i, (text, vector) in enumerate(zip(candidate_texts, candidate_vectors)):
                sim = self.similarity(query_vector, vector)
                similarities.append((text, sim, i))
            
            # 按相似度排序并返回 top_k
            similarities.sort(key=lambda x: x[1], reverse=True)
            return similarities[:top_k]
            
        except Exception as e:
            logger.error(f"查找相似文本失败：{e}")
            return [(text, 0.0, i) for i, text in enumerate(candidate_texts[:top_k])]


# 创建全局向量化器实例
global_sbert_vectorizer = SBertVectorizer(
    model_name='shibing624/text2vec-base-chinese',
    cache_enabled=True
)


def create_sbert_vectorizer(model_name: str = 'shibing624/text2vec-base-chinese', 
                           cache_enabled: bool = True) -> SBertVectorizer:
    """
    创建 SBERT 向量化器实例
    
    Args:
        model_name: 模型名称
        cache_enabled: 是否启用缓存
    
    Returns:
        SBertVectorizer 实例
    """
    return SBertVectorizer(model_name=model_name, cache_enabled=cache_enabled)


def vectorize_data_sbert(texts: List[str], **kwargs) -> List[np.ndarray]:
    """
    向量化数据的主要接口函数（SBERT 版本）
    
    Args:
        texts: 需要向量化的文本列表
        **kwargs: 传递给 vectorize_texts 的参数
    
    Returns:
        向量列表
    """
    if not texts:
        return []
    
    try:
        # 使用全局实例
        return global_sbert_vectorizer.vectorize_texts(texts, **kwargs)
    except Exception as e:
        logger.error(f"向量化过程中出错：{e}")
        # 出错时返回空向量列表
        return [np.zeros(768) for _ in texts]
