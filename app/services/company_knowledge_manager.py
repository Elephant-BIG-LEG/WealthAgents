# 导入必要的库
import os
import json
from typing import List, Dict, Any, Optional
from datetime import datetime
import logging

# 导入现有的工具
from app.chunk.splitter import FinancialTextSplitter
from app.Embedding.Vectorization import vectorize_data
from app.store.faiss_store import FaissVectorStore, store_vectors_with_faiss

# 导入自定义模块
from app.services.company_service import company_service

logger = logging.getLogger(__name__)

class CompanyKnowledgeManager:
    """公司知识库管理器，用于管理公司知识库的增删改查"""
    
    def __init__(self):
        """初始化公司知识库管理器"""
        self.embedding_service = EmbeddingService()
        self.knowledge_base_path = "company_knowledge_base"
        
        # 确保知识库根目录存在
        if not os.path.exists(self.knowledge_base_path):
            os.makedirs(self.knowledge_base_path)
        
        # 初始化向量数据库
        self._initialize_vector_store()
    
    def _initialize_vector_store(self):
        """初始化向量数据库"""
        # 创建一个空的向量数据库
        dimension = 1536  # 使用OpenAI的text-embedding-3-small模型，输出维度为1536
        index = faiss.IndexFlatL2(dimension)
        
        # 创建一个空的文档存储
        docstore = InMemoryDocstore({})
        
        # 创建一个空的索引到文档的映射
        index_to_docstore_id = {}
        
        # 创建向量数据库
        self.vector_store = FAISS(
            embedding_function=self.embedding_service.get_embedding_model(),
            index=index,
            docstore=docstore,
            index_to_docstore_id=index_to_docstore_id
        )
        
        # 加载所有公司的向量数据
        self._load_all_company_vectors()
    
    def _load_all_company_vectors(self):
        """加载所有公司的向量数据"""
        # 获取所有公司列表
        companies = company_service.list_companies()
        
        for company in companies:
            self._load_company_vectors(company['company_name'])
        
        logger.info(f"向量数据库初始化完成，共加载 {len(self.vector_store.index_to_docstore_id)} 个向量")
    
    def _load_company_vectors(self, company_name: str):
        """加载指定公司的向量数据"""
        company_info = company_service.get_company(company_name=company_name)
        if not company_info:
            logger.warning(f"公司 {company_name} 不存在")
            return
        
        vector_store_path = os.path.join(company_info['knowledge_base_path'], "vector_store")
        
        # 检查向量数据库是否存在
        if os.path.exists(os.path.join(vector_store_path, "index.faiss")) and os.path.exists(os.path.join(vector_store_path, "index.pkl")):
            # 加载向量数据库
            try:
                company_vector_store = FAISS.load_local(
                    vector_store_path,
                    embedding_function=self.embedding_service.get_embedding_model(),
                    allow_dangerous_deserialization=True
                )
                
                # 将加载的向量数据库合并到全局向量数据库中
                self.vector_store.merge_from(company_vector_store)
                logger.info(f"成功加载公司 {company_name} 的向量数据库")
            except Exception as e:
                logger.error(f"加载公司 {company_name} 的向量数据库失败: {str(e)}")
    
    def add_company_knowledge(self, company_name: str, document_content: str, document_name: str = ""):
        """向公司知识库添加文档
        
        参数：
        - company_name: 公司名称
        - document_content: 文档内容
        - document_name: 文档名称
        
        返回：
        - 添加结果
        """
        try:
            # 检查公司是否存在，如果不存在则创建
            company = company_service.get_company(company_name=company_name)
            if not company:
                logger.info(f"公司 {company_name} 不存在，正在创建...")
                company_service.add_company(company_name=company_name)
                company = company_service.get_company(company_name=company_name)
        
            # 分割文档
            text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)
            documents = text_splitter.create_documents([document_content], metadatas=[{"company_name": company_name, "document_name": document_name}])
        
            # 添加到向量数据库
            self.vector_store.add_documents(documents)
        
            # 保存公司的向量数据库
            self._save_company_vector_store(company_name)
        
            # 更新公司统计信息
            company_info = company_service.get_company(company_name=company_name)
            if company_info:
                document_count = company_info.get('document_count', 0) + 1
                chunk_count = company_info.get('chunk_count', 0) + len(documents)
                company_service.update_company_statistics(company_info['id'], document_count, chunk_count)
        
            logger.info(f"向公司 {company_name} 添加了 {len(documents)} 个文本块")
            return {
                "success": True,
                "message": f"向公司 {company_name} 添加了 {len(documents)} 个文本块"
            }
        except Exception as e:
            logger.error(f"向公司 {company_name} 添加知识库失败: {str(e)}")
            return {
                "success": False,
                "message": f"向公司 {company_name} 添加知识库失败: {str(e)}"
            }
    
    def _save_company_vector_store(self, company_name: str):
        """保存公司的向量数据库"""
        company_info = company_service.get_company(company_name=company_name)
        if not company_info:
            logger.warning(f"公司 {company_name} 不存在")
            return
        
        vector_store_path = os.path.join(company_info['knowledge_base_path'], "vector_store")
        
        # 创建向量数据库目录
        if not os.path.exists(vector_store_path):
            os.makedirs(vector_store_path)
        
        # 保存向量数据库
        try:
            # 获取公司的所有文档
            company_documents = []
            for doc_id in self.vector_store.index_to_docstore_id.values():
                document = self.vector_store.docstore.search(doc_id)
                if document and document.metadata.get("company_name") == company_name:
                    company_documents.append(document)
            
            # 如果有文档，创建并保存公司向量数据库
            if company_documents:
                # 创建公司向量数据库
                company_vector_store = FAISS.from_documents(
                    company_documents,
                    embedding=self.embedding_service.get_embedding_model()
                )
                
                # 保存公司向量数据库
                company_vector_store.save_local(vector_store_path)
                logger.info(f"公司 {company_name} 的向量数据库已保存")
        except Exception as e:
            logger.error(f"保存公司 {company_name} 的向量数据库失败: {str(e)}")
    
    def query_company_knowledge(self, company_name: str, query: str, top_k: int = 3):
        """查询公司知识库
        
        参数：
        - company_name: 公司名称
        - query: 查询内容
        - top_k: 返回的最相关文档数量
        
        返回：
        - 查询结果
        """
        try:
            # 检查公司是否存在
            if not company_service.get_company(company_name=company_name):
                return {
                    "success": False,
                    "message": f"公司 {company_name} 不存在"
                }
        
            # 执行查询
            results = self.vector_store.similarity_search_with_score(query, k=top_k)
        
            # 过滤出该公司的结果
            filtered_results = []
            for result in results:
                document, score = result
                if document.metadata.get("company_name") == company_name:
                    filtered_results.append({
                        "content": document.page_content,
                        "score": score,
                        "document_name": document.metadata.get("document_name", "")
                    })
        
            # 如果没有找到相关结果，返回空列表
            if not filtered_results:
                return {
                    "success": True,
                    "message": f"未找到公司 {company_name} 的相关知识",
                    "data": []
                }
        
            # 返回查询结果
            return {
                "success": True,
                "message": f"成功查询到公司 {company_name} 的相关知识",
                "data": filtered_results
            }
        except Exception as e:
            logger.error(f"查询公司 {company_name} 的知识库失败: {str(e)}")
            return {
                "success": False,
                "message": f"查询公司 {company_name} 的知识库失败: {str(e)}"
            }
    
    def delete_company_knowledge(self, company_name: str, document_name: str = ""):
        """删除公司知识库
        
        参数：
        - company_name: 公司名称
        - document_name: 文档名称（可选，如果不指定则删除公司所有知识库）
        
        返回：
        - 删除结果
        """
        try:
            # 检查公司是否存在
            company_info = company_service.get_company(company_name=company_name)
            if not company_info:
                return {
                    "success": False,
                    "message": f"公司 {company_name} 不存在"
                }
        
            # 获取要删除的文档ID
            doc_ids_to_delete = []
            for doc_id in self.vector_store.index_to_docstore_id.values():
                document = self.vector_store.docstore.search(doc_id)
                if document and document.metadata.get("company_name") == company_name:
                    if not document_name or document.metadata.get("document_name") == document_name:
                        doc_ids_to_delete.append(doc_id)
        
            # 删除文档
            if doc_ids_to_delete:
                for doc_id in doc_ids_to_delete:
                    del self.vector_store.docstore._dict[doc_id]
                    # 从向量索引中删除
                    indices_to_delete = [i for i, id in self.vector_store.index_to_docstore_id.items() if id == doc_id]
                    for index in indices_to_delete:
                        del self.vector_store.index_to_docstore_id[index]
        
                # 重新构建向量索引
                self._rebuild_vector_index()
                
                # 保存公司的向量数据库
                self._save_company_vector_store(company_name)
        
            # 更新公司统计信息
            if not document_name:
                # 如果删除所有文档，重置统计信息
                company_service.update_company_statistics(company_info['id'], 0, 0)
            else:
                # 如果删除单个文档，需要重新计算统计信息
                self._update_company_statistics(company_name)
        
            logger.info(f"成功删除公司 {company_name} 的知识库")
            return {
                "success": True,
                "message": f"成功删除公司 {company_name} 的知识库"
            }
        except Exception as e:
            logger.error(f"删除公司 {company_name} 的知识库失败: {str(e)}")
            return {
                "success": False,
                "message": f"删除公司 {company_name} 的知识库失败: {str(e)}"
            }
    
    def _rebuild_vector_index(self):
        """重新构建向量索引"""
        # 创建一个新的向量索引
        dimension = 1536  # 使用OpenAI的text-embedding-3-small模型，输出维度为1536
        index = faiss.IndexFlatL2(dimension)
        
        # 创建一个新的文档存储
        docstore = InMemoryDocstore({})
        
        # 创建一个新的索引到文档的映射
        index_to_docstore_id = {}
        
        # 重新添加所有文档
        if self.vector_store.docstore._dict:
            new_vector_store = FAISS.from_documents(
                list(self.vector_store.docstore._dict.values()),
                embedding=self.embedding_service.get_embedding_model()
            )
            
            self.vector_store = new_vector_store
    
    def _update_company_statistics(self, company_name: str):
        """更新公司统计信息"""
        company_info = company_service.get_company(company_name=company_name)
        if not company_info:
            logger.warning(f"公司 {company_name} 不存在")
            return
        
        # 计算文档数量和文本块数量
        document_names = set()
        chunk_count = 0
        
        for doc_id in self.vector_store.index_to_docstore_id.values():
            document = self.vector_store.docstore.search(doc_id)
            if document and document.metadata.get("company_name") == company_name:
                document_names.add(document.metadata.get("document_name", ""))
                chunk_count += 1
        
        document_count = len(document_names)
        
        # 更新公司统计信息
        company_service.update_company_statistics(company_info['id'], document_count, chunk_count)
    
    def list_companies(self):
        """列出所有公司
        
        返回：
        - 公司列表
        """
        try:
            companies = company_service.list_companies()
            return {
                "success": True,
                "message": "成功获取公司列表",
                "data": companies
            }
        except Exception as e:
            logger.error(f"获取公司列表失败: {str(e)}")
            return {
                "success": False,
                "message": f"获取公司列表失败: {str(e)}"
            }
    
    def add_company(self, company_name: str, **kwargs):
        """添加公司
        
        参数：
        - company_name: 公司名称
        - kwargs: 其他公司信息字段
        
        返回：
        - 添加结果
        """
        try:
            # 检查公司是否已存在
            if company_service.get_company(company_name=company_name):
                return {
                    "success": False,
                    "message": f"公司 {company_name} 已存在"
                }
        
            # 添加公司
            company_id = company_service.add_company(company_name=company_name, **kwargs)
        
            if company_id:
                logger.info(f"成功添加公司: {company_name}")
                return {
                    "success": True,
                    "message": f"成功添加公司: {company_name}",
                    "data": {"company_id": company_id}
                }
            else:
                return {
                    "success": False,
                    "message": f"添加公司 {company_name} 失败"
                }
        except Exception as e:
            logger.error(f"添加公司 {company_name} 失败: {str(e)}")
            return {
                "success": False,
                "message": f"添加公司 {company_name} 失败: {str(e)}"
            }
    
    def delete_company(self, company_name: str):
        """删除公司
        
        参数：
        - company_name: 公司名称
        
        返回：
        - 删除结果
        """
        try:
            # 检查公司是否存在
            company_info = company_service.get_company(company_name=company_name)
            if not company_info:
                return {
                    "success": False,
                    "message": f"公司 {company_name} 不存在"
                }
        
            # 删除公司的所有文档
            self.delete_company_knowledge(company_name)
        
            # 删除公司
            if company_service.delete_company(company_name=company_name):
                logger.info(f"成功删除公司: {company_name}")
                return {
                    "success": True,
                    "message": f"成功删除公司: {company_name}"
                }
            else:
                return {
                    "success": False,
                    "message": f"删除公司 {company_name} 失败"
                }
        except Exception as e:
            logger.error(f"删除公司 {company_name} 失败: {str(e)}")
            return {
                "success": False,
                "message": f"删除公司 {company_name} 失败: {str(e)}"
            }
    
    def update_company(self, company_name: str, **kwargs):
        """更新公司信息
        
        参数：
        - company_name: 公司名称
        - kwargs: 要更新的字段
        
        返回：
        - 更新结果
        """
        try:
            # 检查公司是否存在
            if not company_service.get_company(company_name=company_name):
                return {
                    "success": False,
                    "message": f"公司 {company_name} 不存在"
                }
        
            # 更新公司信息
            if company_service.update_company(company_name=company_name, **kwargs):
                logger.info(f"成功更新公司信息: {company_name}")
                return {
                    "success": True,
                    "message": f"成功更新公司信息: {company_name}"
                }
            else:
                return {
                    "success": False,
                    "message": f"更新公司信息 {company_name} 失败"
                }
        except Exception as e:
            logger.error(f"更新公司信息 {company_name} 失败: {str(e)}")
            return {
                "success": False,
                "message": f"更新公司信息 {company_name} 失败: {str(e)}"
            }

# 导入现有的工具
from app.chunk.splitter import FinancialTextSplitter
from app.Embedding.Vectorization import vectorize_data
from app.store.faiss_store import FaissVectorStore, store_vectors_with_faiss

# 导入自定义模块
from app.services.company_service import company_service

logger = logging.getLogger(__name__)

class CompanyKnowledgeManager:
    """公司知识库管理器类"""
    
    def __init__(self, knowledge_base_path: str = "company_knowledge_base"):
        """
        初始化公司知识库管理器
        
        参数：
        - knowledge_base_path: 知识库存储路径
        """
        self.knowledge_base_path = knowledge_base_path
        self.splitter = FinancialTextSplitter()
        
        # 确保知识库目录存在
        if not os.path.exists(knowledge_base_path):
            os.makedirs(knowledge_base_path)
    
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
            
            # 检查公司是否存在，如果不存在则创建
            company = company_service.get_company(company_name=company_name)
            if not company:
                logger.info(f"公司 {company_name} 不存在，正在创建...")
                company_id = company_service.add_company(company_name=company_name)
                company = company_service.get_company(company_id=company_id)
            
            company_path = company['knowledge_base_path']
            
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
                        'total_chunks': len(chunks),
                        'company_name': company_name
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
                
                # 更新公司统计信息
                document_count = company.get('document_count', 0) + len(documents)
                chunk_count = company.get('chunk_count', 0) + len(all_chunks)
                company_service.update_company_statistics(
                    company['id'], 
                    document_count, 
                    chunk_count
                )
                
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
            # 检查公司是否存在于数据库中
            company = company_service.get_company(company_name=company_name)
            if not company:
                logger.warning(f"公司 {company_name} 的知识库不存在")
                return []
            
            # 获取公司的知识库路径
            company_path = company.get('knowledge_base_path')
            if not company_path or not os.path.exists(os.path.join(company_path, 'faiss_store')):
                logger.warning(f"无法找到公司 {company_name} 的向量存储")
                return []
            
            # 加载公司的向量存储
            company_store = FaissVectorStore(
                dimension=128,  # 默认维度，会从文件中自动加载
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
        companies = company_service.list_companies()
        return [company['company_name'] for company in companies]
    
    def get_company_info(self, company_name: str) -> Optional[Dict[str, Any]]:
        """
        获取公司知识库信息
        
        参数：
        - company_name: 公司名称
        
        返回：
        - 公司知识库信息字典
        """
        return company_service.get_company(company_name=company_name)
    
    def delete_company_knowledge(self, company_name: str) -> bool:
        """
        删除公司知识库
        
        参数：
        - company_name: 公司名称
        
        返回：
        - 操作是否成功
        """
        try:
            # 检查公司是否存在于数据库中
            company = company_service.get_company(company_name=company_name)
            if not company:
                return False
            
            # 删除公司文件夹
            import shutil
            company_path = company.get('knowledge_base_path')
            if company_path and os.path.exists(company_path):
                shutil.rmtree(company_path)
            
            # 更新公司统计信息
            company_service.update_company_statistics(
                company['id'], 
                document_count=0, 
                chunk_count=0
            )
            
            logger.info(f"公司 {company_name} 的知识库已删除")
            return True
        except Exception as e:
            logger.error(f"删除公司 {company_name} 知识库时出错: {str(e)}")
            return False
    
    def add_company(self, company_name: str, **kwargs) -> Dict[str, Any]:
        """
        添加公司
        
        参数：
        - company_name: 公司名称
        - kwargs: 其他公司信息字段
        
        返回：
        - 添加结果
        """
        try:
            # 检查公司是否已存在
            if company_service.get_company(company_name=company_name):
                return {
                    "status": "error",
                    "message": f"公司 {company_name} 已存在"
                }
        
            # 添加公司
            company_id = company_service.add_company(
                company_name=company_name,
                **kwargs
            )
        
            if company_id:
                logger.info(f"成功添加公司: {company_name}")
                return {
                    "status": "success",
                    "message": f"成功添加公司: {company_name}",
                    "data": {"company_id": company_id}
                }
            else:
                return {
                    "status": "error",
                    "message": f"添加公司 {company_name} 失败"
                }
        except Exception as e:
            logger.error(f"添加公司 {company_name} 失败: {str(e)}")
            return {
                "status": "error",
                "message": f"添加公司 {company_name} 失败: {str(e)}"
            }
    
    def delete_company(self, company_name: str) -> Dict[str, Any]:
        """
        删除公司
        
        参数：
        - company_name: 公司名称
        
        返回：
        - 删除结果
        """
        try:
            # 检查公司是否存在
            company = company_service.get_company(company_name=company_name)
            if not company:
                return {
                    "status": "error",
                    "message": f"公司 {company_name} 不存在"
                }
        
            # 删除公司的所有文档
            self.delete_company_knowledge(company_name)
        
            # 删除公司
            if company_service.delete_company(company_id=company['id']):
                logger.info(f"成功删除公司: {company_name}")
                return {
                    "status": "success",
                    "message": f"成功删除公司: {company_name}"
                }
            else:
                return {
                    "status": "error",
                    "message": f"删除公司 {company_name} 失败"
                }
        except Exception as e:
            logger.error(f"删除公司 {company_name} 失败: {str(e)}")
            return {
                "status": "error",
                "message": f"删除公司 {company_name} 失败: {str(e)}"
            }
    
    def update_company(self, company_name: str, **kwargs) -> Dict[str, Any]:
        """
        更新公司信息
        
        参数：
        - company_name: 公司名称
        - kwargs: 要更新的字段
        
        返回：
        - 更新结果
        """
        try:
            # 检查公司是否存在
            if not company_service.get_company(company_name=company_name):
                return {
                    "status": "error",
                    "message": f"公司 {company_name} 不存在"
                }
        
            # 更新公司信息
            if company_service.update_company(company_name=company_name, **kwargs):
                logger.info(f"成功更新公司信息: {company_name}")
                return {
                    "status": "success",
                    "message": f"成功更新公司信息: {company_name}"
                }
            else:
                return {
                    "status": "error",
                    "message": f"更新公司信息 {company_name} 失败"
                }
        except Exception as e:
            logger.error(f"更新公司信息 {company_name} 失败: {str(e)}")
            return {
                "status": "error",
                "message": f"更新公司信息 {company_name} 失败: {str(e)}"
            }
    
    def migrate_from_json_to_db(self) -> Dict[str, Any]:
        """
        从JSON注册表迁移到数据库
        
        返回：
        - 迁移结果统计
        """
        registry_path = os.path.join(self.knowledge_base_path, "company_registry.json")
        if not os.path.exists(registry_path):
            return {
                'status': 'error',
                'message': 'JSON注册表文件不存在'
            }
        
        # 读取JSON注册表
        try:
            with open(registry_path, 'r', encoding='utf-8') as f:
                company_registry = json.load(f)
        except Exception as e:
            return {
                'status': 'error',
                'message': f'读取JSON注册表失败: {str(e)}'
            }
        
        # 迁移数据
        migrated_count = 0
        failed_count = 0
        
        for company_name, company_info in company_registry.items():
            # 检查公司是否已存在
            if company_service.get_company(company_name=company_name):
                logger.warning(f"公司 {company_name} 已存在于数据库中，跳过")
                continue
            
            # 添加公司信息
            company_id = company_service.add_company(
                company_name=company_name,
                knowledge_base_path=company_info['knowledge_base_path']
            )
            
            if company_id:
                # 更新公司统计信息
                company_service.update_company_statistics(
                    company_id=company_id,
                    document_count=company_info['document_count'],
                    chunk_count=company_info['chunk_count']
                )
                migrated_count += 1
            else:
                failed_count += 1
        
        return {
            'status': 'success',
            'migrated_count': migrated_count,
            'failed_count': failed_count,
            'total_count': len(company_registry)
        }

# 创建全局实例
company_knowledge_manager = CompanyKnowledgeManager()
# 添加别名以保持向后兼容
knowledge_manager = company_knowledge_manager

# 初始化
if __name__ == "__main__":
    # 初始化向量数据库
    company_knowledge_manager._initialize_vector_store()