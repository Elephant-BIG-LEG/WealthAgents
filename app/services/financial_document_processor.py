# -*- coding: utf-8 -*-
"""
财务文档处理器模块
"""
import os
import json
import logging
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime

# 配置日志
logger = logging.getLogger(__name__)

class FinancialDocumentProcessor:
    """
    财务文档处理器，负责处理财务文档的上传、解析、分割和向量化
    """
    def __init__(self, knowledge_base_path: str = "./financial_knowledge_base"):
        """
        初始化财务文档处理器
        
        参数：
        - knowledge_base_path: 知识库存储路径
        """
        self.knowledge_base_path = knowledge_base_path
        self.document_registry_path = os.path.join(self.knowledge_base_path, "document_registry.json")
        self.document_registry = self._load_document_registry()
        
        # 确保知识库目录存在
        if not os.path.exists(self.knowledge_base_path):
            os.makedirs(self.knowledge_base_path)
            logger.info(f"创建知识库目录: {self.knowledge_base_path}")
    
    def _load_document_registry(self) -> Dict[str, Dict[str, Any]]:
        """
        加载文档注册表
        
        返回：
        - 文档注册表字典
        """
        if os.path.exists(self.document_registry_path):
            try:
                with open(self.document_registry_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                logger.error(f"加载文档注册表时出错: {str(e)}")
                return {}
        else:
            return {}
    
    def _save_document_registry(self):
        """
        保存文档注册表
        """
        try:
            with open(self.document_registry_path, 'w', encoding='utf-8') as f:
                json.dump(self.document_registry, f, ensure_ascii=False, indent=2)
            logger.info("文档注册表保存成功")
        except Exception as e:
            logger.error(f"保存文档注册表时出错: {str(e)}")
    
    def build_company_knowledge_base(self, company_name: str, documents: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        为指定公司构建财务知识库
        
        参数：
        - company_name: 公司名称
        - documents: 文档列表，每个文档包含'file_path'和'file_name'
        
        返回：
        - 包含构建结果和统计信息的字典
        """
        try:
            logger.info(f"开始为公司 {company_name} 构建财务知识库")
            
            # 创建公司特定的知识库路径
            company_path = os.path.join(self.knowledge_base_path, company_name.replace(' ', '_'))
            if not os.path.exists(company_path):
                os.makedirs(company_path)
            
            # 初始化公司文档信息
            if company_name not in self.document_registry:
                self.document_registry[company_name] = {
                    'documents': {},
                    'created_at': datetime.now().isoformat(),
                    'updated_at': datetime.now().isoformat()
                }
            
            # 处理每个文档
            processed_docs = []
            for doc in documents:
                file_path = doc.get('file_path')
                file_name = doc.get('file_name')
                
                if not file_path or not file_name:
                    logger.warning("文档缺少必要的路径或文件名信息")
                    continue
                
                # 处理财务文件
                result = self.process_financial_file(file_path, file_name)
                if 'error' in result:
                    logger.error(f"处理文件 {file_name} 失败: {result['error']}")
                    continue
                
                # 保存处理后的文档信息
                doc_info = {
                    'file_name': file_name,
                    'original_path': file_path,
                    'processed_at': datetime.now().isoformat()
                }
                
                self.document_registry[company_name]['documents'][file_name] = doc_info
                processed_docs.append(file_name)
            
            # 更新注册表
            self.document_registry[company_name]['updated_at'] = datetime.now().isoformat()
            self._save_document_registry()
            
            logger.info(f"公司 {company_name} 的财务知识库构建完成，成功处理 {len(processed_docs)} 个文档")
            
            return {
                'status': 'success',
                'message': f'为公司 {company_name} 成功构建财务知识库',
                'processed_documents': processed_docs,
                'total_documents': len(processed_docs),
                'knowledge_base_path': company_path
            }
            
        except Exception as e:
            logger.error(f"为公司 {company_name} 构建财务知识库时出错: {str(e)}")
            return {
                'status': 'error',
                'message': f'构建财务知识库失败: {str(e)}'
            }
    
    def query_company_knowledge(self, company_name: str, query: str, top_k: int = 5) -> List[Dict[str, Any]]:
        """
        查询公司的财务知识库
        
        参数：
        - company_name: 公司名称
        - query: 查询文本
        - top_k: 返回结果数量
        
        返回：
        - 查询结果列表
        """
        try:
            if company_name not in self.document_registry:
                logger.warning(f"公司 {company_name} 的财务知识库不存在")
                return []
            
            # 这里应该实现向量搜索，但目前返回模拟结果
            company_docs = self.document_registry[company_name]['documents']
            
            # 模拟搜索结果
            results = []
            for doc_name, doc_info in company_docs.items():
                results.append({
                    'file_name': doc_name,
                    'content': f"这是来自 {doc_name} 的示例内容摘要",
                    'score': 0.9,
                    'metadata': doc_info
                })
            
            # 格式化结果
            formatted_results = []
            for result in results[:top_k]:
                formatted_results.append({
                    'document': result['file_name'],
                    'content': result['content'],
                    'relevance': result['score']
                })
            
            return formatted_results
            
        except Exception as e:
            logger.error(f"查询公司 {company_name} 财务知识库时出错: {str(e)}")
            return []
    
    def get_company_list(self) -> List[str]:
        """
        获取所有拥有财务知识库的公司列表
        
        返回：
        - 公司名称列表
        """
        return list(self.document_registry.keys())
    
    def get_company_documents(self, company_name: str) -> Dict[str, Dict[str, Any]]:
        """
        获取特定公司的所有文档信息
        
        参数：
        - company_name: 公司名称
        
        返回：
        - 文档信息字典
        """
        if company_name not in self.document_registry:
            return {}
        
        return self.document_registry[company_name].get('documents', {})
    
    def delete_company_knowledge(self, company_name: str) -> bool:
        """
        删除公司的财务知识库
        
        参数：
        - company_name: 公司名称
        
        返回：
        - 操作是否成功
        """
        try:
            if company_name not in self.document_registry:
                return False
            
            # 删除公司文件夹
            import shutil
            company_path = os.path.join(self.knowledge_base_path, company_name.replace(' ', '_'))
            if os.path.exists(company_path):
                shutil.rmtree(company_path)
            
            # 从注册表中移除
            del self.document_registry[company_name]
            self._save_document_registry()
            
            logger.info(f"公司 {company_name} 的财务知识库已删除")
            return True
        except Exception as e:
            logger.error(f"删除公司 {company_name} 财务知识库时出错: {str(e)}")
            return False
    
    def process_financial_file(self, file_path: str, file_name: str) -> Dict[str, Any]:
        """
        处理单个财务文件并提取内容
        
        参数：
        - file_path: 文件路径
        - file_name: 文件名
        
        返回：
        - 包含文件名和内容的字典
        """
        try:
            logger.info(f"开始处理文件: {file_name} ({file_path})")
            
            # 根据文件扩展名处理不同类型的文件
            file_ext = os.path.splitext(file_name)[1].lower()
            content = ""
            
            if file_ext in [".txt", ".md"]:
                # 文本文件
                with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read()
            
            elif file_ext == ".pdf":
                # PDF文件 - 尝试导入PyPDF2进行处理
                try:
                    import PyPDF2
                    with open(file_path, 'rb') as f:
                        reader = PyPDF2.PdfReader(f)
                        content = ""
                        for page in reader.pages:
                            content += page.extract_text() or ""
                except ImportError:
                    logger.warning("PyPDF2未安装，无法处理PDF文件")
                    return {
                        'file_name': file_name,
                        'content': "",
                        'error': "PDF处理模块未安装"
                    }
                except Exception as e:
                    logger.error(f"处理PDF文件时出错: {str(e)}")
                    return {
                        'file_name': file_name,
                        'content': "",
                        'error': f"PDF处理错误: {str(e)}"
                    }
            
            elif file_ext in [".docx", ".doc"]:
                # Word文件 - 尝试导入python-docx进行处理
                try:
                    import docx
                    doc = docx.Document(file_path)
                    content = "\n".join([para.text for para in doc.paragraphs])
                except ImportError:
                    logger.warning("python-docx未安装，无法处理Word文件")
                    return {
                        'file_name': file_name,
                        'content': "",
                        'error': "Word处理模块未安装"
                    }
                except Exception as e:
                    logger.error(f"处理Word文件时出错: {str(e)}")
                    return {
                        'file_name': file_name,
                        'content': "",
                        'error': f"Word处理错误: {str(e)}"
                    }
            
            else:
                logger.warning(f"不支持的文件格式: {file_ext}")
                # 尝试作为文本文件读取
                try:
                    with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                        content = f.read()
                except:
                    content = ""
            
            logger.info(f"文件 {file_name} 处理完成，内容长度: {len(content)} 字符")
            
            return {
                'file_name': file_name,
                'content': content
            }
            
        except Exception as e:
            logger.error(f"处理文件 {file_name} 时出错: {str(e)}")
            return {
                'file_name': file_name,
                'content': "",
                'error': str(e)
            }

# 创建全局实例供外部使用
financial_document_processor = FinancialDocumentProcessor()