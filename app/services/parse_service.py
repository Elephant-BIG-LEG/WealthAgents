from typing import List
from app.parse.parsing import parse_data

"""
解析服务模块
封装数据解析的核心功能，提供简单的调用接口
"""


def clean_and_parse_texts(texts: List[str]) -> List[str]:
    """
    清洗并解析文本列表
    
    Args:
        texts: 需要解析的原始文本列表
    
    Returns:
        清洗和解析后的文本列表
    """
    try:
        # 调用解析模块进行清洗
        cleaned_texts = parse_data(texts)
        return cleaned_texts
    except Exception as e:
        print(f"文本解析过程中出错: {e}")
        # 出错时尝试简单过滤
        filtered_texts = []
        for text in texts:
            if text and len(text.strip()) > 5:
                filtered_texts.append(text.strip())
        return filtered_texts[:20]