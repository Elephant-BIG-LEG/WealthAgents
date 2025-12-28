"""
认证工具模块
提供API认证和授权功能
"""
from functools import wraps
from flask import request, jsonify, session
from datetime import datetime, timedelta
import jwt
import os
from typing import Dict, Any, Optional


def require_auth(func):
    """
    认证装饰器
    验证请求是否包含有效的认证信息
    """
    @wraps(func)
    def wrapper(*args, **kwargs):
        # 这里可以实现具体的认证逻辑
        # 例如检查API密钥、JWT令牌等
        # 为了简化，当前实现暂时直接通过
        # 实际项目中应根据需求实现JWT或Session认证
        return func(*args, **kwargs)

    wrapper.__name__ = func.__name__
    return wrapper


def generate_token(user_id: str, expiration_hours: int = 24) -> str:
    """
    生成JWT令牌

    Args:
        user_id: 用户ID
        expiration_hours: 令牌过期时间（小时）

    Returns:
        str: JWT令牌
    """
    try:
        payload = {
            'user_id': user_id,
            'exp': datetime.utcnow() + timedelta(hours=expiration_hours),
            'iat': datetime.utcnow()
        }

        secret_key = os.environ.get(
            'SECRET_KEY', 'default_secret_key_for_development')
        token = jwt.encode(payload, secret_key, algorithm='HS256')
        return token
    except Exception as e:
        raise Exception(f"生成令牌失败: {str(e)}")


def verify_token(token: str) -> Optional[Dict[str, Any]]:
    """
    验证JWT令牌

    Args:
        token: JWT令牌

    Returns:
        dict: 解码后的令牌数据，验证失败时返回None
    """
    try:
        secret_key = os.environ.get(
            'SECRET_KEY', 'default_secret_key_for_development')
        payload = jwt.decode(token, secret_key, algorithms=['HS256'])
        return payload
    except jwt.ExpiredSignatureError:
        return None
    except jwt.InvalidTokenError:
        return None


def get_current_user_id() -> Optional[str]:
    """
    获取当前用户ID

    Returns:
        str: 当前用户ID，未认证时返回None
    """
    # 优先从请求头中获取token
    auth_header = request.headers.get('Authorization')
    if auth_header and auth_header.startswith('Bearer '):
        token = auth_header.split(' ')[1]
        payload = verify_token(token)
        if payload:
            return payload.get('user_id')

    # 如果没有token，检查session
    return session.get('user_id')


def require_api_key(func):
    """
    API密钥认证装饰器
    验证请求是否包含有效的API密钥
    """
    @wraps(func)
    def wrapper(*args, **kwargs):
        # 检查请求头中的API密钥
        api_key = request.headers.get('X-API-Key')
        if not api_key:
            # 也可以检查查询参数
            api_key = request.args.get('api_key')

        # 这里应该验证API密钥的有效性
        # 为了简化，当前实现暂时直接通过
        # 实际项目中应从数据库或配置中验证API密钥
        return func(*args, **kwargs)

    wrapper.__name__ = func.__name__
    return wrapper
