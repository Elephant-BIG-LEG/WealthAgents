"""
财富Agent - 智能投研分析平台
私人Agent模块 - 记忆管理组件
负责管理短期记忆和上下文保持
"""
from typing import Dict, Any, Optional, List
import time
import redis
import pickle
import os
import logging

# 配置日志
logger = logging.getLogger(__name__)



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
                redis_password = os.getenv('REDIS_PASSWORD', None)  # 从环境变量获取Redis密码

                self.redis_client = redis.Redis(
                    host=redis_host,
                    port=redis_port,
                    db=redis_db,
                    password=redis_password,  # 添加密码参数
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

    def get_context(self, user_id: str, user_query: str) -> List[Dict[str, Any]]:
        """
        获取与用户查询相关的上下文历史，使用Redis ZSet按时间排序获取最新10条

        Args:
            user_id: 用户ID（直接使用，不是生成的）
            user_query: 用户查询

        Returns:
            上下文历史列表，每项包含查询和响应
        """
        # 初始化结果列表
        context_history = []
        
        # 使用用户ID作为ZSet的key，确保每个用户的交互记录是独立的
        # 添加"chats"作为盐值，避免key冲突
        user_zset_key = f"interactions:{user_id}:chats"
        
        if self.use_redis:
            try:
                # 从Redis ZSet中获取按时间排序的最新10条交互记录
                # 使用zrevrange按score（时间戳）降序获取最新的记录
                # withscores=True 同时获取成员和对应的分数（时间戳）
                interactions = self.redis_client.zrevrange(user_zset_key, 0, 9, withscores=True)
                
                # 处理结果
                for member, score in interactions:
                    # 从member中获取实际内容的key
                    value = self.redis_client.get(member)
                    if value:
                        interaction = pickle.loads(value)
                        context_history.append(interaction)
            except Exception as e:
                logger.warning(f"从Redis获取上下文失败: {e}")
        else:
            # 从内存存储获取交互记录
            interaction_records = []
            for key, entry in self.memory_store.items():
                # 检查key是否可能属于当前用户
                # 用户ID前8位作为前缀
                user_id_part = user_id[:8]
                if key.startswith(user_id_part) and len(key) == 16:
                    try:
                        interaction = pickle.loads(entry['value'])
                        # 确认是当前用户的记录且未过期
                        if interaction.get('user_id') == user_id and time.time() < entry['expires_at']:
                            interaction_records.append(interaction)
                    except:
                        continue
            
            # 按时间排序，获取最近的10条记录
            context_history = sorted(interaction_records, 
                                   key=lambda x: x.get('timestamp', 0), 
                                   reverse=True)[:10]
        
        return context_history
        
    def save_interaction(self, user_id: str, query: str, response: Any):
        """
        保存用户交互历史到Redis ZSet，用于get_context方法获取排序后的记录

        Args:
            user_id: 用户ID（直接使用，不是生成的）
            query: 用户查询
            response: 系统响应
        """
        # 生成16位key，前几位用实际用户ID的一部分，后几位用时间戳的一部分
        timestamp = time.time()
        
        # 确保用户ID前8位（如果不足8位则全部使用）
        user_id_part = user_id[:8]
        
        # 生成时间戳的一部分（取后8位，确保总共16位）
        ts_part = str(int(timestamp * 1000))[-8:]
        
        # 合并生成16位key
        key = f"{user_id_part}{ts_part}"
        
        # 创建交互记录
        interaction = {
            'user_id': user_id,  # 保存完整的原始用户ID
            'query': query,
            'response': response,
            'timestamp': timestamp
        }
        
        # 序列化交互记录
        value = pickle.dumps(interaction)
        
        # 设置过期时间为7天
        expiry_time = 7 * 24 * 3600  # 7天 = 604800秒
        
        if self.use_redis:
            try:
                # 在Redis中保存交互记录，设置过期时间
                self.redis_client.setex(key, expiry_time, value)
                
                # 使用用户ID作为ZSet的key，确保每个用户的交互记录是独立的
                # 添加"chats"作为盐值，避免key冲突
                user_zset_key = f"interactions:{user_id}:chats"
                
                # 将交互记录的key以时间戳为score添加到ZSet中
                self.redis_client.zadd(user_zset_key, {key: timestamp})
                
                # 只保留ZSet中最近的10条记录，避免数据过大
                count = self.redis_client.zcard(user_zset_key)
                if count > 10:
                    # 删除最早的(count-10)条记录
                    oldest_keys = self.redis_client.zrange(user_zset_key, 0, count-11)
                    if oldest_keys:
                        # 先从ZSet中删除
                        self.redis_client.zrem(user_zset_key, *oldest_keys)
                        # 再删除对应的实际内容
                        self.redis_client.delete(*oldest_keys)
                
                # 为ZSet设置过期时间
                self.redis_client.expire(user_zset_key, expiry_time)
            except Exception as e:
                logger.warning(f"保存交互到Redis失败: {e}")
        else:
            # 在内存中保存，记录过期时间
            self.memory_store[key] = {
                'value': value,
                'expires_at': time.time() + expiry_time
            }

    def save_conversation_history(self, user_id: str, message: Dict[str, Any]):
        """
        使用Redis list存储对话内容，zset存储时间戳用于排序，保留最近10条

        Args:
            user_id: 用户ID
            message: 消息内容，包含role、content、timestamp等字段
        """
        content_key = f"conversation_content:{user_id}"
        time_key = f"conversation_time:{user_id}"
        message_id = str(int(time.time() * 1000))  # 使用时间戳作为消息ID
        message['message_id'] = message_id
        
        if self.use_redis:
            try:
                # 保存对话内容到List
                self.redis_client.rpush(content_key, pickle.dumps(message))
                
                # 保存时间戳到zset (score为时间戳，value为消息ID)
                timestamp = float(message.get('timestamp', time.time()))
                self.redis_client.zadd(time_key, {message_id: timestamp})
                
                # 保留最近10条记录
                self.redis_client.ltrim(content_key, -10, -1)
                
                # 只保留zset中最近的10个元素
                count = self.redis_client.zcard(time_key)
                if count > 10:
                    # 获取最早的(10-count)个元素并删除
                    oldest_ids = self.redis_client.zrange(time_key, 0, count - 11)
                    if oldest_ids:
                        self.redis_client.zrem(time_key, *oldest_ids)
                
                # 设置过期时间为7天
                self.redis_client.expire(content_key, 7 * 86400)
                self.redis_client.expire(time_key, 7 * 86400)
            except Exception as e:
                logger.warning(f"保存对话历史到Redis失败: {e}")
        else:
            # 如果Redis不可用，使用内存存储作为备选
            history_key = f"user_history:{user_id}"
            if history_key not in self.memory_store:
                self.memory_store[history_key] = {
                    'messages': [],
                    'expires_at': time.time() + 7 * 86400
                }
            
            # 添加新消息
            self.memory_store[history_key]['messages'].append(message)
            
            # 按时间戳排序（降序）并只保留最近10条
            self.memory_store[history_key]['messages'].sort(key=lambda x: x.get('timestamp', time.time()), reverse=True)
            if len(self.memory_store[history_key]['messages']) > 10:
                self.memory_store[history_key]['messages'] = self.memory_store[history_key]['messages'][:10]
    
    def get_conversation_history(self, user_id: str) -> List[Dict[str, Any]]:
        """
        获取用户的最近10条对话历史，按时间排序

        Args:
            user_id: 用户ID

        Returns:
            对话历史列表，按时间排序，每条包含role、content、timestamp等字段
        """
        content_key = f"conversation_content:{user_id}"
        time_key = f"conversation_time:{user_id}"
        history = []
        
        if self.use_redis:
            try:
                # 从List获取所有消息
                messages = self.redis_client.lrange(content_key, 0, -1)
                all_messages = {}
                
                for msg_bytes in messages:
                    message = pickle.loads(msg_bytes)
                    all_messages[message.get('message_id')] = message
                
                # 从zset获取排序后的消息ID (按时间升序)
                sorted_ids = self.redis_client.zrange(time_key, 0, -1)
                sorted_ids = [id.decode('utf-8') if isinstance(id, bytes) else id for id in sorted_ids]
                
                # 按排序顺序构建历史记录
                for msg_id in sorted_ids:
                    if msg_id in all_messages:
                        history.append(all_messages[msg_id])
            except Exception as e:
                logger.warning(f"获取对话历史失败: {e}")
        else:
            # 如果Redis不可用，从内存存储获取
            history_key = f"user_history:{user_id}"
            if history_key in self.memory_store:
                entry = self.memory_store[history_key]
                if time.time() < entry['expires_at']:
                    # 按时间戳排序（升序）
                    history = sorted(entry['messages'], key=lambda x: x.get('timestamp', time.time()))
                else:
                    # 清理过期条目
                    del self.memory_store[history_key]
        
        return history
    
    def clear_conversation_history(self, user_id: str):
        """
        清除用户的所有对话历史

        Args:
            user_id: 用户ID
        """
        content_key = f"conversation_content:{user_id}"
        time_key = f"conversation_time:{user_id}"
        
        if self.use_redis:
            try:
                self.redis_client.delete(content_key)
                self.redis_client.delete(time_key)
            except Exception as e:
                logger.warning(f"清除对话历史失败: {e}")
        else:
            # 如果Redis不可用，清除内存存储
            history_key = f"user_history:{user_id}"
            if history_key in self.memory_store:
                del self.memory_store[history_key]