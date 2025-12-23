"""
财富Agent - 智能投研分析平台
私人Agent模块 - 数据库工具
"""
from typing import Dict, Any, List
from ...store.database_service import DatabaseConnection, get_database_connection
import logging


class DatabaseTool:
    """数据库工具类"""

    def __init__(self):
        self.logger = logging.getLogger(__name__)
        try:
            self.db_connection = get_database_connection()
        except Exception as e:
            self.logger.error(f"初始化数据库连接失败: {e}")
            self.db_connection = None

    def query_financial_data(self, query_params: Dict[str, Any]) -> Dict[str, Any]:
        """
        查询金融数据

        Args:
            query_params: 查询参数

        Returns:
            查询结果
        """
        try:
            if self.db_connection is None:
                return {
                    "status": "error",
                    "error_message": "数据库连接未正确初始化",
                    "timestamp": __import__('time').time()
                }

            # 获取数据库连接
            connection = self.db_connection.get_connection()
            if not connection:
                return {
                    "status": "error",
                    "error_message": "无法获取数据库连接",
                    "timestamp": __import__('time').time()
                }

            # 根据查询参数执行数据库查询
            table_name = query_params.get('table', 'financial_data')
            conditions = query_params.get('conditions', {})

            # 构建查询语句
            cursor = connection.cursor(dictionary=True)

            if conditions:
                # 如果有条件，构建WHERE子句
                where_clause = " AND ".join(
                    [f"{key} = %s" for key in conditions.keys()])
                query = f"SELECT * FROM {table_name} WHERE {where_clause}"
                values = list(conditions.values())
                cursor.execute(query, values)
            else:
                # 没有条件，查询所有数据
                query = f"SELECT * FROM {table_name}"
                cursor.execute(query)

            result = cursor.fetchall()
            cursor.close()

            return {
                "status": "success",
                "data": result,
                "record_count": len(result) if result else 0,
                "query_params": query_params,
                "timestamp": __import__('time').time()
            }

        except Exception as e:
            self.logger.error(f"数据库查询失败: {str(e)}")
            return {
                "status": "error",
                "error_message": str(e),
                "timestamp": __import__('time').time()
            }

    def save_analysis_result(self, analysis_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        保存分析结果到数据库

        Args:
            analysis_data: 分析结果数据

        Returns:
            保存结果
        """
        try:
            if self.db_connection is None:
                return {
                    "status": "error",
                    "error_message": "数据库连接未正确初始化",
                    "timestamp": __import__('time').time()
                }

            # 获取数据库连接
            connection = self.db_connection.get_connection()
            if not connection:
                return {
                    "status": "error",
                    "error_message": "无法获取数据库连接",
                    "timestamp": __import__('time').time()
                }

            # 保存分析结果
            table_name = analysis_data.get('table', 'analysis_results')
            data = analysis_data.get('data', {})

            if not data:
                return {
                    "status": "error",
                    "error_message": "没有要保存的数据",
                    "timestamp": __import__('time').time()
                }

            # 构建插入语句
            cursor = connection.cursor()

            columns = ', '.join(data.keys())
            placeholders = ', '.join(['%s'] * len(data))
            query = f"INSERT INTO {table_name} ({columns}) VALUES ({placeholders})"

            cursor.execute(query, list(data.values()))
            connection.commit()

            inserted_id = cursor.lastrowid
            cursor.close()

            return {
                "status": "success",
                "inserted_id": inserted_id,
                "data_saved": data,
                "timestamp": __import__('time').time()
            }

        except Exception as e:
            self.logger.error(f"保存分析结果失败: {str(e)}")
            return {
                "status": "error",
                "error_message": str(e),
                "timestamp": __import__('time').time()
            }


# 便捷函数，供Executor调用
def database_tool(operation: str, data: Dict[str, Any], **kwargs) -> Dict[str, Any]:
    """
    数据库工具便捷函数

    Args:
        operation: 操作类型 ('query' 或 'save')
        data: 操作数据
        **kwargs: 其他参数

    Returns:
        操作结果
    """
    tool = DatabaseTool()

    if operation == 'query':
        return tool.query_financial_data(data)
    elif operation == 'save':
        return tool.save_analysis_result(data)
    else:
        return {
            "status": "error",
            "error_message": f"不支持的操作类型: {operation}",
            "timestamp": __import__('time').time()
        }
