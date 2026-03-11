import json
import os
from typing import List, Dict, Any, Optional
from datetime import datetime
import logging
import mysql.connector
from mysql.connector import Error

from app.store.database_service import get_database_connection
from app.config.config import DB_CONFIG

logger = logging.getLogger(__name__)

class CompanyService:
    """公司信息管理服务类"""
    
    def __init__(self):
        self.db_connection = get_database_connection()
        self.knowledge_base_path = "company_knowledge_base"
    
    def _execute_query(self, query: str, params: tuple = None, fetch_all: bool = False) -> Any:
        """
        执行SQL查询
        
        参数：
        - query: SQL查询语句
        - params: 查询参数
        - fetch_all: 是否获取所有结果
        
        返回：
        - 查询结果
        """
        connection = self.db_connection.get_connection()
        if not connection:
            return None
        
        try:
            cursor = connection.cursor(dictionary=True)
            cursor.execute(query, params)
            
            if query.strip().upper().startswith('SELECT'):
                if fetch_all:
                    result = cursor.fetchall()
                    return result
                else:
                    result = cursor.fetchone()
                    return result
            else:
                connection.commit()
                return cursor.lastrowid
        except Error as e:
            logger.error(f"执行SQL查询失败: {str(e)}")
            logger.error(f"查询语句: {query}")
            logger.error(f"参数: {params}")
            # 发生错误时回滚事务
            connection.rollback()
            return None
        finally:
            if 'cursor' in locals():
                cursor.close()
            # 每次执行后关闭连接，确保事务正确提交
            if connection.is_connected():
                connection.close()
                self.db_connection.connection = None
    
    def add_company(self, company_name: str, **kwargs) -> Optional[int]:
        """
        增加公司信息
        
        参数：
        - company_name: 公司名称
        - kwargs: 其他公司信息字段（english_name, stock_code, industry, founded_year, headquarters, website等）
        
        返回：
        - 公司ID，如果失败返回None
        """
        logger.info(f"尝试添加公司: {company_name}, 其他参数: {kwargs}")
        # 生成知识库路径，使用公司ID作为目录名而不是中文名称，避免编码问题
        # 先执行SQL插入获取公司ID
        # 注意：knowledge_base_path字段需要一个初始值，因为它没有默认值
        columns = ['company_name', 'knowledge_base_path']
        values = [company_name, '']
        
        # 添加可选字段
        optional_fields = ['english_name', 'stock_code', 'industry', 'founded_year', 'headquarters', 'website']
        for field in optional_fields:
            if field in kwargs:
                columns.append(field)
                values.append(kwargs[field])
                logger.info(f"添加可选字段: {field} = {kwargs[field]}")
        
        logger.info(f"准备插入数据库: columns={columns}, values={values}")
        # 先插入基本信息（包含临时的knowledge_base_path）
        columns_str = ', '.join(columns)
        placeholders = ', '.join(['%s'] * len(values))
        query = f"INSERT INTO Company ({columns_str}) VALUES ({placeholders})"
        
        # 执行查询获取公司ID
        company_id = self._execute_query(query, tuple(values))
        
        if not company_id:
            logger.error(f"添加公司 {company_name} 失败，无法获取公司ID")
            return None
        
        # 使用公司ID作为知识库目录名，避免中文编码问题
        knowledge_base_path = os.path.join(self.knowledge_base_path, f"company_{company_id}")
        
        # 确保知识库目录存在
        if not os.path.exists(knowledge_base_path):
            try:
                os.makedirs(knowledge_base_path)
                logger.info(f"已创建公司知识库目录: {knowledge_base_path}")
            except Exception as e:
                logger.error(f"创建知识库目录失败: {str(e)}")
                return None
        
        # 更新公司信息，设置知识库路径
        update_query = "UPDATE Company SET knowledge_base_path = %s WHERE id = %s"
        update_result = self._execute_query(update_query, (knowledge_base_path, company_id))
        
        if update_result is not None:
            logger.info(f"公司 {company_name} 已添加，ID: {company_id}")
            return company_id
        else:
            logger.error(f"更新公司知识库路径失败")
            return None
    
    def delete_company(self, company_id: int = None, company_name: str = None) -> bool:
        """
        删除公司信息
        
        参数：
        - company_id: 公司ID（可选）
        - company_name: 公司名称（可选）
        
        返回：
        - 是否删除成功
        """
        if not company_id and not company_name:
            logger.error("删除公司时必须提供company_id或company_name")
            return False
        
        # 获取公司信息以删除知识库目录
        company_info = self.get_company(company_id, company_name)
        if not company_info:
            logger.warning("要删除的公司不存在")
            return False
        
        # 构建WHERE子句
        if company_id:
            where_clause = f"id = {company_id}"
        else:
            where_clause = f"company_name = '{company_name}'"
        
        # 执行删除查询
        query = f"DELETE FROM Company WHERE {where_clause}"
        result = self._execute_query(query)
        
        if result is not None:
            # 删除知识库目录
            import shutil
            if os.path.exists(company_info['knowledge_base_path']):
                try:
                    shutil.rmtree(company_info['knowledge_base_path'])
                    logger.info(f"已删除公司 {company_info['company_name']} 的知识库目录")
                except Exception as e:
                    logger.error(f"删除公司知识库目录时出错: {str(e)}")
            
            logger.info(f"公司 {company_info['company_name']} 已删除")
            return True
        
        return False
    
    def update_company(self, company_id: int = None, company_name: str = None, **kwargs) -> bool:
        """
        更新公司信息
        
        参数：
        - company_id: 公司ID（可选）
        - company_name: 公司名称（可选）
        - kwargs: 要更新的字段
        
        返回：
        - 是否更新成功
        """
        if not company_id and not company_name:
            logger.error("更新公司时必须提供company_id或company_name")
            return False
        
        if not kwargs:
            logger.warning("没有要更新的字段")
            return True
        
        # 构建SET子句
        set_clauses = []
        values = []
        for key, value in kwargs.items():
            set_clauses.append(f"{key} = %s")
            values.append(value)
        
        set_clause_str = ', '.join(set_clauses)
        
        # 构建WHERE子句
        if company_id:
            where_clause = f"id = {company_id}"
        else:
            where_clause = f"company_name = '{company_name}'"
        
        # 执行更新查询
        query = f"UPDATE Company SET {set_clause_str} WHERE {where_clause}"
        result = self._execute_query(query, tuple(values))
        
        if result is not None:
            logger.info(f"公司信息已更新")
            return True
        
        return False
    
    def get_company(self, company_id: int = None, company_name: str = None) -> Optional[Dict[str, Any]]:
        """
        查询公司信息
        
        参数：
        - company_id: 公司ID（可选）
        - company_name: 公司名称（可选）
        
        返回：
        - 公司信息字典，如果不存在返回None
        """
        if not company_id and not company_name:
            logger.error("查询公司时必须提供company_id或company_name")
            return None
        
        # 构建WHERE子句
        if company_id:
            where_clause = f"id = {company_id}"
        else:
            where_clause = f"company_name = '{company_name}'"
        
        # 执行查询
        query = f"SELECT * FROM Company WHERE {where_clause}"
        return self._execute_query(query, fetch_all=False)
    
    def list_companies(self, **filters) -> List[Dict[str, Any]]:
        """
        列出所有公司
        
        参数：
        - filters: 过滤条件（industry, stock_code等）
        
        返回：
        - 公司列表
        """
        # 构建WHERE子句
        where_clauses = []
        values = []
        for key, value in filters.items():
            where_clauses.append(f"{key} = %s")
            values.append(value)
        
        where_clause_str = 'WHERE ' + ' AND '.join(where_clauses) if where_clauses else ''
        
        # 执行查询
        query = f"SELECT * FROM Company {where_clause_str} ORDER BY company_name"
        return self._execute_query(query, tuple(values), fetch_all=True) or []
    
    def get_all_companies(self) -> List[Dict[str, Any]]:
        """
        获取所有公司列表（无过滤条件）
        
        返回：
        - 公司列表
        """
        return self.list_companies()
    
    def add_company_version(self, company_id: int, document_count: int, chunk_count: int, version_note: str = None) -> Optional[int]:
        """
        添加公司知识库版本
        
        参数：
        - company_id: 公司ID
        - document_count: 文档数量
        - chunk_count: 文本块数量
        - version_note: 版本说明
        
        返回：
        - 版本ID，如果失败返回None
        """
        query = "INSERT INTO CompanyVersion (company_id, document_count, chunk_count, version_note) VALUES (%s, %s, %s, %s)"
        return self._execute_query(query, (company_id, document_count, chunk_count, version_note))
    
    def update_company_statistics(self, company_id: int, document_count: int, chunk_count: int) -> bool:
        """
        更新公司统计信息
        
        参数：
        - company_id: 公司ID
        - document_count: 文档数量
        - chunk_count: 文本块数量
        
        返回：
        - 是否更新成功
        """
        # 更新公司表中的统计信息
        query = "UPDATE Company SET document_count = %s, chunk_count = %s WHERE id = %s"
        result = self._execute_query(query, (document_count, chunk_count, company_id))
        
        if result is not None:
            # 添加版本记录
            self.add_company_version(company_id, document_count, chunk_count)
            return True
        
        return False
    
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
            if self.get_company(company_name=company_name):
                logger.warning(f"公司 {company_name} 已存在于数据库中，跳过")
                continue
            
            # 添加公司信息
            company_id = self.add_company(
                company_name=company_name,
                knowledge_base_path=company_info['knowledge_base_path']
            )
            
            if company_id:
                # 更新公司统计信息
                self.update_company_statistics(
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

# 创建全局实例供外部使用
company_service = CompanyService()





