import numpy as np
import faiss
import json
import os
import platform
import re
from typing import List, Tuple, Dict, Any
from datetime import datetime

"""
TODO
写入向量库
"""

class FaissVectorStore:
    """基于Faiss的向量存储类"""

    def _clean_path(self, path: str) -> str:
        """
        清理路径字符串 - 改进版本
        - 处理路径中的空格
        - 移除非法字符
        - 标准化路径格式
        """
        if not path:
            return path
        
        # 使用正则表达式替换所有空格（包括连续空格）
        import re
        path = re.sub(r'\s+', '_', path)
        
        # 标准化路径
        path = os.path.normpath(path)
        
        return path

    def _load_or_create_index(self):
        """
        加载或创建Faiss索引 - 简化版本，与_save_index保持一致的路径逻辑
        """
        try:
            # 尝试从简单路径加载索引，与_save_index保持一致
            simple_path = "faiss_index.bin"
            print(f"\n_load_or_create_index: 尝试加载简单路径 = {simple_path}")
            
            # 检查文件是否存在且大小大于0
            file_exists = os.path.exists(simple_path)
            file_size = os.path.getsize(simple_path) if file_exists else 0
            print(f"_load_or_create_index: 文件存在 = {file_exists}, 文件大小 = {file_size} 字节")
            
            if file_exists and file_size > 0:
                # 尝试加载索引
                try:
                    index = faiss.read_index(simple_path)
                    print(f"成功加载Faiss索引，包含 {index.ntotal} 个向量")
                    # 更新索引文件路径以保持一致
                    self.index_file = simple_path
                    return index
                except Exception as e:
                    print(f"从简单路径加载索引时出错: {str(e)}")
            
            # 如果简单路径失败，尝试从固定路径加载
            fixed_path = "C:\\faiss_index.bin"
            print(f"_load_or_create_index: 尝试加载固定路径 = {fixed_path}")
            
            file_exists = os.path.exists(fixed_path)
            file_size = os.path.getsize(fixed_path) if file_exists else 0
            
            if file_exists and file_size > 0:
                try:
                    index = faiss.read_index(fixed_path)
                    print(f"成功从固定路径加载Faiss索引，包含 {index.ntotal} 个向量")
                    self.index_file = fixed_path
                    return index
                except Exception as e:
                    print(f"从固定路径加载索引时出错: {str(e)}")
            
            # 文件不存在、大小为0或加载失败，创建新索引
            print(f"文件不存在、大小为0或加载失败，创建新的Faiss索引")
            
            # 使用内积索引，适合归一化向量的余弦相似度计算
            # 使用IndexIDMap包装IndexFlatIP以支持add_with_ids
            index = faiss.IndexIDMap(faiss.IndexFlatIP(self.dimension))
            
            # 保存新创建的空索引
            self.index = index  # 临时设置self.index用于保存
            self._save_index()
            print(f"成功创建新的Faiss索引")
            return index
            
        except Exception as e:
            print(f"_load_or_create_index 方法出错: {str(e)}")
            # 创建一个空索引作为后备
            index = faiss.IndexIDMap(faiss.IndexFlatIP(self.dimension))
            print(f"创建了空的Faiss索引作为后备")
            return index
    def __init__(self, dimension: int = 128, storage_path: str = "faiss_database"):
        """初始化Faiss向量存储"""
        self.dimension = dimension
        
        # 1. 严格清理存储路径 - 使用正则表达式替换所有空格
        import re
        clean_storage_path = re.sub(r'\s+', '_', storage_path)
        print(f"DEBUG: 原始storage_path = {storage_path}")
        print(f"DEBUG: 清理后storage_path = {clean_storage_path}")
        
        # 2. 使用系统标准化路径
        clean_storage_path = os.path.normpath(clean_storage_path)
        print(f"DEBUG: 标准化后storage_path = {clean_storage_path}")
        
        # 3. 使用当前工作目录作为基准创建路径
        base_path = os.getcwd()
        self.storage_path = os.path.join(base_path, clean_storage_path)
        print(f"DEBUG: 最终storage_path = {self.storage_path}")
        
        # 4. 创建存储目录（包括所有父目录）- 增强的目录创建逻辑
        self._ensure_directory_exists()
        
        # 5. 使用清理后的路径创建文件路径
        self.index_file = os.path.join(self.storage_path, "faiss_index.bin")
        self.metadata_file = os.path.join(self.storage_path, "metadata.json")
        print(f"DEBUG: 最终index_file = {self.index_file}")
        
        # 6. 初始化Faiss索引
        self.index = self._load_or_create_index()

        # 7. 初始化元数据
        self.metadata = self._load_metadata()

        # 8. ID映射（Faiss内部ID到自定义ID）
        self.id_mapping = {}  # {faiss_id: custom_id}
        self.reverse_id_mapping = {}  # {custom_id: faiss_id}

        # 9. 如果索引中有数据，重建ID映射
        if hasattr(self.index, 'ntotal') and self.index.ntotal > 0:
            self._rebuild_id_mapping()

    def _ensure_directory_exists(self):
        """
        增强的目录创建逻辑，确保所有父目录都存在
        """
        try:
            # 确保所有父目录存在
            os.makedirs(self.storage_path, exist_ok=True)
            
            # 额外检查，确保目录真的存在
            if not os.path.exists(self.storage_path):
                # 尝试使用不同的方式创建目录
                parent_dir = os.path.dirname(self.storage_path)
                if not os.path.exists(parent_dir):
                    os.makedirs(parent_dir, exist_ok=True)
                os.mkdir(self.storage_path)
            
            # 验证目录存在且可写
            if not os.path.exists(self.storage_path):
                raise FileNotFoundError(f"无法创建存储目录: {self.storage_path}")
            
            if not os.access(self.storage_path, os.W_OK):
                raise PermissionError(f"存储目录不可写: {self.storage_path}")
                
        except Exception as e:
            # 记录详细的目录创建失败信息
            print(f"警告：创建目录时发生错误 {self.storage_path}: {str(e)}")
            # 尝试使用当前工作目录作为备选
            alt_path = os.path.join(os.getcwd(), "faiss_store_backup")
            print(f"尝试使用备选路径: {alt_path}")
            os.makedirs(alt_path, exist_ok=True)
            self.storage_path = alt_path
            self.index_file = os.path.join(alt_path, "faiss_index.bin")
            self.metadata_file = os.path.join(alt_path, "metadata.json")

    def _load_metadata(self) -> List[Dict[str, Any]]:
        """加载元数据"""
        try:
            if os.path.exists(self.metadata_file):
                with open(self.metadata_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
        except Exception as e:
            print(f"加载元数据时出错: {str(e)}")
        return []

    def _save_index(self):
        """
        保存Faiss索引 - 简化版本，避免复杂路径问题
        """
        try:
            # 首先尝试使用当前目录下的简单文件名，完全避免路径问题
            simple_path = "faiss_index.bin"
            print(f"\n尝试保存到简单路径: {simple_path}")
            
            try:
                # 直接保存到当前目录
                faiss.write_index(self.index, simple_path)
                print(f"成功保存Faiss索引到简单路径: {simple_path}")
                self.index_file = simple_path
                return
            except Exception as e1:
                print(f"简单路径保存失败: {str(e1)}")
            
            # 如果简单路径失败，尝试使用固定路径
            fixed_path = "C:\\faiss_index.bin"
            print(f"尝试保存到固定路径: {fixed_path}")
            
            try:
                faiss.write_index(self.index, fixed_path)
                print(f"成功保存Faiss索引到固定路径: {fixed_path}")
                self.index_file = fixed_path
                return
            except Exception as e2:
                print(f"固定路径保存失败: {str(e2)}")
            
            # 如果所有方法都失败，使用内存索引
            print("警告：所有保存尝试都失败，索引将只保存在内存中")
            
        except Exception as e:
            print(f"保存索引时出错: {str(e)}")
            print("警告：所有保存尝试都失败，索引将只保存在内存中")

    def _save_metadata(self):
        """保存元数据"""
        try:
            # 确保目录存在
            self._ensure_directory_exists()
            
            # 修复元数据文件路径中的空格问题
            safe_metadata_file = self.metadata_file.replace(' ', '_')
            
            with open(safe_metadata_file, 'w', encoding='utf-8') as f:
                json.dump(self.metadata, f, ensure_ascii=False, indent=2)
            
            # 更新元数据文件路径
            self.metadata_file = safe_metadata_file
            print(f"成功保存元数据到: {self.metadata_file}")
        except Exception as e:
            print(f"保存元数据时出错: {str(e)}")

    def _rebuild_id_mapping(self):
        """重建ID映射"""
        self.id_mapping = {}
        self.reverse_id_mapping = {}
        for i, meta in enumerate(self.metadata):
            faiss_id = i  # 假设Faiss ID与元数据索引对应
            custom_id = meta.get("id", i)
            self.id_mapping[faiss_id] = custom_id
            self.reverse_id_mapping[custom_id] = faiss_id

    def add_vectors(self, texts: List[str], vectors: List[np.ndarray], source: str = "unknown"):
        """
        添加向量到Faiss索引中
        :param texts: 原始文本列表
        :param vectors: 向量列表
        :param source: 数据来源
        """
        if len(texts) != len(vectors):
            raise ValueError("文本数量和向量数量不匹配")

        if len(vectors) == 0:
            return

        # 转换向量为numpy数组并确保类型正确
        vectors_array = np.array(vectors).astype('float32')

        # 归一化向量（对于内积索引，这等同于余弦相似度）
        faiss.normalize_L2(vectors_array)

        # 生成新的ID
        start_id = len(self.metadata)
        ids = np.arange(start_id, start_id +
                        len(vectors_array)).astype('int64')

        # 添加到Faiss索引
        self.index.add_with_ids(vectors_array, ids)

        # 添加元数据
        for i, text in enumerate(texts):
            custom_id = start_id + i
            faiss_id = ids[i]

            metadata_entry = {
                "id": custom_id,
                "text": text,
                "source": source,
                "timestamp": datetime.now().isoformat(),
                "vector_index": int(faiss_id)
            }
            self.metadata.append(metadata_entry)

            # 更新ID映射
            self.id_mapping[faiss_id] = custom_id
            self.reverse_id_mapping[custom_id] = faiss_id

        # 保存索引和元数据
        self._save_index()
        self._save_metadata()

        print(f"成功添加 {len(vectors)} 条向量数据到Faiss数据库")

    def search_similar(self, query_vector: np.ndarray, top_k: int = 5) -> List[Tuple[str, float, Dict]]:
        """
        搜索相似向量
        :param query_vector: 查询向量
        :param top_k: 返回最相似的前k个结果
        :return: (文本, 相似度, 元数据) 的元组列表
        """
        if self.index.ntotal == 0:
            return []

        # 确保查询向量是正确的形状和类型
        if query_vector.ndim == 1:
            query_vector = query_vector.reshape(1, -1)

        query_vector = query_vector.astype('float32')

        # 归一化查询向量
        faiss.normalize_L2(query_vector)

        # 搜索相似向量
        distances, indices = self.index.search(query_vector, top_k)

        # 构建结果
        results = []
        for i, (distance, faiss_id) in enumerate(zip(distances[0], indices[0])):
            # Faiss返回-1表示没有找到足够的结果
            if faiss_id == -1:
                continue

            # 通过ID映射找到对应的元数据
            if faiss_id in self.id_mapping:
                custom_id = self.id_mapping[faiss_id]
                if custom_id < len(self.metadata):
                    metadata = self.metadata[custom_id]
                    text = metadata["text"]
                    # 距离是内积，转换为相似度分数
                    similarity = float(distance)
                    results.append((text, similarity, metadata))

        return results

    def get_vector_count(self) -> int:
        """获取向量总数"""
        return self.index.ntotal if hasattr(self.index, 'ntotal') else 0

    def get_metadata_count(self) -> int:
        """获取元数据总数"""
        return len(self.metadata)

    def clear_store(self):
        """清空向量存储"""
        try:
            # 重新创建索引
            self.index = faiss.IndexIDMap(faiss.IndexFlatIP(self.dimension))
            self.metadata = []
            self.id_mapping = {}
            self.reverse_id_mapping = {}

            # 删除文件
            for file_path in [self.index_file, self.metadata_file]:
                if os.path.exists(file_path):
                    try:
                        os.remove(file_path)
                    except Exception as e:
                        print(f"删除文件时出错 {file_path}: {str(e)}")

            print("Faiss向量库已清空")
        except Exception as e:
            print(f"清空向量存储时出错: {str(e)}")

    def get_stats(self) -> Dict[str, Any]:
        """获取存储统计信息"""
        return {
            "vector_count": self.get_vector_count(),
            "metadata_count": self.get_metadata_count(),
            "dimension": self.dimension,
            "storage_path": self.storage_path
        }


def store_vectors_with_faiss(texts: List[str], vectors: List[np.ndarray], source: str = "web_scraping"):
    """
    使用Faiss存储向量的主要接口函数
    :param texts: 文本列表
    :param vectors: 向量列表
    :param source: 数据来源
    """
    # 确定向量维度
    if len(vectors) > 0:
        dimension = len(vectors[0])
    else:
        dimension = 128  # 默认维度

    store = FaissVectorStore(dimension=dimension)
    store.add_vectors(texts, vectors, source)
    return store


def load_faiss_store(dimension: int = 128) -> FaissVectorStore:
    """
    加载已存在的Faiss存储
    :param dimension: 向量维度
    :return: FaissVectorStore实例
    """
    return FaissVectorStore(dimension=dimension)





















