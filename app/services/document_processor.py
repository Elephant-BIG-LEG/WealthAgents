import os
import re
from typing import Dict, List, Any, Tuple, Optional
import logging

logger = logging.getLogger(__name__)

"""
文件处理器
负责从不同类型的文件中提取文本内容
支持常见的文档格式如TXT、PDF、DOCX等
"""

class DocumentProcessor:
    """文档处理器类，支持从多种格式文件中提取文本"""
    
    def __init__(self):
        """初始化文档处理器"""
        # 支持的文件类型及其对应的处理方法
        self.supported_extensions = {
            '.txt': self._process_txt,
            '.pdf': self._process_pdf,
            '.docx': self._process_docx,
            '.json': self._process_json,
            '.csv': self._process_csv,
        }
    
    def process_file(self, file_path: str, file_name: Optional[str] = None) -> Dict[str, Any]:
        """
        处理文件并提取文本内容
        
        参数：
        - file_path: 文件路径
        - file_name: 文件名（可选，默认使用文件路径中的文件名）
        
        返回：
        - 包含文件名和提取的文本内容的字典
        """
        try:
            # 确定文件名
            if not file_name:
                file_name = os.path.basename(file_path)
            
            # 获取文件扩展名
            _, ext = os.path.splitext(file_name.lower())
            
            # 检查是否支持该文件类型
            if ext not in self.supported_extensions:
                logger.warning(f"不支持的文件类型: {ext}")
                return {
                    'file_name': file_name,
                    'content': '',
                    'error': f"不支持的文件类型: {ext}",
                    'status': 'unsupported'
                }
            
            # 调用对应的处理方法
            content = self.supported_extensions[ext](file_path)
            
            return {
                'file_name': file_name,
                'content': content,
                'status': 'success'
            }
        
        except Exception as e:
            logger.error(f"处理文件 {file_path} 时出错: {str(e)}")
            return {
                'file_name': file_name,
                'content': '',
                'error': str(e),
                'status': 'error'
            }
    
    def process_multiple_files(self, file_paths: List[str]) -> List[Dict[str, Any]]:
        """
        批量处理多个文件
        
        参数：
        - file_paths: 文件路径列表
        
        返回：
        - 处理结果列表，每个结果包含文件名和提取的文本内容
        """
        results = []
        for file_path in file_paths:
            results.append(self.process_file(file_path))
        return results
    
    def _process_txt(self, file_path: str) -> str:
        """处理文本文件"""
        try:
            # 尝试不同编码读取文件
            encodings = ['utf-8', 'gbk', 'gb2312', 'latin-1']
            content = ''
            
            for encoding in encodings:
                try:
                    with open(file_path, 'r', encoding=encoding) as f:
                        content = f.read()
                    break
                except UnicodeDecodeError:
                    continue
            
            # 规范化文本（去除多余空白字符等）
            content = self._normalize_text(content)
            return content
        
        except Exception as e:
            logger.error(f"处理文本文件时出错: {str(e)}")
            return ''
    
    def _process_pdf(self, file_path: str) -> str:
        """处理PDF文件"""
        try:
            # 使用PyPDF2或pdfplumber库提取文本（这里提供一个基础实现，实际项目中可能需要安装这些库）
            # 为了避免依赖问题，提供一个简化版实现
            try:
                import PyPDF2
                content = ''
                with open(file_path, 'rb') as file:
                    reader = PyPDF2.PdfReader(file)
                    for page in reader.pages:
                        content += page.extract_text() or ''
                return self._normalize_text(content)
            except ImportError:
                logger.warning("未安装PyPDF2库，无法处理PDF文件")
                # 如果没有相应库，返回一个提示信息而不是空字符串
                return "[PDF文件内容，需要安装PyPDF2库以提取具体文本]"
            except Exception as e:
                logger.error(f"使用PyPDF2处理PDF时出错: {str(e)}")
                return "[PDF文件处理失败]"
        
        except Exception as e:
            logger.error(f"处理PDF文件时出错: {str(e)}")
            return ''
    
    def _process_docx(self, file_path: str) -> str:
        """处理DOCX文件"""
        try:
            # 尝试使用python-docx库提取文本
            try:
                from docx import Document
                doc = Document(file_path)
                content = []
                for para in doc.paragraphs:
                    content.append(para.text)
                full_text = '\n'.join(content)
                return self._normalize_text(full_text)
            except ImportError:
                logger.warning("未安装python-docx库，无法处理DOCX文件")
                return "[DOCX文件内容，需要安装python-docx库以提取具体文本]"
            except Exception as e:
                logger.error(f"使用python-docx处理DOCX时出错: {str(e)}")
                return "[DOCX文件处理失败]"
        
        except Exception as e:
            logger.error(f"处理DOCX文件时出错: {str(e)}")
            return ''
    
    def _process_json(self, file_path: str) -> str:
        """处理JSON文件"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            # 将JSON对象转换为格式化的字符串
            return json.dumps(data, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"处理JSON文件时出错: {str(e)}")
            return ''
    
    def _process_csv(self, file_path: str) -> str:
        """处理CSV文件"""
        try:
            import csv
            content = []
            # 尝试不同编码读取CSV
            encodings = ['utf-8', 'gbk', 'gb2312']
            
            for encoding in encodings:
                try:
                    with open(file_path, 'r', newline='', encoding=encoding) as csvfile:
                        reader = csv.reader(csvfile)
                        for row in reader:
                            content.append(','.join(row))
                    break
                except UnicodeDecodeError:
                    continue
            
            return '\n'.join(content)
        except Exception as e:
            logger.error(f"处理CSV文件时出错: {str(e)}")
            return ''
    
    def _normalize_text(self, text: str) -> str:
        """
        规范化文本内容
        - 去除多余的空白字符
        - 统一换行符
        """
        # 替换连续的空格为单个空格
        text = re.sub(r'\s+', ' ', text)
        # 替换制表符、回车符为空格
        text = text.replace('\t', ' ').replace('\r', ' ')
        # 替换多个换行为单个换行
        text = re.sub(r'\n+', '\n', text)
        # 去除首尾空白
        text = text.strip()
        return text


"""
文件上传工具类
提供文件上传和临时存储功能
"""

class FileUploadHandler:
    """文件上传处理器"""
    
    def __init__(self, upload_dir: str = 'temp_uploads'):
        """
        初始化文件上传处理器
        
        参数：
        - upload_dir: 临时上传目录
        """
        self.upload_dir = upload_dir
        # 确保上传目录存在
        if not os.path.exists(upload_dir):
            os.makedirs(upload_dir)
    
    def save_uploaded_file(self, file_content: bytes, file_name: str) -> str:
        """
        保存上传的文件
        
        参数：
        - file_content: 文件内容（字节形式）
        - file_name: 文件名
        
        返回：
        - 保存的文件路径
        """
        try:
            # 为了安全，清理文件名
            safe_filename = self._sanitize_filename(file_name)
            file_path = os.path.join(self.upload_dir, safe_filename)
            
            # 保存文件
            with open(file_path, 'wb') as f:
                f.write(file_content)
            
            return file_path
        
        except Exception as e:
            logger.error(f"保存上传文件 {file_name} 时出错: {str(e)}")
            raise
    
    def _sanitize_filename(self, filename: str) -> str:
        """
        清理文件名，移除可能的恶意字符
        """
        # 移除或替换不安全的字符
        filename = re.sub(r'[<>:"/\\|?*]', '_', filename)
        # 限制文件名长度
        max_length = 255
        if len(filename) > max_length:
            name, ext = os.path.splitext(filename)
            filename = name[:max_length - len(ext)] + ext
        return filename
    
    def cleanup_uploads(self):
        """
        清理临时上传文件
        """
        try:
            for file_name in os.listdir(self.upload_dir):
                file_path = os.path.join(self.upload_dir, file_name)
                if os.path.isfile(file_path):
                    os.remove(file_path)
            logger.info("临时上传文件已清理")
        except Exception as e:
            logger.error(f"清理临时上传文件时出错: {str(e)}")


# 创建全局实例供外部使用
document_processor = DocumentProcessor()
file_upload_handler = FileUploadHandler()
