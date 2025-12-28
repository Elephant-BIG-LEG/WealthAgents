import os
import json
import numpy as np
from typing import List, Dict, Any, Optional, Tuple
import logging

from app.store.faiss_store import FaissVectorStore, store_vectors_with_faiss, load_faiss_store
from app.Embedding.Vectorization import TextVectorizer

logger = logging.getLogger(__name__)

"""
财务文档向量存储模块
扩展现有存储功能，提供财务文档特有的向量化和存储优化
"""

class FinancialVectorStore(FaissVectorStore):
    """
    财务文档专用向量存储
    扩展了基础的FaissVectorStore，增加了财务文档特有的优化功能
    """
    
    def __init__(self, dimension: int = 128, storage_path: str = "financial_vector_store", 
                 optimize_for_financial: bool = True):
        """
        初始化财务向量存储
        
        参数：
        - dimension: 向量维度
        - storage_path: 存储路径
        - optimize_for_financial: 是否为财务数据优化
        """
        super().__init__(dimension=dimension, storage_path=storage_path)
        self.optimize_for_financial = optimize_for_financial
        self.financial_vectorizer = TextVectorizer()  # 专用的向量化器
        self.metadata_index = {}  # 优化的元数据索引
        self._load_metadata_index()
    
    def _load_metadata_index(self):
        """
        加载元数据索引
        """
        index_path = os.path.join(self.storage_path, "financial_metadata_index.json")
        if os.path.exists(index_path):
            try:
                with open(index_path, 'r', encoding='utf-8') as f:
                    self.metadata_index = json.load(f)
                logger.info(f"已加载财务元数据索引，包含 {len(self.metadata_index)} 条记录")
            except Exception as e:
                logger.error(f"加载元数据索引失败: {str(e)}")
                self.metadata_index = {}
    
    def _save_metadata_index(self):
        """
        保存元数据索引
        """
        index_path = os.path.join(self.storage_path, "financial_metadata_index.json")
        try:
            with open(index_path, 'w', encoding='utf-8') as f:
                json.dump(self.metadata_index, f, ensure_ascii=False, indent=2)
            logger.info(f"已保存财务元数据索引")
        except Exception as e:
            logger.error(f"保存元数据索引失败: {str(e)}")
    
    def _enhance_financial_vectors(self, vectors: np.ndarray, texts: List[str]) -> np.ndarray:
        """
        增强财务文档向量
        对财务文档向量进行特殊处理，提高财务数据检索精度
        
        参数：
        - vectors: 原始向量
        - texts: 对应的文本列表
        
        返回：
        - 增强后的向量
        """
        if not self.optimize_for_financial or len(vectors) == 0:
            return vectors
        
        # 复制向量以避免修改原始数据
        enhanced_vectors = vectors.copy().astype(float)
        
        # 为包含财务数字和关键财务术语的文本增加权重
        for i, text in enumerate(texts):
            weight_factor = 1.0
            
            # 检查是否包含财务数字（货币、百分比等）
            contains_numbers = any(char.isdigit() for char in text)
            
            # 检查是否包含关键财务术语
            financial_terms = [
                '收入', '利润', '资产', '负债', '权益', '现金流', 
                'revenue', 'profit', 'assets', 'liabilities', 'equity', 'cash flow'
            ]
            contains_key_terms = any(term in text.lower() for term in financial_terms)
            
            # 如果包含财务数据，增加向量权重
            if contains_numbers and contains_key_terms:
                weight_factor = 1.2  # 增加20%的权重
                enhanced_vectors[i] *= weight_factor
                logger.debug(f"为索引 {i} 的财务数据向量增加权重至 {weight_factor}")
        
        # 重新归一化向量
        norms = np.linalg.norm(enhanced_vectors, axis=1, keepdims=True)
        # 避免除以零
        norms[norms == 0] = 1.0
        enhanced_vectors = enhanced_vectors / norms
        
        return enhanced_vectors
    
    def add_vectors(self, texts: List[str], vectors: np.ndarray, source: str = "financial", 
                   metadata: Optional[List[Dict[str, Any]]] = None) -> bool:
        """
        添加向量到存储，增加了财务数据特有的处理
        
        参数：
        - texts: 文本列表
        - vectors: 向量数组
        - source: 来源标识
        - metadata: 元数据列表
        
        返回：
        - 是否成功添加
        """
        try:
            # 确保元数据列表长度与文本列表一致
            if metadata is None:
                metadata = [{} for _ in texts]
            elif len(metadata) != len(texts):
                logger.error("元数据列表长度与文本列表不一致")
                return False
            
            # 增强财务向量
            enhanced_vectors = self._enhance_financial_vectors(vectors, texts)
            
            # 使用父类方法添加向量
            success = super().add_vectors(texts, enhanced_vectors, source=source, metadata=metadata)
            
            if success:
                # 更新财务元数据索引
                self._update_financial_index(texts, metadata)
                
            return success
            
        except Exception as e:
            logger.error(f"添加财务向量失败: {str(e)}")
            return False
    
    def _update_financial_index(self, texts: List[str], metadata: List[Dict[str, Any]]):
        """
        更新财务专用的元数据索引
        """
        # 获取当前向量数量（即新添加向量的起始索引）
        current_count = self.get_vector_count() - len(texts)
        
        for i, (text, meta) in enumerate(zip(texts, metadata)):
            vector_index = current_count + i
            
            # 创建财务专用索引条目
            index_entry = {
                'vector_index': vector_index,
                'source': meta.get('source', 'financial'),
                'document_type': meta.get('document_type', ''),
                'financial_tags': meta.get('financial_tags', []),
                'year': meta.get('year'),
                'quarter': meta.get('quarter')
            }
            
            # 生成索引键
            index_key = f"{index_entry['source']}_{vector_index}"
            self.metadata_index[index_key] = index_entry
        
        # 保存更新后的索引
        self._save_metadata_index()
    
    def search_similar_with_filter(self, query_vector: np.ndarray, top_k: int = 5, 
                                 year_filter: Optional[int] = None,
                                 quarter_filter: Optional[int] = None,
                                 tags_filter: Optional[List[str]] = None) -> List[Tuple[str, float, Dict[str, Any]]]:
        """
        带过滤器的相似搜索
        
        参数：
        - query_vector: 查询向量
        - top_k: 返回结果数量
        - year_filter: 年份过滤
        - quarter_filter: 季度过滤
        - tags_filter: 标签过滤
        
        返回：
        - 搜索结果列表 [(text, similarity, metadata), ...]
        """
        try:
            # 首先进行基本的相似搜索，获取更多候选结果
            candidates = super().search_similar(query_vector, top_k * 3)  # 获取3倍结果用于过滤
            
            # 如果没有过滤条件，直接返回原始结果
            if year_filter is None and quarter_filter is None and tags_filter is None:
                return candidates[:top_k]
            
            # 应用过滤条件
            filtered_results = []
            for text, similarity, metadata in candidates:
                # 获取完整元数据
                full_metadata = self._get_complete_metadata(metadata.get('vector_index'))
                
                # 年份过滤
                if year_filter is not None:
                    if full_metadata.get('year') != year_filter:
                        continue
                
                # 季度过滤
                if quarter_filter is not None:
                    if full_metadata.get('quarter') != quarter_filter:
                        continue
                
                # 标签过滤
                if tags_filter is not None and tags_filter:
                    has_matching_tag = False
                    chunk_tags = full_metadata.get('financial_tags', [])
                    for tag in tags_filter:
                        if tag in chunk_tags:
                            has_matching_tag = True
                            break
                    if not has_matching_tag:
                        continue
                
                # 通过所有过滤条件，添加到结果中
                filtered_results.append((text, similarity, full_metadata))
            
            # 按相似度排序并返回指定数量
            filtered_results.sort(key=lambda x: x[1], reverse=True)
            return filtered_results[:top_k]
            
        except Exception as e:
            logger.error(f"带过滤条件的搜索失败: {str(e)}")
            return []
    
    def _get_complete_metadata(self, vector_index: int) -> Dict[str, Any]:
        """
        获取完整的元数据信息
        """
        # 从索引中查找
        for key, entry in self.metadata_index.items():
            if entry.get('vector_index') == vector_index:
                return entry
        
        # 如果没找到，返回基础信息
        return {'vector_index': vector_index}
    
    def get_financial_statistics(self) -> Dict[str, Any]:
        """
        获取财务向量存储的统计信息
        
        返回：
        - 统计信息字典
        """
        stats = {
            'total_vectors': self.get_vector_count(),
            'total_metadata_entries': len(self.metadata_index),
            'years_available': set(),
            'quarters_available': set(),
            'tags_distribution': {},
            'document_types': {}
        }
        
        # 统计年份、季度和标签分布
        for entry in self.metadata_index.values():
            # 统计年份
            if entry.get('year'):
                stats['years_available'].add(entry['year'])
            
            # 统计季度
            if entry.get('quarter'):
                stats['quarters_available'].add(entry['quarter'])
            
            # 统计标签分布
            for tag in entry.get('financial_tags', []):
                stats['tags_distribution'][tag] = stats['tags_distribution'].get(tag, 0) + 1
            
            # 统计文档类型
            doc_type = entry.get('document_type', 'unknown')
            stats['document_types'][doc_type] = stats['document_types'].get(doc_type, 0) + 1
        
        # 转换集合为排序列表
        stats['years_available'] = sorted(list(stats['years_available']))
        stats['quarters_available'] = sorted(list(stats['quarters_available']))
        
        return stats
    
    def clear_financial_store(self):
        """
        清空财务向量存储
        """
        try:
            # 调用父类方法清空存储
            super().clear_store()
            
            # 清空元数据索引
            self.metadata_index = {}
            self._save_metadata_index()
            
            logger.info("已清空财务向量存储")
            return True
        except Exception as e:
            logger.error(f"清空财务向量存储失败: {str(e)}")
            return False


def create_financial_vector_store(company_name: str, dimension: int = 128) -> FinancialVectorStore:
    """
    创建财务向量存储的便捷函数
    
    参数：
    - company_name: 公司名称
    - dimension: 向量维度
    
    返回：
    - 财务向量存储实例
    """
    # 生成标准化的存储路径
    storage_path = os.path.join("financial_analysis_knowledge_base", 
                              company_name.replace(' ', '_'), 
                              "financial_vector_store")
    
    # 确保存储目录存在
    os.makedirs(storage_path, exist_ok=True)
    
    # 创建并返回向量存储实例
    return FinancialVectorStore(dimension=dimension, storage_path=storage_path)


def vectorize_financial_documents(documents: List[Dict[str, str]], batch_size: int = 10) -> Dict[str, Any]:
    """
    向量化处理财务文档集合
    
    参数：
    - documents: 文档列表，每个文档包含 {'text': 文本内容, 'metadata': 元数据}
    - batch_size: 批量处理大小
    
    返回：
    - 包含向量和元数据的结果字典
    """
    results = {
        'vectors': [],
        'texts': [],
        'metadata': [],
        'statistics': {
            'total_documents': len(documents),
            'success_count': 0,
            'error_count': 0,
            'errors': []
        }
    }
    
    vectorizer = TextVectorizer()
    
    # 批量处理文档
    for i in range(0, len(documents), batch_size):
        batch = documents[i:i + batch_size]
        
        # 提取批量文本
        batch_texts = [doc.get('text', '') for doc in batch]
        batch_metadata = [doc.get('metadata', {}) for doc in batch]
        
        try:
            # 批量向量化
            batch_vectors = vectorizer.vectorize_texts(batch_texts)
            
            # 添加到结果中
            results['vectors'].extend(batch_vectors)
            results['texts'].extend(batch_texts)
            results['metadata'].extend(batch_metadata)
            results['statistics']['success_count'] += len(batch)
            
            logger.info(f"成功向量化第 {i+1}-{min(i+batch_size, len(documents))} 个文档")
            
        except Exception as e:
            logger.error(f"向量化批量文档时出错: {str(e)}")
            results['statistics']['error_count'] += len(batch)
            results['statistics']['errors'].append(str(e))
    
    # 将向量列表转换为numpy数组
    if results['vectors']:
        results['vectors'] = np.array(results['vectors'])
    
    return results


# 创建全局实例供服务使用
financial_vector_service = {
    'create_store': create_financial_vector_store,
    'vectorize_documents': vectorize_financial_documents
}
