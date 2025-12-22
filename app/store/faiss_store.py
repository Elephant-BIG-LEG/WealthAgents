import numpy as np
import faiss
import json
import os
from typing import List, Tuple, Dict, Any
from datetime import datetime

"""
TODO
写入向量库
"""

class FaissVectorStore:
    """基于Faiss的向量存储类"""

    def __init__(self, dimension: int = 128, storage_path: str = "faiss_database"):
        """
        初始化Faiss向量存储
        :param dimension: 向量维度
        :param storage_path: 存储路径
        """
        self.dimension = dimension
        self.storage_path = storage_path
        self.index_file = os.path.join(storage_path, "faiss_index.bin")
        self.metadata_file = os.path.join(storage_path, "metadata.json")

        # 创建存储目录
        if not os.path.exists(storage_path):
            os.makedirs(storage_path)

        # 初始化Faiss索引
        self.index = self._load_or_create_index()

        # 初始化元数据
        self.metadata = self._load_metadata()

        # ID映射（Faiss内部ID到自定义ID）
        self.id_mapping = {}  # {faiss_id: custom_id}
        self.reverse_id_mapping = {}  # {custom_id: faiss_id}

        # 如果索引中有数据，重建ID映射
        if self.index.ntotal > 0:
            self._rebuild_id_mapping()

    def _load_or_create_index(self):
        """加载或创建Faiss索引"""
        if os.path.exists(self.index_file):
            # 加载现有索引
            index = faiss.read_index(self.index_file)
            print(f"加载现有Faiss索引，包含 {index.ntotal} 个向量")
            return index
        else:
            # 创建新的索引（使用内积距离，适合余弦相似度）
            index = faiss.IndexIDMap(faiss.IndexFlatIP(self.dimension))
            print("创建新的Faiss索引")
            return index

    def _load_metadata(self) -> List[Dict[str, Any]]:
        """加载元数据"""
        if os.path.exists(self.metadata_file):
            with open(self.metadata_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        return []

    def _save_index(self):
        """保存Faiss索引"""
        faiss.write_index(self.index, self.index_file)

    def _save_metadata(self):
        """保存元数据"""
        with open(self.metadata_file, 'w', encoding='utf-8') as f:
            json.dump(self.metadata, f, ensure_ascii=False, indent=2)

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
        return self.index.ntotal

    def get_metadata_count(self) -> int:
        """获取元数据总数"""
        return len(self.metadata)

    def clear_store(self):
        """清空向量存储"""
        # 重新创建索引
        self.index = faiss.IndexIDMap(faiss.IndexFlatIP(self.dimension))
        self.metadata = []
        self.id_mapping = {}
        self.reverse_id_mapping = {}

        # 删除文件
        for file_path in [self.index_file, self.metadata_file]:
            if os.path.exists(file_path):
                os.remove(file_path)

        print("Faiss向量库已清空")

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
