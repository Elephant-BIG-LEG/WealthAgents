import os
import json
from typing import List, Dict, Any, Optional
from datetime import datetime
import logging

# 导入现有的工具
from app.chunk.splitter import FinancialTextSplitter
from app.Embedding.Vectorization import vectorize_data
from app.store.faiss_store import FaissVectorStore, store_vectors_with_faiss

logger = logging.getLogger(__name__)

"""
公司知识库管理器
负责：
1. 处理上传的公司资料
2. 提取文本内容
3. 构建和管理公司知识库
4. 提供知识库查询接口
"""

class CompanyKnowledgeManager:
    """公司知识库管理器类"""
    
    def __init__(self, knowledge_base_path: str = "company_knowledge_base"):
        """
        初始化公司知识库管理器
        
        参数：
        - knowledge_base_path: 知识库存储路径
        """
        self.knowledge_base_path = knowledge_base_path
        self.company_registry = self._load_company_registry()
        self.splitter = FinancialTextSplitter()
        
        # 确保知识库目录存在
        if not os.path.exists(knowledge_base_path):
            os.makedirs(knowledge_base_path)
    
    def _load_company_registry(self) -> Dict[str, Dict[str, Any]]:
        """
        加载公司注册表，记录已存在的公司知识库信息
        """
        registry_path = os.path.join(self.knowledge_base_path, "company_registry.json")
        if os.path.exists(registry_path):
            try:
                with open(registry_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                logger.error(f"加载公司注册表失败: {str(e)}")
                return {}
        return {}
    
    def _save_company_registry(self):
        """
        保存公司注册表
        """
        registry_path = os.path.join(self.knowledge_base_path, "company_registry.json")
        try:
            with open(registry_path, 'w', encoding='utf-8') as f:
                json.dump(self.company_registry, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"保存公司注册表失败: {str(e)}")
    
    def add_company_knowledge(self, company_name: str, documents: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        为公司添加知识库内容
        
        参数：
        - company_name: 公司名称
        - documents: 文档列表，每个文档包含：
            - file_name: 文件名
            - content: 文本内容
            - document_type: 文档类型（如"财务报表"、"公司规模"等）
            - upload_time: 上传时间
            - year: 年份（可选）
        
        返回：
        - 操作结果字典，包含状态和统计信息
        """
        try:
            logger.info(f"开始为公司 {company_name} 构建知识库")
            
            # 创建公司特定的知识库路径
            company_path = os.path.join(self.knowledge_base_path, company_name.replace(' ', '_'))
            if not os.path.exists(company_path):
                os.makedirs(company_path)
            
            # 收集所有文本内容并进行分块处理
            all_chunks = []
            document_metadata = []
            
            for doc in documents:
                # 使用财务文本分块器处理内容
                chunks = self.splitter.split_text(doc.get('content', ''))
                all_chunks.extend(chunks)
                
                # 为每个分块记录文档元数据
                for i, chunk in enumerate(chunks):
                    chunk_metadata = {
                        'file_name': doc.get('file_name', 'unknown'),
                        'document_type': doc.get('document_type', 'general'),
                        'upload_time': doc.get('upload_time', datetime.now().isoformat()),
                        'chunk_index': i,
                        'total_chunks': len(chunks)
                    }
                    if 'year' in doc:
                        chunk_metadata['year'] = doc['year']
                    document_metadata.append(chunk_metadata)
            
            # 向量化处理后的文本块
            if all_chunks:
                vectors = vectorize_data(all_chunks)
                
                # 创建或加载公司知识库的向量存储
                company_store = FaissVectorStore(
                    dimension=len(vectors[0]),
                    storage_path=os.path.join(company_path, 'faiss_store')
                )
                
                # 准备来源信息，包含公司名称
                source_info = f"company_{company_name}"
                
                # 添加向量到存储
                company_store.add_vectors(all_chunks, vectors, source=source_info)
                
                # 保存文档元数据
                self._save_document_metadata(company_path, document_metadata)
                
                # 更新公司注册表
                self._update_company_registry(company_name, {
                    'document_count': len(documents),
                    'chunk_count': len(all_chunks),
                    'last_updated': datetime.now().isoformat(),
                    'knowledge_base_path': company_path
                })
                
                logger.info(f"公司 {company_name} 知识库构建完成，共添加 {len(documents)} 个文档，{len(all_chunks)} 个文本块")
                
                return {
                    'status': 'success',
                    'message': f'公司 {company_name} 知识库构建成功',
                    'statistics': {
                        'document_count': len(documents),
                        'chunk_count': len(all_chunks),
                        'vector_dimension': len(vectors[0]) if vectors else 0
                    }
                }
            else:
                logger.warning(f"公司 {company_name} 没有可处理的文本内容")
                return {
                    'status': 'warning',
                    'message': '没有可处理的文本内容',
                    'statistics': {
                        'document_count': len(documents),
                        'chunk_count': 0
                    }
                }
        
        except Exception as e:
            logger.error(f"构建公司 {company_name} 知识库时出错: {str(e)}")
            return {
                'status': 'error',
                'message': f'构建知识库时出错: {str(e)}',
                'error': str(e)
            }
    
    def _save_document_metadata(self, company_path: str, metadata_list: List[Dict[str, Any]]):
        """
        保存文档元数据
        """
        metadata_path = os.path.join(company_path, "document_metadata.json")
        try:
            with open(metadata_path, 'w', encoding='utf-8') as f:
                json.dump(metadata_list, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"保存文档元数据失败: {str(e)}")
    
    def _update_company_registry(self, company_name: str, info: Dict[str, Any]):
        """
        更新公司注册表信息
        """
        if company_name not in self.company_registry:
            self.company_registry[company_name] = {
                'created_at': datetime.now().isoformat(),
                'versions': []
            }
        
        # 记录版本历史
        self.company_registry[company_name]['versions'].append(info.copy())
        
        # 更新当前信息
        for key, value in info.items():
            self.company_registry[company_name][key] = value
        
        # 保存更新后的注册表
        self._save_company_registry()
    
    def query_company_knowledge(self, company_name: str, query_text: str, top_k: int = 5) -> List[Dict[str, Any]]:
        """
        查询公司知识库
        
        参数：
        - company_name: 公司名称
        - query_text: 查询文本
        - top_k: 返回最相似的前k个结果
        
        返回：
        - 查询结果列表，每个结果包含：
            - text: 匹配的文本内容
            - similarity: 相似度分数
            - metadata: 元数据信息
        """
        try:
            # 检查公司是否存在于注册表中
            if company_name not in self.company_registry:
                logger.warning(f"公司 {company_name} 的知识库不存在")
                return []
            
            # 加载公司的向量存储
            company_path = self.company_registry[company_name].get('knowledge_base_path')
            if not company_path or not os.path.exists(os.path.join(company_path, 'faiss_store')):
                logger.warning(f"无法找到公司 {company_name} 的向量存储")
                return []
            
            # 获取向量维度
            store_stats = json.loads(
                open(os.path.join(company_path, 'faiss_store', 'metadata.json')).read()
            ) if os.path.exists(os.path.join(company_path, 'faiss_store', 'metadata.json')) else []
            dimension = len(store_stats[0].get('vector_index', 128)) if store_stats else 128
            
            # 加载向量存储
            company_store = FaissVectorStore(
                dimension=dimension,
                storage_path=os.path.join(company_path, 'faiss_store')
            )
            
            # 向量化查询文本
            from app.Embedding.Vectorization import TextVectorizer
            vectorizer = TextVectorizer()
            query_vector = vectorizer.vectorize_text(query_text)
            
            # 查询相似内容
            results = company_store.search_similar(query_vector, top_k)
            
            # 格式化返回结果
            formatted_results = []
            for text, similarity, metadata in results:
                formatted_results.append({
                    'text': text,
                    'similarity': similarity,
                    'metadata': metadata
                })
            
            return formatted_results
        
        except Exception as e:
            logger.error(f"查询公司 {company_name} 知识库时出错: {str(e)}")
            return []
    
    def list_companies(self) -> List[str]:
        """
        列出所有已构建知识库的公司
        
        返回：
        - 公司名称列表
        """
        return list(self.company_registry.keys())
    
    def get_company_info(self, company_name: str) -> Optional[Dict[str, Any]]:
        """
        获取公司知识库信息
        
        参数：
        - company_name: 公司名称
        
        返回：
        - 公司知识库信息字典
        """
        return self.company_registry.get(company_name)
    
    def delete_company_knowledge(self, company_name: str) -> bool:
        """
        删除公司知识库
        
        参数：
        - company_name: 公司名称
        
        返回：
        - 操作是否成功
        """
        try:
            if company_name not in self.company_registry:
                return False
            
            # 删除公司文件夹
            import shutil
            company_path = self.company_registry[company_name].get('knowledge_base_path')
            if company_path and os.path.exists(company_path):
                shutil.rmtree(company_path)
            
            # 从注册表中移除
            del self.company_registry[company_name]
            self._save_company_registry()
            
            logger.info(f"公司 {company_name} 的知识库已删除")
            return True
        except Exception as e:
            logger.error(f"删除公司 {company_name} 知识库时出错: {str(e)}")
            return False


# 创建全局实例供外部使用
knowledge_manager = CompanyKnowledgeManager()
