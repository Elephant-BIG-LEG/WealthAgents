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

    def __init__(self, dimension: int = 128, storage_path: str = "faiss_database"):
        """
        初始化Faiss向量存储
        :param dimension: 向量维度
        :param storage_path: 存储路径
        """
        self.dimension = dimension
        # 清理路径中的多余空格和规范化处理
        clean_storage_path = self._clean_path(storage_path)
        # 使用绝对路径和系统标准化路径处理
        self.storage_path = os.path.abspath(os.path.normpath(clean_storage_path))
        
        # 确保使用系统正确的路径分隔符
        self.index_file = os.path.join(self.storage_path, "faiss_index.bin")
        self.metadata_file = os.path.join(self.storage_path, "metadata.json")

        # 创建存储目录（包括所有父目录）- 增强的目录创建逻辑
        self._ensure_directory_exists()
        
        # 初始化Faiss索引
        self.index = self._load_or_create_index()

        # 初始化元数据
        self.metadata = self._load_metadata()

        # ID映射（Faiss内部ID到自定义ID）
        self.id_mapping = {}  # {faiss_id: custom_id}
        self.reverse_id_mapping = {}  # {custom_id: faiss_id}

        # 如果索引中有数据，重建ID映射
        if hasattr(self.index, 'ntotal') and self.index.ntotal > 0:
            self._rebuild_id_mapping()

    def _clean_path(self, path: str) -> str:
        """
        清理路径中的多余空格和特殊字符
        :param path: 原始路径
        :return: 清理后的路径
        """
        # 移除路径组件之间的多余空格
        path_parts = path.split(os.sep)
        clean_parts = [part.strip() for part in path_parts]
        # 过滤掉空的路径组件
        clean_parts = [part for part in clean_parts if part]
        # 重新组合路径
        return os.sep.join(clean_parts)

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

    def _load_or_create_index(self):
        """加载或创建Faiss索引"""
        try:
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
        except Exception as e:
            print(f"加载或创建索引时出错: {str(e)}")
            # 返回备用索引
            return faiss.IndexIDMap(faiss.IndexFlatIP(self.dimension))

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
        保存Faiss索引 - 增强版本，确保路径正确处理
        """
        try:
            # 再次确认目录存在
            self._ensure_directory_exists()
            
            # 修复路径中的空格问题
            safe_index_file = self.index_file.replace(' ', '_')
            print(f"\n使用修复后的路径写入索引: {safe_index_file}")
            
            # 特殊处理：先创建一个空文件，验证路径可写
            with open(safe_index_file, 'wb') as f:
                f.write(b'')
            
            # Windows路径特殊处理
            if platform.system() == 'Windows':
                # 对于Windows，使用try/except模式尝试不同的路径处理
                try:
                    # 方法1：直接使用修复后的路径
                    faiss.write_index(self.index, safe_index_file)
                    print(f"成功保存Faiss索引到修复路径: {safe_index_file}")
                    # 如果成功，确保我们的原始索引文件路径指向正确的文件
                    self.index_file = safe_index_file
                except Exception as e1:
                    print(f"方法1失败，尝试方法2: {str(e1)}")
                    # 方法2：使用临时文件然后复制
                    temp_path = os.path.join(os.getcwd(), "temp_faiss_index.bin")
                    faiss.write_index(self.index, temp_path)
                    # 复制文件到目标位置
                    import shutil
                    shutil.copy2(temp_path, safe_index_file)
                    os.remove(temp_path)  # 删除临时文件
                    self.index_file = safe_index_file
                    print(f"成功通过临时文件方法保存索引到: {safe_index_file}")
            else:
                # Linux/Mac使用标准方法
                faiss.write_index(self.index, safe_index_file)
                self.index_file = safe_index_file
                
            print(f"成功保存Faiss索引到: {self.index_file}")
        except Exception as e:
            print(f"保存索引时出错: {str(e)}")
            # 尝试保存到当前目录作为备份
            backup_path = os.path.join(os.getcwd(), "faiss_index_backup.bin")
            try:
                faiss.write_index(self.index, backup_path)
                print(f"已保存索引到备份路径: {backup_path}")
            except:
                print("备份索引也失败")

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

