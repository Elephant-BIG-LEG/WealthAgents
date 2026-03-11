# 文本切片器 - 专为理财文章设计
# 采用 Recursive Chunking + Overlap + Metadata 模式
import re
from typing import List, Dict, Tuple, Any, Optional
from dataclasses import dataclass, field
import logging

logger = logging.getLogger(__name__)


@dataclass
class TextChunk:
    """
    文本块数据类
    包含文本内容、元数据和位置信息
    """
    text: str                          # 文本内容
    chunk_id: str                      # 唯一标识
    start_pos: int                     # 在原文中的起始位置
    end_pos: int                       # 在原文中的结束位置
    metadata: Dict[str, Any] = field(default_factory=dict)  # 元数据
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            'text': self.text,
            'chunk_id': self.chunk_id,
            'start_pos': self.start_pos,
            'end_pos': self.end_pos,
            'metadata': self.metadata
        }
    
    @classmethod
    def from_text(cls, text: str, start_pos: int, end_pos: int, 
                  chunk_id: str = None, metadata: Dict = None):
        """从文本创建实例"""
        return cls(
            text=text,
            chunk_id=chunk_id or f"chunk_{start_pos}_{end_pos}",
            start_pos=start_pos,
            end_pos=end_pos,
            metadata=metadata or {}
        )

"""
TODO
不能很好地切分，采用什么切分逻辑待确定
"""
class FinancialTextSplitter:
    """
    专为理财文章设计的递归文本切片器
    
    核心特性：
    1. Recursive Chunking - 多层级递归分割（文档→章节→段落→句子）
    2. Overlap - 智能上下文重叠（保持语义连贯）
    3. Metadata - 丰富的元数据追踪（来源、位置、类型等）
    
    分割策略（优先级从高到低）：
    Level 1: 按章节分割（保持主题完整性）
    Level 2: 按段落分割（保持论述完整性）
    Level 3: 按句子分割（保持语义完整性）
    Level 4: 按字符分割（保底方案）
    """
    
    def __init__(self, 
                 chunk_size: int = 600,      # 目标块大小（字符）
                 chunk_overlap: int = 90,    # 重叠大小（约 15%）
                 min_chunk_size: int = 150,  # 最小块大小
                 separators: List[str] = None,  # 分层分隔符列表
                 preserve_structure: bool = True,  # 保持结构完整性
                 add_metadata: bool = True,      # 添加详细元数据
                ):
        """
        初始化递归切片器
        
        Args:
            chunk_size: 目标块大小（字符数）
            chunk_overlap: 重叠部分大小（用于保持上下文连贯）
            min_chunk_size: 最小块大小（小于此值的块会合并）
            separators: 分层分隔符列表（按优先级排序）
            preserve_structure: 是否保持文档结构（章节、表格等）
            add_metadata: 是否为每个块添加详细元数据
        """
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.min_chunk_size = min_chunk_size
        self.preserve_structure = preserve_structure
        self.add_metadata = add_metadata
        
        # 分层分隔符（按优先级降序排列）
        # 先尝试用高优先级分隔符，不行再用低优先级的
        self.separators = separators or [
            # Level 1: 章节级别分隔符
            r'\n\n(?=#{1,6}\s)',           # Markdown 标题前
            r'\n\n(?=\*{2}[^\n]+\*{2})',   # 粗体标题
            r'\n\n(?=\d+[\.、]\s)',       # 数字序号
            r'\n\n(?=\[[^\]]+\])',        # 方括号标题
            
            # Level 2: 段落级别分隔符
            r'\n\n+',                      # 多个换行（段落间隔）
            r'\r\n\r\n+',                  # Windows 风格段落间隔
            
            # Level 3: 句子级别分隔符
            r'(?<=[。！？.!?])\s*',       # 句末标点
            r'(?<=[；;])\s*',             # 分号
            r'(?<=[，,])\s*',             # 逗号
            
            # Level 4: 其他分隔符
            r'\s+',                        # 空格
            r'',                           # 无分隔符（强制字符级分割）
        ]
        
        # 统计信息
        self.stats = {
            'total_chunks': 0,
            'by_level': {1: 0, 2: 0, 3: 0, 4: 0},
            'avg_chunk_size': 0,
            'total_characters': 0
        }
    
    def split_text(self, text: str, metadata: Dict[str, Any] = None) -> List[TextChunk]:
        """
        递归分割文本（主入口）
        
        Args:
            text: 待分割的文本
            metadata: 基础元数据（如 source, file_name 等）
        
        Returns:
            TextChunk 对象列表
        """
        if not text or len(text.strip()) == 0:
            return []
        
        # 重置统计
        self.stats = {'total_chunks': 0, 'by_level': {1: 0, 2: 0, 3: 0, 4: 0}, 
                      'avg_chunk_size': 0, 'total_characters': 0}
        
        logger.info(f"开始递归分割文本，总长度：{len(text)} 字符")
        
        # Step 1: 文本预处理
        text = self._preprocess_text(text)
        
        # Step 2: 递归分割
        chunks = self._recursive_split(text, level=0)
        
        # Step 3: 添加元数据和重叠
        final_chunks = self._finalize_chunks(chunks, metadata or {})
        
        # Step 4: 更新统计
        self._update_stats(final_chunks)
        
        logger.info(f"分割完成，共生成 {len(final_chunks)} 个文本块")
        logger.debug(f"统计信息：{self.stats}")
        
        return final_chunks
    
    def _preprocess_text(self, text: str) -> str:
        """
        文本预处理
        - 规范化空白字符
        - 统一换行符
        - 移除不可见字符
        """
        # 移除不可见字符
        text = re.sub(r'[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]', '', text)
            
        # 统一换行符
        text = re.sub(r'\r\n', '\n', text)
        text = re.sub(r'\r', '\n', text)
            
        # 规范化连续空白
        text = re.sub(r'[ \t]+', ' ', text)
        text = re.sub(r'\n\s*\n', '\n\n', text)  # 保留段落间隔标记
            
        # 去除首尾空白
        text = text.strip()
            
        return text
        
    def _recursive_split(self, text: str, level: int = 0) -> List[Tuple[str, int, int]]:
        """
        递归分割文本（核心逻辑）
            
        Args:
            text: 待分割文本
            level: 当前递归层级（0 表示从头开始）
            
        Returns:
            [(文本片段，起始位置，结束位置), ...]
            
        递归策略：
        1. 如果文本长度 <= chunk_size，直接返回（无需分割）
        2. 使用当前层级的分隔符尝试分割
        3. 如果分割成功（产生多个片段），对每个片段递归处理
        4. 如果分割失败（还是太长），进入下一层级尝试更细粒度的分隔符
        5. 如果所有层级都失败，强制按字符分割
        """
        # 基本情况：文本已经足够短
        if len(text) <= self.chunk_size:
            return [(text, 0, len(text))]
            
        # 获取当前层级的分隔符
        if level < len(self.separators):
            separator = self.separators[level]
        else:
            # 所有分隔符都失败了，强制按字符分割
            return self._force_split_by_chars(text)
            
        # 尝试用当前分隔符分割
        if separator:
            # 使用正则表达式分割
            parts = re.split(f'({separator})', text)
                
            # 重新组合（保留分隔符）
            segments = []
            current_segment = ""
                
            for i, part in enumerate(parts):
                # 跳过空的分隔符
                if re.fullmatch(separator, part) or not part.strip():
                    if current_segment.strip():
                        segments.append(current_segment.strip())
                        current_segment = ""
                else:
                    current_segment += part
                
            if current_segment.strip():
                segments.append(current_segment.strip())
        else:
            # 空分隔符意味着按字符硬切
            return self._force_split_by_chars(text)
            
        # 如果只产生了一个 segment（分割失败），进入下一层级
        if len(segments) <= 1:
            return self._recursive_split(text, level + 1)
            
        # 对每个 segment 递归处理
        result = []
        current_pos = 0
            
        for segment in segments:
            segment = segment.strip()
            if not segment:
                continue
                
            segment_len = len(segment)
                
            # 如果 segment 仍然太长，递归分割
            if segment_len > self.chunk_size:
                sub_segments = self._recursive_split(segment, level + 1)
                    
                # 调整位置信息
                for sub_text, sub_start, sub_end in sub_segments:
                    global_start = current_pos + sub_start
                    global_end = current_pos + sub_end
                    result.append((sub_text, global_start, global_end))
            else:
                # segment 长度合适，直接添加
                result.append((segment, current_pos, current_pos + segment_len))
                
            current_pos += segment_len
            
        return result
    
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
    
    def _force_split_by_chars(self, text: str) -> List[Tuple[str, int, int]]:
        """
        强制按字符分割（保底方案）
        在句子边界处智能切断，而非简单按固定长度
        """
        result = []
        start = 0
        
        while start < len(text):
            end = min(start + self.chunk_size, len(text))
            
            # 如果不是最后一段，尝试在句子边界处切断
            if end < len(text):
                # 向前查找最近的句子边界（最多回退 chunk_size 的 30%）
                search_back = int(self.chunk_size * 0.3)
                cut_point = self._find_best_cut_point(text[start:end], search_back)
                
                if cut_point > 0:
                    end = start + cut_point
            
            # 提取文本段
            segment = text[start:end].strip()
            if segment:
                result.append((segment, start, end))
            
            # 移动到下一段（考虑 overlap）
            if end < len(text):
                start = end - self.chunk_overlap
            else:
                start = end
        
        return result
    
    def _find_best_cut_point(self, text: str, search_range: int) -> int:
        """
        在文本中查找最佳切断点
        优先级：句号 > 分号 > 逗号 > 空格
        """
        end_pos = len(text)
        start_search = max(0, end_pos - search_range)
        
        # 优先级 1: 句末标点
        for i in range(end_pos - 1, start_search - 1, -1):
            if text[i] in ['。', '！', '？', '.', '!', '?']:
                return i + 1
        
        # 优先级 2: 分号
        for i in range(end_pos - 1, start_search - 1, -1):
            if text[i] in ['；', ';']:
                return i + 1
        
        # 优先级 3: 逗号
        for i in range(end_pos - 1, start_search - 1, -1):
            if text[i] in ['，', ',', '\n']:
                return i + 1
        
        # 没找到合适的切断点，返回末尾
        return end_pos
    
    def _finalize_chunks(self, raw_chunks: List[Tuple[str, int, int]], 
                         base_metadata: Dict[str, Any]) -> List[TextChunk]:
        """
        最终处理：添加元数据和上下文重叠
        
        Args:
            raw_chunks: 原始分割结果 [(text, start, end), ...]
            base_metadata: 基础元数据
        
        Returns:
            TextChunk 对象列表（带完整元数据和重叠）
        """
        if not raw_chunks:
            return []
        
        # Step 1: 转换为 TextChunk 对象并添加基础元数据
        chunks = []
        for i, (text, start, end) in enumerate(raw_chunks):
            chunk_metadata = base_metadata.copy()
            
            # 添加自动生成的元数据
            if self.add_metadata:
                chunk_metadata.update({
                    'chunk_index': i,
                    'total_chunks': len(raw_chunks),
                    'chunk_size': len(text),
                    'start_position': start,
                    'end_position': end,
                    'has_overlap': False,
                    'created_at': __import__('datetime').datetime.now().isoformat()
                })
            
            chunk = TextChunk.from_text(
                text=text,
                start_pos=start,
                end_pos=end,
                chunk_id=f"chunk_{i:04d}_{start}_{end}",
                metadata=chunk_metadata
            )
            chunks.append(chunk)
        
        # Step 2: 添加上下文重叠
        chunks_with_overlap = self._add_smart_overlap(chunks)
        
        # Step 3: 合并过小的 chunk（避免碎片化）
        final_chunks = self._merge_small_chunks(chunks_with_overlap)
        
        return final_chunks
    
    def _add_smart_overlap(self, chunks: List[TextChunk]) -> List[TextChunk]:
        """
        智能添加上下文重叠
        
        策略：
        1. 从前一个 chunk 的末尾取 overlap_size 个字符
        2. 在词边界处切断（避免切断词语）
        3. 添加到当前 chunk 的开头
        """
        if len(chunks) <= 1:
            return chunks
        
        enhanced_chunks = []
        
        for i, chunk in enumerate(chunks):
            if i == 0:
                # 第一个 chunk 不需要添加前面的重叠
                enhanced_chunks.append(chunk)
            else:
                prev_chunk = chunks[i - 1]
                
                # 计算实际重叠大小（固定为 chunk_overlap，但不超过前一个 chunk 的 1/3）
                actual_overlap = min(self.chunk_overlap, len(prev_chunk.text) // 3)
                
                if actual_overlap > 0 and len(prev_chunk.text) > actual_overlap:
                    # 提取重叠文本
                    overlap_text = prev_chunk.text[-actual_overlap:]
                    
                    # 在词边界处切断（避免切断完整词语）
                    overlap_text = self._trim_to_word_boundary(overlap_text, from_start=True)
                    
                    # 添加到当前 chunk 开头
                    new_text = overlap_text + chunk.text
                    
                    # 创建新的 chunk（保留原有元数据）
                    new_chunk = TextChunk(
                        text=new_text,
                        chunk_id=chunk.chunk_id,
                        start_pos=chunk.start_pos,
                        end_pos=chunk.end_pos,
                        metadata=chunk.metadata.copy()
                    )
                    new_chunk.metadata['has_overlap'] = True
                    new_chunk.metadata['overlap_size'] = len(overlap_text)
                    
                    enhanced_chunks.append(new_chunk)
                else:
                    # 不需要添加重叠
                    enhanced_chunks.append(chunk)
        
        return enhanced_chunks
    
    def _trim_to_word_boundary(self, text: str, from_start: bool = False) -> str:
        """
        在词边界处修剪文本
        避免切断完整的词语（特别是中文词汇）
        
        Args:
            text: 待修剪的文本
            from_start: 是否从开头修剪（否则从末尾修剪）
        """
        if len(text) <= 10:
            return text  # 文本太短，直接返回
        
        # 查找边界字符
        boundary_chars = [' ', '。', '，', '.', ',', '!', '!', '?', '？', ';', '；', '\n']
        
        if from_start:
            # 从开头向后找第一个边界
            for i in range(min(len(text), 20)):
                if text[i] in boundary_chars:
                    return text[i+1:] if i < len(text) - 1 else text
        else:
            # 从末尾向前找第一个边界
            for i in range(min(len(text), 20), 5, -1):
                if text[-i] in boundary_chars:
                    return text[-i:]
        
        # 没找到边界，直接返回原文本
        return text
    
    def _merge_small_chunks(self, chunks: List[TextChunk]) -> List[TextChunk]:
        """
        合并过小的 chunk（避免碎片化）
        
        合并策略：
        - 如果连续几个 chunk 都很小且总和不超过 chunk_size，合并它们
        """
        if len(chunks) <= 1:
            return chunks
        
        merged = []
        current_group = [chunks[0]]
        current_size = len(chunks[0].text)
        
        for i in range(1, len(chunks)):
            chunk = chunks[i]
            chunk_size = len(chunk.text)
            
            # 如果当前组太小且加上新 chunk 也不超过限制，合并
            if current_size < self.min_chunk_size and current_size + chunk_size <= self.chunk_size:
                current_group.append(chunk)
                current_size += chunk_size
            else:
                # 保存当前组并开始新的一组
                if len(current_group) == 1:
                    merged.append(current_group[0])
                else:
                    # 合并多个 chunk
                    merged_chunk = self._merge_chunk_group(current_group)
                    merged.append(merged_chunk)
                
                current_group = [chunk]
                current_size = chunk_size
        
        # 处理最后一组
        if len(current_group) == 1:
            merged.append(current_group[0])
        else:
            merged.append(self._merge_chunk_group(current_group))
        
        return merged
    
    def _merge_chunk_group(self, group: List[TextChunk]) -> TextChunk:
        """
        合并一组 chunk
        """
        if not group:
            raise ValueError("Chunk group cannot be empty")
        
        # 合并文本（用换行符连接）
        merged_text = '\n\n'.join(chunk.text for chunk in group)
        
        # 合并元数据
        merged_metadata = group[0].metadata.copy()
        merged_metadata.update({
            'merged_from': [chunk.chunk_id for chunk in group],
            'merge_count': len(group),
            'original_sizes': [len(chunk.text) for chunk in group]
        })
        
        return TextChunk(
            text=merged_text,
            chunk_id=f"merged_{group[0].chunk_id}_to_{group[-1].chunk_id}",
            start_pos=group[0].start_pos,
            end_pos=group[-1].end_pos,
            metadata=merged_metadata
        )
    
    def _update_stats(self, chunks: List[TextChunk]):
        """更新统计信息"""
        if not chunks:
            return
        
        self.stats['total_chunks'] = len(chunks)
        self.stats['total_characters'] = sum(len(c.text) for c in chunks)
        self.stats['avg_chunk_size'] = self.stats['total_characters'] / len(chunks)
    
    def get_stats(self) -> Dict[str, Any]:
        """获取分割统计信息"""
        return self.stats.copy()


# 创建全局切片器实例（使用优化后的递归分割配置）
global_splitter = FinancialTextSplitter(
    chunk_size=600,           # 目标块大小
    chunk_overlap=90,         # 重叠大小（15%）
    min_chunk_size=150,       # 最小块大小
    preserve_structure=True,  # 保持结构
    add_metadata=True         # 添加详细元数据
)

# 创建默认的切片器实例
def create_financial_splitter(**kwargs) -> FinancialTextSplitter:
    """
    创建并返回一个默认配置的财经文本切片器
    
    推荐配置：
    - chunk_size=600: 适合财务报告的中等长度
    - chunk_overlap=90: 15% 的重叠率，平衡连贯性和冗余度
    - min_chunk_size=150: 允许短小精悍的完整表述
    """
    if kwargs:
        return FinancialTextSplitter(**kwargs)
    else:
        return FinancialTextSplitter(
            chunk_size=600,           # 理财文章标准大小
            chunk_overlap=90,         # 15% 重叠率
            min_chunk_size=150,       # 最小切片大小
            preserve_structure=True,  # 保持章节完整性
            add_metadata=True         # 添加详细元数据
        )

# 简单的文本切片函数（方便直接调用）
def split_financial_text(text: str, metadata: Dict[str, Any] = None, **kwargs) -> List[TextChunk]:
    """
    直接分割文本的便捷函数
    
    Args:
        text: 待分割的文本
        metadata: 基础元数据（如 source, file_name 等）
        **kwargs: 自定义配置参数
    
    Returns:
        TextChunk 对象列表
    """
    if kwargs:
        # 如果提供了自定义参数，创建新实例
        splitter = FinancialTextSplitter(**kwargs)
        return splitter.split_text(text, metadata=metadata)
    else:
        # 使用全局实例
        try:
            return global_splitter.split_text(text, metadata=metadata)
        except Exception as e:
            logger.error(f"文本切片过程中出错：{e}")
            # 出错时返回空列表
            return []