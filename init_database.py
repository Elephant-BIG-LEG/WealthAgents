import mysql.connector
from mysql.connector import Error
import os
import sys

# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# 导入配置
from app.config.config import DB_CONFIG

def init_database():
    """
    初始化数据库结构，执行database_schema.sql脚本
    """
    # 先不指定数据库名称，只连接MySQL服务器
    conn = None
    try:
        # 使用连接配置连接到MySQL服务器
        conn = mysql.connector.connect(
            host=DB_CONFIG['host'],
            user=DB_CONFIG['user'],
            password=DB_CONFIG['password'],
            port=DB_CONFIG['port'],
            auth_plugin='mysql_native_password'
        )
        
        if conn.is_connected():
            print("成功连接到MySQL服务器")
            
            # 创建游标
            cursor = conn.cursor()
            
            # 读取SQL脚本文件
            schema_file = 'database_schema.sql'
            if not os.path.exists(schema_file):
                print(f"错误：找不到SQL脚本文件 {schema_file}")
                return False
            
            # 读取整个SQL文件
            with open(schema_file, 'r', encoding='utf-8') as f:
                sql_script = f.read()
            
            # 执行SQL脚本
            print("开始执行SQL脚本...")
            
            # 分割SQL语句（通常以分号分隔）
            sql_statements = sql_script.split(';')
            
            # 过滤掉空语句和注释
            valid_statements = []
            for statement in sql_statements:
                statement = statement.strip()
                if statement and not statement.startswith('--'):
                    valid_statements.append(statement)
            
            # 标记是否创建了数据库和表
            db_and_table_created = False
            
            # 先执行创建数据库和表的语句，跳过索引创建
            for i, statement in enumerate(valid_statements):
                # 跳过索引创建语句，先确保数据库和表创建成功
                if 'CREATE INDEX' in statement or 'ADD FULLTEXT INDEX' in statement:
                    print(f"跳过索引创建语句: {statement[:30]}...")
                    continue
                
                try:
                    cursor.execute(statement)
                    print(f"成功执行: {statement[:50]}...")
                    if 'CREATE TABLE' in statement:
                        db_and_table_created = True
                except Error as e:
                    print(f"执行SQL语句失败: {e}")
                    print(f"SQL: {statement}")
                    # 如果是创建数据库失败，可能是已经存在，继续执行其他语句
                    if 'CREATE DATABASE' in statement and 'already exists' in str(e):
                        print("数据库可能已存在，继续执行...")
                        continue
                    # 如果不是索引创建语句失败，返回False
                    if not ('CREATE INDEX' in statement or 'ADD FULLTEXT INDEX' in statement):
                        return False
            
            # 如果数据库和表创建成功，尝试创建索引（失败也可以接受）
            if db_and_table_created:
                for statement in valid_statements:
                    if 'CREATE INDEX' in statement or 'ADD FULLTEXT INDEX' in statement:
                        try:
                            cursor.execute(statement)
                            print(f"成功创建索引: {statement[:30]}...")
                        except Error as e:
                            print(f"创建索引失败（将继续执行）: {e}")
                            print(f"索引SQL: {statement}")
                            # 索引创建失败不影响整体初始化
                            continue
            
            print("数据库初始化完成！")
            return True
    
    except Error as e:
        print(f"连接MySQL服务器失败: {e}")
        return False
    
    finally:
        if conn and conn.is_connected():
            conn.close()
            print("MySQL连接已关闭")

if __name__ == "__main__":
    print("=== 数据库初始化工具 ===")
    print("本工具将执行database_schema.sql创建数据库和表结构")
    print("请确保MySQL服务器正在运行，并且用户有权限创建数据库和表")
    
    success = init_database()
    if success:
        print("\n✅ 数据库初始化成功！")
        print("您现在可以运行应用程序了。")
    else:
        print("\n❌ 数据库初始化失败！")
        print("请检查错误信息并修复问题后重试。")