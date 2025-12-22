from typing import List
import numpy as np
from app.Embedding.Vectorization import TextVectorizer

"""
向量化服务模块
封装文本向量化的核心功能，提供简单的调用接口
"""

# 创建全局向量化器实例
vectorizer = TextVectorizer()


def vectorize_texts(texts: List[str]) -> List[np.ndarray]:
    """
    将文本列表向量化
    
    Args:
        texts: 需要向量化的文本列表
    
    Returns:
        向量化后的向量列表
    """
    try:
        vectors = vectorizer.vectorize_texts(texts)
        return vectors
    except Exception as e:
        print(f"向量化过程中出错: {e}")
        # 出错时返回空列表
        return []


def get_vector_similarity(vec1: np.ndarray, vec2: np.ndarray) -> float:
    """
    计算两个向量之间的余弦相似度
    
    Args:
        vec1: 第一个向量
        vec2: 第二个向量
    
    Returns:
        相似度值 (0-1)
    """
    try:
        return vectorizer.similarity(vec1, vec2)
    except Exception as e:
        print(f"计算相似度过程中出错: {e}")
        return 0.0