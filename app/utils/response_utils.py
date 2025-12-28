"""
响应工具模块
提供统一的API响应格式化功能
"""
import json
from flask import jsonify
from datetime import datetime
from typing import Dict, Any, Optional


def success_response(message: str = "操作成功", data: Any = None, status_code: int = 200) -> tuple:
    """
    生成成功响应

    Args:
        message: 响应消息
        data: 响应数据
        status_code: HTTP状态码

    Returns:
        tuple: (响应数据, 状态码)
    """
    response = {
        "code": 200,
        "message": message,
        "data": data if data is not None else {},
        "timestamp": datetime.now().isoformat()
    }
    return jsonify(response), status_code


def error_response(message: str = "操作失败", data: Any = None, status_code: int = 400) -> tuple:
    """
    生成错误响应

    Args:
        message: 错误消息
        data: 响应数据
        status_code: HTTP状态码

    Returns:
        tuple: (响应数据, 状态码)
    """
    response = {
        "code": status_code,
        "message": message,
        "data": data if data is not None else {},
        "timestamp": datetime.now().isoformat()
    }
    return jsonify(response), status_code


def format_api_response(success: bool, message: str, data: Any = None,
                        status_code: int = 200) -> tuple:
    """
    格式化API响应

    Args:
        success: 是否成功
        message: 消息
        data: 响应数据
        status_code: HTTP状态码

    Returns:
        tuple: (响应数据, 状态码)
    """
    response = {
        "success": success,
        "message": message,
        "data": data if data is not None else {},
        "timestamp": datetime.now().isoformat()
    }

    if success:
        status_code = 200
    else:
        status_code = status_code if status_code != 200 else 400

    return jsonify(response), status_code


def validate_required_fields(data: Dict[str, Any], required_fields: list) -> tuple:
    """
    验证必需字段

    Args:
        data: 待验证的数据
        required_fields: 必需字段列表

    Returns:
        tuple: (是否通过验证, 错误消息)
    """
    missing_fields = []
    for field in required_fields:
        if field not in data or data[field] is None or data[field] == "":
            missing_fields.append(field)

    if missing_fields:
        return False, f"缺少必需字段: {', '.join(missing_fields)}"

    return True, ""
