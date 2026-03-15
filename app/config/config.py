import dotenv
import os

# 加载环境变量
dotenv.load_dotenv()

# DashScope API配置
DASHSCOPE_API_KEY = os.getenv("DASHSCOPE_API_KEY")
DASHSCOPE_BASE_URL = os.getenv("DASHSCOPE_BASE_URL")

# 数据库配置
DB_CONFIG = {
    'host': os.getenv('DB_HOST', 'localhost'),
    'port': int(os.getenv('DB_PORT', '13306')),
    'user': os.getenv('DB_USER', 'root'),
    'password': os.getenv('DB_PASSWORD', 'abc123'),
    'database': os.getenv('DB_NAME', 'FinanceData'),
    'charset': 'utf8mb4'  # 添加charset参数修复连接错误
}

# 其他配置
DEBUG = os.getenv('DEBUG', 'False').lower() == 'true'
SECRET_KEY = os.getenv('SECRET_KEY', 'your-secret-key-here')

# RAG 与向量化配置（Sentence-BERT text2vec-base-chinese 为 768 维）
RAG_EMBEDDING_MODEL = os.getenv("RAG_EMBEDDING_MODEL", "shibing624/text2vec-base-chinese")
RAG_EMBEDDING_DIM = 768
RAG_FAISS_INDEX_PATH = os.getenv("RAG_FAISS_INDEX_PATH", "faiss_index.bin")
RAG_CHUNK_SIZE = int(os.getenv("RAG_CHUNK_SIZE", "600"))
RAG_CHUNK_OVERLAP = int(os.getenv("RAG_CHUNK_OVERLAP", "90"))
RAG_TOP_K = int(os.getenv("RAG_TOP_K", "5"))
RAG_USE_HYBRID = os.getenv("RAG_USE_HYBRID", "true").lower() == "true"
RAG_HYBRID_DENSE_WEIGHT = float(os.getenv("RAG_HYBRID_DENSE_WEIGHT", "0.6"))
RAG_HYBRID_SPARSE_WEIGHT = float(os.getenv("RAG_HYBRID_SPARSE_WEIGHT", "0.4"))

