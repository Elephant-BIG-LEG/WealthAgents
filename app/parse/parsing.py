import re
import sys
import os

# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


"""
解析 & 清洗数据
TODO
效果不好：无效信息没有过滤、数据没有结构化
"""


def parse_data(link_texts) -> list[str]:
    cleaned_texts = []
    for text in link_texts:
        # 清理HTML标签
        clean_text = re.sub(r'<[^>]+>', '', text).strip()
        if clean_text and len(clean_text) > 5:  # 过滤掉太短的文本
            cleaned_texts.append(clean_text)

    # TODO 返回的数据大小可修改
    return cleaned_texts[:20]  # 返回前20个文本
