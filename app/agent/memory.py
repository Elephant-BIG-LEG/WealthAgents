"""
财富Agent - 智能投研分析平台
私人Agent模块 - 记忆管理组件
负责管理短期记忆和上下文保持
"""
from typing import Dict, Any, Optional, List
import json
import time
from datetime import datetime, timedelta
import redis
import pickle
import os



class MemoryManager:
    """记忆管理器 - 负责管理短期记忆和上下文"""

    def __init__(self, use_redis: bool = True):
        """
        初始化记忆管理器

        Args:
            use_redis: 是否使用Redis作为存储后端
        """
        self.use_redis = use_redis
        self.redis_client = None

        if use_redis:
            try:
                # 从环境变量获取Redis连接信息
                redis_host = os.getenv('REDIS_HOST', 'localhost')
                redis_port = int(os.getenv('REDIS_PORT', 6379))
                redis_db = int(os.getenv('REDIS_DB', 0))

                self.redis_client = redis.Redis(
                    host=redis_host,
                    port=redis_port,
                    db=redis_db,
                    decode_responses=False  # 保持二进制模式以支持pickle
                )

                # 测试连接
                self.redis_client.ping()
                print("Redis连接成功")

            except Exception as e:
                print(f"Redis连接失败: {e}，将使用内存存储")
                self.use_redis = False

        # 如果Redis不可用，使用内存存储作为备选
        if not self.use_redis:
            self.memory_store = {}

    def save_task_result(self, task_id: str, result: Dict[str, Any]):
        """
        保存任务执行结果到记忆

        Args:
            task_id: 任务ID
            result: 任务执行结果
        """
        key = f"task_result:{task_id}"
        value = pickle.dumps(result)

        if self.use_redis:
            # 在Redis中保存结果，设置过期时间为24小时
            self.redis_client.setex(key, 86400, value)  # 24小时 = 86400秒
        else:
            # 在内存中保存结果
            self.memory_store[key] = {
                'value': value,
                'expires_at': time.time() + 86400  # 24小时后过期
            }

    def get_task_result(self, task_id: str) -> Optional[Dict[str, Any]]:
        """
        从记忆中获取任务执行结果

        Args:
            task_id: 任务ID

        Returns:
            任务执行结果，如果不存在则返回None
        """
        key = f"task_result:{task_id}"

        if self.use_redis:
            value = self.redis_client.get(key)
            if value is not None:
                return pickle.loads(value)
        else:
            if key in self.memory_store:
                entry = self.memory_store[key]

                # 检查是否过期
                if time.time() < entry['expires_at']:
                    return pickle.loads(entry['value'])
                else:
                    # 清理过期条目
                    del self.memory_store[key]

        return None

    def save_conversation_context(self, session_id: str, context: Dict[str, Any]):
        """
        保存对话上下文

        Args:
            session_id: 会话ID
            context: 对话上下文
        """
        key = f"conversation:{session_id}"
        value = pickle.dumps(context)

        if self.use_redis:
            # 保存对话上下文，设置过期时间为1小时
            self.redis_client.setex(key, 3600, value)  # 1小时 = 3600秒
        else:
            self.memory_store[key] = {
                'value': value,
                'expires_at': time.time() + 3600  # 1小时后过期
            }

    def get_conversation_context(self, session_id: str) -> Optional[Dict[str, Any]]:
        """
        获取对话上下文

        Args:
            session_id: 会话ID

        Returns:
            对话上下文，如果不存在则返回None
        """
        key = f"conversation:{session_id}"

        if self.use_redis:
            value = self.redis_client.get(key)
            if value is not None:
                return pickle.loads(value)
        else:
            if key in self.memory_store:
                entry = self.memory_store[key]

                # 检查是否过期
                if time.time() < entry['expires_at']:
                    return pickle.loads(entry['value'])
                else:
                    # 清理过期条目
                    del self.memory_store[key]

        return None

    def save_user_preferences(self, user_id: str, preferences: Dict[str, Any]):
        """
        保存用户偏好设置

        Args:
            user_id: 用户ID
            preferences: 用户偏好设置
        """
        key = f"user_preferences:{user_id}"
        value = pickle.dumps(preferences)

        if self.use_redis:
            # 保存用户偏好，设置过期时间为7天
            self.redis_client.setex(key, 7 * 86400, value)  # 7天 = 604800秒
        else:
            self.memory_store[key] = {
                'value': value,
                'expires_at': time.time() + 7 * 86400  # 7天后过期
            }

    def get_user_preferences(self, user_id: str) -> Optional[Dict[str, Any]]:
        """
        获取用户偏好设置

        Args:
            user_id: 用户ID

        Returns:
            用户偏好设置，如果不存在则返回None
        """
        key = f"user_preferences:{user_id}"

        if self.use_redis:
            value = self.redis_client.get(key)
            if value is not None:
                return pickle.loads(value)
        else:
            if key in self.memory_store:
                entry = self.memory_store[key]

                # 检查是否过期
                if time.time() < entry['expires_at']:
                    return pickle.loads(entry['value'])
                else:
                    # 清理过期条目
                    del self.memory_store[key]

        return None

    def save_intermediate_result(self, session_id: str, step_name: str, result: Any):
        """
        保存中间结果

        Args:
            session_id: 会话ID
            step_name: 步骤名称
            result: 中间结果
        """
        key = f"intermediate_result:{session_id}:{step_name}"
        value = pickle.dumps(result)

        if self.use_redis:
            # 保存中间结果，设置过期时间为30分钟
            self.redis_client.setex(key, 1800, value)  # 30分钟 = 1800秒
        else:
            self.memory_store[key] = {
                'value': value,
                'expires_at': time.time() + 1800  # 30分钟后过期
            }

    def get_intermediate_result(self, session_id: str, step_name: str) -> Optional[Any]:
        """
        获取中间结果

        Args:
            session_id: 会话ID
            step_name: 步骤名称

        Returns:
            中间结果，如果不存在则返回None
        """
        key = f"intermediate_result:{session_id}:{step_name}"

        if self.use_redis:
            value = self.redis_client.get(key)
            if value is not None:
                return pickle.loads(value)
        else:
            if key in self.memory_store:
                entry = self.memory_store[key]

                # 检查是否过期
                if time.time() < entry['expires_at']:
                    return pickle.loads(entry['value'])
                else:
                    # 清理过期条目
                    del self.memory_store[key]

        return None

    def cleanup_expired_entries(self):
        """
        清理过期的内存条目
        注意：Redis会自动过期，但内存存储需要手动清理
        """
        if not self.use_redis:
            current_time = time.time()
            expired_keys = []

            for key, entry in self.memory_store.items():
                if current_time >= entry['expires_at']:
                    expired_keys.append(key)

            for key in expired_keys:
                del self.memory_store[key]

    def clear_session_memory(self, session_id: str):
        """
        清除特定会话的所有记忆

        Args:
            session_id: 会话ID
        """
        if self.use_redis:
            # 删除与会话相关的所有键
            pattern = f"conversation:{session_id}*"
            keys = self.redis_client.keys(pattern)
            if keys:
                self.redis_client.delete(*keys)

            pattern = f"intermediate_result:{session_id}*"
            keys = self.redis_client.keys(pattern)
            if keys:
                self.redis_client.delete(*keys)
        else:
            # 在内存存储中查找并删除相关键
            keys_to_delete = []
            for key in self.memory_store.keys():
                if key.startswith(f"conversation:{session_id}") or \
                   key.startswith(f"intermediate_result:{session_id}"):
                    keys_to_delete.append(key)

            for key in keys_to_delete:
                del self.memory_store[key]
