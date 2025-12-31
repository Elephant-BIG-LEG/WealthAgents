import mysql.connector
from mysql.connector import Error
from typing import Optional, Dict, Any
from app.config.config import DB_CONFIG


class DatabaseConnection:
    """
    MySQL数据库连接管理类
    提供基本的数据库连接功能
    """

    def __init__(self):
        """
        初始化数据库连接配置，从环境变量读取
        """
        self.host = DB_CONFIG['host']
        self.user = DB_CONFIG['user']
        self.password = DB_CONFIG['password']
        self.database = DB_CONFIG['database']
        self.port = DB_CONFIG['port']
        self.connection = None

    def connect(self) -> Optional[mysql.connector.connection.MySQLConnection]:
        """
        建立数据库连接

        Returns:
            数据库连接对象，如果连接失败返回None
        """
        try:
            self.connection = mysql.connector.connect(
                host=self.host,
                user=self.user,
                password=self.password,
                database=self.database,
                port=self.port,
                auth_plugin='mysql_native_password',
                charset=DB_CONFIG['charset']
            )

            if self.connection.is_connected():
                print(f"成功连接到数据库 {self.database}")
                return self.connection

        except Error as e:
            print(f"数据库连接失败: {e}")
            self.connection = None
            return None

    def disconnect(self) -> None:
        """
        关闭数据库连接
        """
        if self.connection and self.connection.is_connected():
            self.connection.close()
            print("数据库连接已关闭")

    def get_connection(self) -> Optional[mysql.connector.connection.MySQLConnection]:
        """
        获取当前数据库连接，如果连接不存在或已断开，则尝试重新连接

        Returns:
            数据库连接对象
        """
        if not self.connection or not self.connection.is_connected():
            return self.connect()
        return self.connection

    def is_connected(self) -> bool:
        """
        检查是否已连接到数据库

        Returns:
            是否已连接
        """
        return self.connection is not None and self.connection.is_connected()


# 单例模式管理数据库连接
_db_connection_instance = None


def get_database_connection() -> DatabaseConnection:
    """
    获取数据库连接实例

    Returns:
        DatabaseConnection实例
    """
    global _db_connection_instance
    if _db_connection_instance is None:
        _db_connection_instance = DatabaseConnection()
    return _db_connection_instance


def get_database_service() -> DatabaseConnection:
    """
    为了兼容性，提供与现有代码匹配的函数名

    Returns:
        DatabaseConnection实例
    """
    return get_database_connection()
