from typing import List, Dict, Any, Optional, Tuple
import re
from datetime import datetime
import os
import nltk
from nltk.tokenize import sent_tokenize
import logging
from app.chunk.splitter import FinancialTextSplitter

logger = logging.getLogger(__name__)

# 尝试下载NLTK资源
try:
    nltk.download('punkt', quiet=True)
except:
    logger.warning("无法下载NLTK资源punkt")


class EnhancedFinancialTextSplitter(FinancialTextSplitter):
    """
    增强的财务文本分块器
    扩展了基础的FinancialTextSplitter，添加了专为财务文档设计的分块逻辑
    """
    
    def __init__(self, chunk_size: int = 600, chunk_overlap: int = 120, 
                 preserve_financial_sections: bool = True, 
                 smart_sentence_ending: bool = True):
        """
        初始化增强的财务文本分块器
        
        参数：
        - chunk_size: 文本块大小
        - chunk_overlap: 文本块重叠大小
        - preserve_financial_sections: 是否保留财务章节结构
        - smart_sentence_ending: 是否智能处理句子结尾
        """
        super().__init__(chunk_size=chunk_size, chunk_overlap=chunk_overlap, 
                        preserve_sections=preserve_financial_sections)
        self.smart_sentence_ending = smart_sentence_ending
        
        # 财务文档特有的章节标题模式
        self.financial_section_patterns = [
            # 财务报表部分
            r'^\s*(?:资产负债表|利润表|现金流量表|所有者权益变动表)',
            r'^\s*(?:Balance\s+Sheet|Income\s+Statement|Cash\s+Flow\s+Statement|Statement\s+of\s+Changes\s+in\s+Equity)',
            
            # 财务分析部分
            r'^\s*(?:财务分析|财务状况|经营成果|业绩分析|盈利能力|偿债能力|运营能力|发展能力)',
            r'^\s*(?:Financial\s+Analysis|Financial\s+Position|Operating\s+Results|Profitability|Solvency|Operating\s+Capacity|Development\s+Capacity)',
            
            # 管理层讨论与分析
            r'^\s*(?:管理层讨论与分析|MD\u0026A|Management\s+Discussion\s+and\s+Analysis)',
            
            # 风险部分
            r'^\s*(?:风险因素|风险分析|风险管理)',
            r'^\s*(?:Risk\s+Factors|Risk\s+Analysis|Risk\s+Management)',
            
            # 附注部分
            r'^\s*(?:附注|会计报表附注|Notes\s+to\s+Financial\s+Statements)',
            
            # 审计报告
            r'^\s*(?:审计报告|Auditor\s+Report|Independent\s+Auditor\s+Report)',
            
            # 董事会报告
            r'^\s*(?:董事会报告|Board\s+Report)',
            
            # 财务指标部分
            r'^\s*(?:主要财务指标|核心财务数据|Key\s+Financial\s+Indicators|Core\s+Financial\s+Data)'
        ]
        
        # 财务数字模式，用于避免在财务数据中间分割
        self.financial_number_pattern = r'\d+(?:,\d{3})*(?:\.\d+)?\s*[%$￥]?'
    
    def _identify_financial_sections(self, text: str) -> List[Tuple[int, int, str]]:
        """
        识别财务文档中的关键章节
        
        参数：
        - text: 完整文本
        
        返回：
        - 章节列表，每个元素包含(开始位置, 结束位置, 章节标题)
        """
        sections = []
        lines = text.split('\n')
        section_start = 0
        current_title = ""
        text_pos = 0
        
        for i, line in enumerate(lines):
            line_len = len(line) + 1  # +1 for the newline character
            
            # 检查是否匹配财务章节标题模式
            matched = False
            for pattern in self.financial_section_patterns:
                if re.match(pattern, line.strip()):
                    # 保存前一个章节(如果有的话)
                    if current_title:
                        sections.append((section_start, text_pos, current_title))
                    
                    # 开始新章节
                    current_title = line.strip()
                    section_start = text_pos
                    matched = True
                    break
            
            if matched:
                logger.debug(f"识别到财务章节: {current_title}")
            
            text_pos += line_len
        
        # 添加最后一个章节
        if current_title:
            sections.append((section_start, text_pos, current_title))
        
        return sections
    
    def _smart_split_at_sentence(self, text: str, target_length: int) -> Tuple[str, str]:
        """
        智能地在句子结尾处分割文本，避免在财务数据中间分割
        
        参数：
        - text: 要分割的文本
        - target_length: 目标分割长度
        
        返回：
        - (前半部分, 后半部分) 元组
        """
        # 如果文本长度小于目标长度，直接返回
        if len(text) <= target_length:
            return text, ""
        
        # 查找合适的分割位置
        # 优先考虑句号、问号、感叹号等句子结束符
        end_markers = ['.', '。', '!', '！', '?', '？']
        split_pos = target_length
        
        # 在目标长度附近寻找句子结束符
        lookahead_window = min(100, len(text) - target_length)
        for i in range(target_length, target_length + lookahead_window):
            if i < len(text) and text[i] in end_markers:
                # 确保不是在财务数字中间，例如："10.5%的增长率"
                if not (text[i] == '.' and i > 0 and i < len(text) - 1 and 
                        text[i-1].isdigit() and text[i+1].isdigit()):
                    split_pos = i + 1  # 包含结束符
                    break
        
        # 如果没找到合适的句子结束符，退回到普通分割
        return text[:split_pos], text[split_pos:]
    
    def _preserve_financial_tables(self, chunks: List[str]) -> List[str]:
        """
        尝试保留财务表格的完整性，合并被错误分割的表格
        
        参数：
        - chunks: 初步分割的文本块列表
        
        返回：
        - 处理后的文本块列表
        """
        if not chunks or len(chunks) < 2:
            return chunks
        
        processed_chunks = [chunks[0]]
        i = 1
        
        while i < len(chunks):
            current_chunk = chunks[i]
            prev_chunk = processed_chunks[-1]
            
            # 简单检测表格：检查是否包含多个连续数字和特定的表格分隔符
            prev_has_numerical_data = bool(re.search(r'\d+\s+\d+', prev_chunk))
            current_has_numerical_data = bool(re.search(r'\d+\s+\d+', current_chunk))
            
            # 检查是否包含典型的表格标记
            prev_has_table_markers = bool(re.search(r'[-\+\|\s]{20,}', prev_chunk))
            current_has_table_markers = bool(re.search(r'[-\+\|\s]{20,}', current_chunk))
            
            # 如果相邻块都包含表格特征，尝试合并它们
            if (prev_has_numerical_data and current_has_numerical_data) or \
               (prev_has_table_markers and current_has_table_markers):
                # 合并前检查合并后的长度是否超过阈值
                if len(prev_chunk) + len(current_chunk) < self.chunk_size * 1.5:
                    processed_chunks[-1] = prev_chunk + " " + current_chunk
                    logger.debug("检测到并合并了表格数据块")
                else:
                    processed_chunks.append(current_chunk)
            else:
                processed_chunks.append(current_chunk)
            
            i += 1
        
        return processed_chunks
    
    def split_text(self, text: str) -> List[str]:
        """
        分割文本为适合财务文档的文本块
        
        参数：
        - text: 要分割的文本
        
        返回：
        - 分割后的文本块列表
        """
        # 1. 首先使用基础类的方法进行初步分割
        chunks = super().split_text(text)
        
        # 2. 应用智能句子结尾处理
        if self.smart_sentence_ending and chunks:
            processed_chunks = []
            for chunk in chunks:
                # 如果文本块以不完整的句子结尾，尝试调整
                if not chunk.strip().endswith(('.', '。', '!', '！', '?', '？')) and len(chunk) > self.chunk_size * 0.8:
                    # 在保持块大小不变的情况下，尝试在句子结尾分割
                    smart_chunk, _ = self._smart_split_at_sentence(chunk, len(chunk))
                    processed_chunks.append(smart_chunk)
                else:
                    processed_chunks.append(chunk)
            chunks = processed_chunks
        
        # 3. 尝试保留财务表格完整性
        chunks = self._preserve_financial_tables(chunks)
        
        # 4. 过滤空块和过短的块
        chunks = [chunk.strip() for chunk in chunks if chunk.strip() and len(chunk.strip()) > 20]
        
        return chunks


class FinancialTagGenerator:
    """
    财务标签生成器，为财务文本生成相关标签
    """
    
    def __init__(self):
        """初始化财务标签生成器"""
        # 定义财务领域的标签分类
        self.financial_categories = {
            'financial_metrics': [
                'revenue', 'income', 'profit', 'loss', 'earnings', 'margin', 
                'growth', 'EPS', 'EBITDA', 'cash_flow', 'debt', 'assets', 
                'liabilities', 'equity', 'ROE', 'ROA', 'operating_income',
                'revenue', '收入', '利润', '亏损', '收益', '利润率', 
                '增长', '每股收益', '现金流', '债务', '资产', '负债',
                '股东权益', '净资产收益率', '总资产收益率', '营业收入'
            ],
            'financial_analysis': [
                'forecast', 'projection', 'trend', 'comparison', 'analysis',
                'outlook', 'performance', 'benchmark', 'ratio', 'indicator',
                '预测', '趋势', '比较', '分析', '展望', '表现', '基准',
                '比率', '指标'
            ],
            'financial_statements': [
                'balance_sheet', 'income_statement', 'cash_flow_statement',
                'financial_report', 'annual_report', 'quarterly_report',
                '审计', '财务报表', '资产负债表', '利润表', '现金流量表',
                '财务报告', '年报', '季报'
            ],
            'special_financial_items': [
                'acquisition', 'merger', 'dividend', 'stock_split',
                'IPO', 'bankruptcy', 'restructuring', 'regulatory',
                'compliance', 'tax', 'acquisition', 'merger', 'dividend',
                '收购', '合并', '分红', '股票分割', '首次公开募股',
                '破产', '重组', '监管', '合规', '税收'
            ]
        }
        
        # 文档类型标签模式
        self.document_type_patterns = {
            'annual_report': [r'annual\s+report', r'年报', r'年度报告'],
            'quarterly_report': [r'quarterly\s+report', r'季报', r'季度报告'],
            'financial_statement': [r'financial\s+statement', r'财务报表'],
            'balance_sheet': [r'balance\s+sheet', r'资产负债表'],
            'income_statement': [r'income\s+statement', r'利润表', r'损益表'],
            'cash_flow': [r'cash\s+flow', r'现金流量表'],
            'earnings_call': [r'earnings\s+call', r'财报电话会议'],
            'analyst_report': [r'analyst\s+report', r'分析师报告']
        }
    
    def generate_content_tags(self, text: str) -> List[str]:
        """
        基于文本内容生成财务标签
        
        Args:
            text: 财务文本内容
            
        Returns:
            生成的标签列表
        """
        if not text or not isinstance(text, str):
            return []
        
        tags = []
        text_lower = text.lower()
        
        # 检查每个财务类别
        for category, keywords in self.financial_categories.items():
            for keyword in keywords:
                if keyword.lower() in text_lower:
                    tags.append(category)
                    break  # 每个类别只添加一次
        
        # 添加金额标签
        if self._contains_financial_amounts(text):
            tags.append('financial_amounts')
        
        # 添加百分比标签
        if self._contains_percentages(text):
            tags.append('percentages')
        
        # 添加时间相关标签
        if self._contains_time_references(text):
            tags.append('time_references')
        
        return list(set(tags))  # 去重
    
    def identify_document_type(self, text: str, filename: str = "") -> str:
        """
        识别文档类型
        
        Args:
            text: 文档文本内容
            filename: 文件名（可选，用于辅助识别）
            
        Returns:
            识别出的文档类型
        """
        combined_text = (text + " " + filename).lower()
        
        # 检查每个文档类型的模式
        for doc_type, patterns in self.document_type_patterns.items():
            for pattern in patterns:
                if re.search(pattern, combined_text, re.IGNORECASE):
                    return doc_type
        
        return 'financial_report'  # 默认类型
    
    def extract_year_from_content(self, text: str, filename: str = "") -> Optional[int]:
        """
        从文本或文件名中提取年份
        
        Args:
            text: 文档文本内容
            filename: 文件名（可选）
            
        Returns:
            提取的年份，如果没有找到则返回None
        """
        combined_text = text + " " + filename
        
        # 搜索2000-2099年间的年份模式
        year_pattern = r'\b(20[0-9]{2})\b'
        matches = re.findall(year_pattern, combined_text)
        
        if matches:
            # 尝试找到最近的年份或在特定上下文中提到的年份
            current_year = datetime.now().year
            valid_years = [int(y) for y in matches if 2000 <= int(y) <= current_year + 1]
            
            if valid_years:
                # 优先选择接近当前年份的
                return min(valid_years, key=lambda y: abs(y - current_year))
        
        return None
    
    def extract_quarter_from_content(self, text: str, filename: str = "") -> Optional[str]:
        """
        从文本或文件名中提取季度
        
        Args:
            text: 文档文本内容
            filename: 文件名（可选）
            
        Returns:
            提取的季度，如果没有找到则返回None
        """
        combined_text = text + " " + filename
        
        # 定义季度的正则表达式模式
        quarter_patterns = [
            (r'\bQ([1-4])\b', r'Q\1'),  # Q1, Q2, Q3, Q4
            (r'\b第([一二三四])季度\b', lambda m: f"Q{m.group(1).translate(str.maketrans('一二三四', '1234'))}"),
            (r'\b第一季度\b', r'Q1'),
            (r'\b第二季度\b', r'Q2'),
            (r'\b第三季度\b', r'Q3'),
            (r'\b第四季度\b', r'Q4'),
            (r'\b一季度\b', r'Q1'),
            (r'\b二季度\b', r'Q2'),
            (r'\b三季度\b', r'Q3'),
            (r'\b四季度\b', r'Q4')
        ]
        
        for pattern, replacement in quarter_patterns:
            match = re.search(pattern, combined_text, re.IGNORECASE)
            if match:
                if callable(replacement):
                    return replacement(match)
                return replacement
        
        return None
    
    def generate_enhanced_metadata(self, filename: str, text: str, base_metadata: Dict[str, Any]) -> Dict[str, Any]:
        """
        生成增强的元数据
        
        Args:
            filename: 文件名
            text: 文档文本内容
            base_metadata: 基础元数据字典
            
        Returns:
            增强后的元数据字典
        """
        # 创建元数据副本
        enhanced_metadata = base_metadata.copy() if base_metadata else {}
        
        # 添加文件名和文本长度信息
        enhanced_metadata['filename'] = filename
        enhanced_metadata['text_length'] = len(text)
        
        # 如果没有文档类型，尝试自动识别
        if 'document_type' not in enhanced_metadata or not enhanced_metadata['document_type']:
            enhanced_metadata['document_type'] = self.identify_document_type(text, filename)
        
        # 如果没有年份信息，尝试提取
        if 'year' not in enhanced_metadata or enhanced_metadata['year'] is None:
            extracted_year = self.extract_year_from_content(text, filename)
            if extracted_year:
                enhanced_metadata['year'] = extracted_year
        
        # 如果没有季度信息，尝试提取
        if 'quarter' not in enhanced_metadata or enhanced_metadata['quarter'] is None:
            extracted_quarter = self.extract_quarter_from_content(text, filename)
            if extracted_quarter:
                enhanced_metadata['quarter'] = extracted_quarter
        
        # 生成文档别名
        enhanced_metadata['document_alias'] = self._generate_document_alias(filename, enhanced_metadata)
        
        # 添加处理时间
        enhanced_metadata['processing_time'] = datetime.now().isoformat()
        
        return enhanced_metadata
    
    def _contains_financial_amounts(self, text: str) -> bool:
        """
        检查文本是否包含财务金额
        
        Args:
            text: 待检查的文本
            
        Returns:
            是否包含财务金额
        """
        # 匹配数字模式，例如 $100,000, 100万元, 1,000.00
        amount_patterns = [
            r'\$?\d{1,3}(,\d{3})*(\.\d{1,2})?\s*(million|billion|trillion|万|亿)?',
            r'\d+(\.\d+)?\s*(元|美元|欧元|英镑)'
        ]
        
        for pattern in amount_patterns:
            if re.search(pattern, text, re.IGNORECASE):
                return True
        
        return False
    
    def _contains_percentages(self, text: str) -> bool:
        """
        检查文本是否包含百分比
        
        Args:
            text: 待检查的文本
            
        Returns:
            是否包含百分比
        """
        percentage_pattern = r'\d+(\.\d+)?\s*%'
        return bool(re.search(percentage_pattern, text))
    
    def _contains_time_references(self, text: str) -> bool:
        """
        检查文本是否包含时间参考
        
        Args:
            text: 待检查的文本
            
        Returns:
            是否包含时间参考
        """
        time_patterns = [
            r'\b(\d{1,2})[-/](\d{1,2})[-/](\d{2,4})\b',  # 日期格式
            r'\b(\d{4})[-/](\d{1,2})[-/](\d{1,2})\b',
            r'\b(january|february|march|april|may|june|july|august|september|october|november|december)\b',
            r'\b(一月|二月|三月|四月|五月|六月|七月|八月|九月|十月|十一月|十二月)\b',
            r'\bQ[1-4]\b',  # 季度
            r'\b(第一|第二|第三|第四)季度\b'
        ]
        
        text_lower = text.lower()
        for pattern in time_patterns:
            if re.search(pattern, text_lower):
                return True
        
        return False
    
    def _generate_document_alias(self, filename: str, metadata: Dict[str, Any]) -> str:
        """
        生成文档别名
        
        Args:
            filename: 文件名
            metadata: 文档元数据
            
        Returns:
            生成的文档别名
        """
        # 从文件名提取基础名称
        base_name = os.path.splitext(filename)[0]
        
        # 如果有年份和季度信息，添加到别名中
        if 'year' in metadata and metadata['year']:
            alias_parts = [str(metadata['year'])]
            
            if 'quarter' in metadata and metadata['quarter']:
                alias_parts.append(metadata['quarter'])
            
            if 'document_type' in metadata and metadata['document_type']:
                # 将文档类型转换为更易读的形式
                doc_type = metadata['document_type'].replace('_', ' ')
                alias_parts.append(doc_type)
            
            return ' '.join(alias_parts)
        
        # 如果无法生成更详细的别名，返回文件名（去除扩展名）
        return base_name