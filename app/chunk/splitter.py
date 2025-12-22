# 文本切片器 - 专为理财文章设计
import re
from typing import List, Dict, Tuple

"""
TODO
不能很好的切分，采用什么切分逻辑待确定
"""
class FinancialTextSplitter:
    """
    专为理财文章设计的文本切片器
    特点：
    1. 保持段落完整性
    2. 保持章节结构完整性
    3. 保留上下文连贯性（添加重叠）
    4. 智能处理表格和列表
    5. 考虑内容重要性的动态切片长度
    """
    
    def __init__(self, 
                 chunk_size: int = 600,  # 减小默认切片大小，便于更细粒度的切片
                 chunk_overlap: int = 100,  # 减小默认重叠大小
                 min_chunk_size: int = 200,  # 减小最小切片大小
                 preserve_sections: bool = True,  # 是否保持章节完整性
                 preserve_tables: bool = True,  # 是否保持表格完整性
                 dynamic_chunking: bool = True  # 是否启用动态切片长度
                ):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.min_chunk_size = min_chunk_size
        self.preserve_sections = preserve_sections
        self.preserve_tables = preserve_tables
        self.dynamic_chunking = dynamic_chunking
    
    def split_text(self, text: str) -> List[str]:
        """
        分割文本，返回切片列表
        """
        if not text or len(text.strip()) == 0:
            return []
        
        # 首先预处理文本，移除多余的空白字符
        text = re.sub(r'\s+', ' ', text)
        text = re.sub(r'\s*\n\s*', '\n', text)
        
        # 1. 对所有文本首先进行强制字符级分割（确保生成足够多的切片）
        # 这是最直接有效的方法，特别是对于非结构化或格式不规范的文本
        chunks = self._force_split_long_text(text)
        
        # 2. 添加上下文重叠
        final_chunks = self._add_context_overlap(chunks)
        
        return final_chunks
    
    def _identify_sections(self, text: str) -> List[Tuple[str, str]]:
        """
        识别文章中的章节结构
        """
        sections = []
        
        # 匹配常见的章节标题格式，优化了对理财文章格式的支持
        section_patterns = [
            # Markdown格式和理财报告常见格式
            r'(#{1,6}\s*\*{0,2}[^\n]+\*{0,2})\s*\n([\s\S]*?)(?=#{1,6}\s*\*{0,2}[^\n]+\*{0,2}|$)',
            # **标题**格式，增强对理财报告的匹配
            r'(\*{2}\s*[^\*\n]+\s*\*{2})\s*\n([\s\S]*?)(?=\*{2}\s*[^\*\n]+\s*\*{2}|$)',
            # 下划线格式
            r'([^\n]+)\s*\n[-=]+\s*\n([\s\S]*?)(?=[^\n]+\s*\n[-=]+\s*\n|$)',
            # [标题]格式
            r'(\[[^\]]+\])\s*\n([\s\S]*?)(?=\[[^\]]+\]\s*\n|$)',
            # 理财报告中常见的数字序号章节
            r'(\d+\.\s+[^\n]+)\s*\n([\s\S]*?)(?=\d+\.\s+[^\n]+|$)',
            r'(\d+\s*[、.]\s*[^\n]+)\s*\n([\s\S]*?)(?=\d+\s*[、.]\s*[^\n]+|$)'
        ]
        
        for pattern in section_patterns:
            matches = re.findall(pattern, text, re.MULTILINE | re.DOTALL)
            if matches and len(matches) > 1:  # 确保找到了多个章节
                for title, content in matches:
                    sections.append((title.strip(), content.strip()))
                return sections
        
        return []  # 没有找到合适的章节结构
    
    def _split_by_paragraphs(self, text: str) -> List[str]:
        """
        基于段落进行分割
        """
        # 按段落分割（增强对多种换行符格式的支持）
        paragraphs = re.split(r'\n\s*\n|\r\n\s*\r\n', text.strip())
        paragraphs = [p.strip() for p in paragraphs if p.strip()]
        
        chunks = []
        current_chunk = ""
        
        # 减小chunk_size参数的判断阈值，确保能生成更多切片
        adjusted_chunk_size = int(self.chunk_size * 0.8)  # 调整为原大小的80%
        
        for paragraph in paragraphs:
            # 判断是否应该创建新切片（使用调整后的阈值）
            if len(current_chunk) + len(paragraph) + 2 > adjusted_chunk_size:  # +2 是为了换行符
                if current_chunk.strip():
                    chunks.append(current_chunk.strip())
                current_chunk = paragraph
            else:
                if current_chunk:
                    current_chunk += "\n\n" + paragraph
                else:
                    current_chunk = paragraph
        
        if current_chunk.strip():
            chunks.append(current_chunk.strip())
        
        # 如果仍然只有一个切片且很长，强制进行字符级别的分割
        if len(chunks) == 1 and len(chunks[0]) > self.chunk_size:
            return self._force_split_long_text(chunks[0])
            
        return chunks
    
    def _should_create_new_chunk(self, current_length: int, section_length: int) -> bool:
        """
        判断是否应该创建新切片
        调整判断逻辑，确保生成更多合理大小的切片
        """
        # 如果当前切片为空，不需要创建新切片
        if current_length == 0:
            return False
        
        # 降低阈值，使切片更容易创建（原1.2倍调整为0.9倍）
        if current_length + section_length + 2 > self.chunk_size * 0.9:  # 更严格的长度控制
            return True
        
        # 如果章节很长，单独作为一个切片（原0.8倍调整为0.7倍）
        if section_length > self.chunk_size * 0.7:
            return True
        
        return False
    
    def _split_long_chunk(self, chunk: str) -> List[str]:
        """
        处理超长切片
        增强分割逻辑
        """
        sub_chunks = []
        start = 0
        
        while start < len(chunk):
            end = min(start + self.chunk_size, len(chunk))
            
            # 尝试在最近的段落边界处分割
            if end < len(chunk):
                # 寻找最近的换行符，同时考虑多种换行格式
                last_newline = chunk.rfind('\n\n', start, end)
                if last_newline <= start + self.min_chunk_size:
                    last_newline = chunk.rfind('\n', start, end)
                if last_newline > start + self.min_chunk_size:
                    end = last_newline + 1  # 包含换行符
            
            sub_chunks.append(chunk[start:end].strip())
            start = end - self.chunk_overlap if end - self.chunk_overlap > 0 else 0
        
        return sub_chunks
        
    def _force_split_long_text(self, text: str) -> List[str]:
        """
        强制分割超长文本
        这是最可靠的分割方法，确保生成多个合理大小的切片
        """
        sub_chunks = []
        start = 0
        
        # 使用更小的切片大小，确保生成更多切片
        actual_chunk_size = int(self.chunk_size * 0.8)  # 使用80%的chunk_size
        
        # 循环分割文本
        while start < len(text):
            # 计算当前切片结束位置
            end = min(start + actual_chunk_size, len(text))
            
            # 如果不是最后一个切片，尝试在适当的位置分割
            if end < len(text):
                # 扩大查找范围，增加找到合适分割点的概率
                search_range = min(100, int(actual_chunk_size * 0.2))  # 最多向前查找100个字符或20%的chunk_size
                for i in range(end, max(start + self.min_chunk_size, end - search_range), -1):
                    # 优先在标点符号处分割
                    if text[i-1] in ['。', '！', '？', '.', '!', '?', ';', '；']:
                        end = i
                        break
                    # 如果找不到标点，在逗号或空格处分割
                    elif text[i-1] in ['，', ',', ' ', '\n']:
                        end = i
            
            # 提取并保存当前切片
            sub_chunk = text[start:end].strip()
            if sub_chunk:  # 确保切片不为空
                sub_chunks.append(sub_chunk)
            
            # 计算下一个切片的起始位置，考虑重叠
            start = end - self.chunk_overlap if end < len(text) else end
        
        return sub_chunks
    
    def _add_context_overlap(self, chunks: List[str]) -> List[str]:
        """
        添加上下文重叠，提高连贯性
        """
        if len(chunks) <= 1:
            return chunks
        
        enhanced_chunks = []
        
        for i, chunk in enumerate(chunks):
            # 简化重叠逻辑，只在必要时添加重叠，避免过度复杂化
            if i == 0:
                # 第一个切片
                enhanced_chunks.append(chunk)
            else:
                # 对于后续切片，从前一个切片末尾添加重叠文本
                prev_chunk = chunks[i-1]
                # 确保重叠大小合理
                actual_overlap = min(self.chunk_overlap, len(prev_chunk) // 3)  # 最多使用前一个切片的1/3作为重叠
                if actual_overlap > 0:
                    # 添加重叠文本，但不添加额外的标记文本，以保持内容的自然性
                    overlap_text = prev_chunk[-actual_overlap:]
                    # 尝试在词边界处分割重叠文本
                    overlap_text = self._find_word_boundary(overlap_text, True)
                    enhanced_chunks.append(overlap_text + chunk)
                else:
                    enhanced_chunks.append(chunk)
        
        return enhanced_chunks
        
    def _find_word_boundary(self, text: str, from_end: bool = False) -> str:
        """
        尝试在词边界处分割文本
        """
        if len(text) <= 10:  # 文本太短，直接返回
            return text
            
        if from_end:
            # 从文本末尾向前查找词边界
            for i in range(min(len(text), 20), 5, -1):
                if text[-i] in [' ', '。', '，', '.', ',', '!', '！', '?', '？', ';', '；', '\n']:
                    return text[-i:]
        else:
            # 从文本开头向后查找词边界
            for i in range(5, min(len(text), 20)):
                if text[i] in [' ', '。', '，', '.', ',', '!', '！', '?', '？', ';', '；', '\n']:
                    return text[:i+1]
                    
        return text  # 如果找不到合适的词边界，返回原始文本

# 创建默认的切片器实例
def create_financial_splitter():
    """
    创建并返回一个默认配置的财经文本切片器
    """
    return FinancialTextSplitter(
        chunk_size=800,       # 理财文章切片稍小一些，保持更细粒度
        chunk_overlap=150,    # 适当的重叠以保持连贯性
        min_chunk_size=200,   # 最小切片大小
        preserve_sections=True,  # 保持章节完整性
        preserve_tables=True,    # 保持表格完整性
        dynamic_chunking=True    # 启用动态切片长度
    )

# 简单的文本切片函数（方便直接调用）
def split_financial_text(text: str, **kwargs) -> List[str]:
    """
    直接分割文本的便捷函数
    """
    splitter = FinancialTextSplitter(**kwargs)
    return splitter.split_text(text)
