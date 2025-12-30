"""
财富Agent - 智能投研分析平台
日志配置模块
提供统一的日志格式和配置选项
"""
import logging
import logging.handlers
import os
from datetime import datetime

# 日志级别映射
LOG_LEVELS = {
    'DEBUG': logging.DEBUG,
    'INFO': logging.INFO,
    'WARNING': logging.WARNING,
    'ERROR': logging.ERROR,
    'CRITICAL': logging.CRITICAL
}

# 统一的日志格式
LOG_FORMAT = '%(asctime)s - %(levelname)s - %(module)s:%(funcName)s:%(lineno)d - [%(session_id)s] - %(message)s'
CONSOLE_FORMAT = '%(asctime)s - %(levelname)s - %(module)s - %(message)s'

# 日志目录
LOG_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), 'logs')


class SessionFilter(logging.Filter):
    """会话过滤器，为日志添加会话ID信息"""
    def __init__(self, session_id=None):
        super().__init__()
        self.session_id = session_id or 'N/A'

    def filter(self, record):
        """为日志记录添加会话ID"""
        if not hasattr(record, 'session_id'):
            record.session_id = self.session_id
        return True


def setup_logger(name=__name__, level='INFO', session_id=None):
    """
    配置并返回日志记录器

    Args:
        name: 日志记录器名称
        level: 日志级别
        session_id: 会话ID，用于跟踪请求

    Returns:
        配置好的日志记录器
    """
    logger = logging.getLogger(name)
    
    # 如果已经配置过，直接返回
    if logger.handlers:
        return logger

    # 设置日志级别
    logger.setLevel(LOG_LEVELS.get(level.upper(), logging.INFO))

    # 确保日志目录存在
    os.makedirs(LOG_DIR, exist_ok=True)

    # 创建格式化器
    formatter = logging.Formatter(LOG_FORMAT)
    console_formatter = logging.Formatter(CONSOLE_FORMAT)

    # 创建文件处理器 - 按天滚动
    log_file = os.path.join(LOG_DIR, f"wealth_agent_{datetime.now().strftime('%Y-%m-%d')}.log")
    file_handler = logging.handlers.TimedRotatingFileHandler(
        log_file, when='midnight', interval=1, backupCount=30,
        encoding='utf-8'
    )
    file_handler.setFormatter(formatter)

    # 创建控制台处理器
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(console_formatter)

    # 添加过滤器
    # 无论是否提供session_id，都添加过滤器，确保session_id字段存在
    session_filter = SessionFilter(session_id)
    logger.addFilter(session_filter)
    file_handler.addFilter(session_filter)
    console_handler.addFilter(session_filter)

    # 添加处理器
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)

    # 防止日志传播到父记录器
    logger.propagate = False

    return logger


def get_logger(name=__name__, session_id=None):
    """
    获取日志记录器，如果不存在则创建

    Args:
        name: 日志记录器名称
        session_id: 会话ID，用于跟踪请求

    Returns:
        日志记录器
    """
    logger = logging.getLogger(name)
    
    # 如果日志记录器没有处理器，设置默认配置
    if not logger.handlers:
        return setup_logger(name, session_id=session_id)
    
    # 确保始终有SessionFilter，无论是否提供了session_id
    has_session_filter = any(isinstance(f, SessionFilter) for f in logger.filters)
    if not has_session_filter:
        session_filter = SessionFilter(session_id)
        logger.addFilter(session_filter)
        for handler in logger.handlers:
            handler.addFilter(session_filter)
    
    return logger


def log_with_context(logger, level, message, **context):
    """
    记录带有上下文信息的日志

    Args:
        logger: 日志记录器
        level: 日志级别
        message: 日志消息
        **context: 上下文信息
    """
    # 将上下文信息格式化为字符串
    context_str = ' '.join([f"{k}={v}" for k, v in context.items()])
    full_message = f"{message} | {context_str}"
    
    # 记录日志
    logger.log(level, full_message)


def debug(logger, message, **context):
    """记录DEBUG级别的日志"""
    log_with_context(logger, logging.DEBUG, message, **context)


def info(logger, message, **context):
    """记录INFO级别的日志"""
    log_with_context(logger, logging.INFO, message, **context)


def warning(logger, message, **context):
    """记录WARNING级别的日志"""
    log_with_context(logger, logging.WARNING, message, **context)


def error(logger, message, **context):
    """记录ERROR级别的日志"""
    log_with_context(logger, logging.ERROR, message, **context)


def critical(logger, message, **context):
    """记录CRITICAL级别的日志"""
    log_with_context(logger, logging.CRITICAL, message, **context)
