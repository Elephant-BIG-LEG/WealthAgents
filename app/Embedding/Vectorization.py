import numpy as np
from typing import List, Union
import hashlib
import pickle
import os

"""
TODO
文本向量化
"""

class TextVectorizer:
    """文本向量化类，用于将文本转换为向量表示"""

    def __init__(self, vector_dim: int = 128):
        """
        初始化向量化器
        :param vector_dim: 向量维度
        """
        self.vector_dim = vector_dim
        self.cache_file = "vector_cache.pkl"
        self.vector_cache = self._load_cache()

    def _load_cache(self):
        """加载向量缓存"""
        if os.path.exists(self.cache_file):
            try:
                with open(self.cache_file, 'rb') as f:
                    return pickle.load(f)
            except:
                return {}
        return {}

    def _save_cache(self):
        """保存向量缓存"""
        with open(self.cache_file, 'wb') as f:
            pickle.dump(self.vector_cache, f)

    def _hash_text(self, text: str) -> str:
        """对文本进行哈希处理，用于缓存键"""
        return hashlib.md5(text.encode('utf-8')).hexdigest()

    def _simple_hash_vector(self, text: str) -> np.ndarray:
        """
        使用简单的哈希方法将文本转换为向量
        这是一种简化的向量化方法，实际项目中可以替换为更复杂的模型
        """
        # 使用哈希值生成确定性的向量
        hash_val = self._hash_text(text)

        # 将哈希值转换为数字并生成向量
        vector = np.zeros(self.vector_dim)
        for i in range(min(len(hash_val), self.vector_dim)):
            # 使用哈希字符的ASCII值作为种子生成伪随机数
            np.random.seed(ord(hash_val[i]) + i)
            vector[i] = np.random.rand()

        # 归一化向量
        norm = np.linalg.norm(vector)
        if norm > 0:
            vector = vector / norm

        return vector

    def vectorize_text(self, text: str) -> np.ndarray:
        """
        将单个文本转换为向量
        :param text: 输入文本
        :return: 文本的向量表示
        """
        # 检查缓存
        text_hash = self._hash_text(text)
        if text_hash in self.vector_cache:
            return self.vector_cache[text_hash]

        # 生成向量
        vector = self._simple_hash_vector(text)

        # 缓存结果
        self.vector_cache[text_hash] = vector
        self._save_cache()

        return vector

    def vectorize_texts(self, texts: List[str]) -> List[np.ndarray]:
        """
        将多个文本转换为向量
        :param texts: 输入文本列表
        :return: 文本向量列表
        """
        return [self.vectorize_text(text) for text in texts]

    def similarity(self, vec1: np.ndarray, vec2: np.ndarray) -> float:
        """
        计算两个向量之间的余弦相似度
        :param vec1: 第一个向量
        :param vec2: 第二个向量
        :return: 余弦相似度 (0-1之间)
        """
        # 确保向量归一化
        vec1_norm = vec1 / np.linalg.norm(vec1)
        vec2_norm = vec2 / np.linalg.norm(vec2)

        # 计算余弦相似度
        return float(np.dot(vec1_norm, vec2_norm))

    def find_similar_texts(self, query_text: str, candidate_texts: List[str], top_k: int = 5) -> List[tuple]:
        """
        在候选文本中查找与查询文本最相似的文本
        :param query_text: 查询文本
        :param candidate_texts: 候选文本列表
        :param top_k: 返回最相似的前k个结果
        :return: (文本, 相似度) 的元组列表
        """
        # 向量化查询文本
        query_vector = self.vectorize_text(query_text)

        # 向量化候选文本
        candidate_vectors = self.vectorize_texts(candidate_texts)

        # 计算相似度
        similarities = []
        for i, (text, vector) in enumerate(zip(candidate_texts, candidate_vectors)):
            sim = self.similarity(query_vector, vector)
            similarities.append((text, sim, i))

        # 按相似度排序并返回top_k
        similarities.sort(key=lambda x: x[1], reverse=True)
        return similarities[:top_k]


def vectorize_data(texts: List[str]) -> List[np.ndarray]:
    """
    向量化数据的主要接口函数
    :param texts: 需要向量化的文本列表
    :return: 向量列表
    """
    vectorizer = TextVectorizer()
    return vectorizer.vectorize_texts(texts)


def save_vectors_to_file(vectors: List[np.ndarray], filename: str):
    """
    将向量保存到文件
    :param vectors: 向量列表
    :param filename: 保存文件名
    """
    with open(filename, 'wb') as f:
        pickle.dump(vectors, f)


def load_vectors_from_file(filename: str) -> List[np.ndarray]:
    """
    从文件加载向量
    :param filename: 文件名
    :return: 向量列表
    """
    with open(filename, 'rb') as f:
        return pickle.load(f)
