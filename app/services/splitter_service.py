from typing import List
from app.chunk.splitter import FinancialTextSplitter

"""
切片服务模块
封装文本切片的核心功能，提供简单的调用接口
"""

# 创建全局切片器实例
splitter = FinancialTextSplitter(
    chunk_size=600,
    chunk_overlap=100,
    min_chunk_size=200,
    preserve_sections=True,
    preserve_tables=True,
    dynamic_chunking=True
)


def split_text(text: str) -> List[str]:
    """
    将文本分割成多个切片
    
    Args:
        text: 需要分割的文本
    
    Returns:
        切片后的文本列表
    """
    try:
        chunks = splitter.split_text(text)
        return chunks
    except Exception as e:
        print(f"文本切片过程中出错: {e}")
        # 出错时返回原文本作为单个切片
        return [text] if text else []


def split_texts(texts: List[str]) -> List[str]:
    """
    将多个文本分割成多个切片
    
    Args:
        texts: 需要分割的文本列表
    
    Returns:
        所有切片合并后的列表
    """
    all_chunks = []
    for text in texts:
        chunks = split_text(text)
        all_chunks.extend(chunks)
    return all_chunks