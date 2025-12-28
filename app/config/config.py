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

