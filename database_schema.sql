-- MySQL数据库结构设计
-- 数据库名：FinanceData

-- 创建数据库（如果不存在）
CREATE DATABASE IF NOT EXISTS FinanceData 
CHARACTER SET utf8mb4 
COLLATE utf8mb4_unicode_ci;

-- 使用FinanceData数据库
USE FinanceData;

-- 创建RecentHotTopics表
CREATE TABLE IF NOT EXISTS RecentHotTopics (
    id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY COMMENT '自增主键',
    topic VARCHAR(255) NOT NULL COMMENT '热点主题',
    article_content TEXT COMMENT '市场背景和文章主体内容',
    investment_advice TEXT COMMENT '投资建议',
    market_summary TEXT COMMENT '行情与市场影响总结',
    source VARCHAR(50) NOT NULL COMMENT '数据来源',
    created_ts TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL COMMENT '数据入库时间',
    INDEX idx_created_ts (created_ts) COMMENT '时间索引，支持时间范围查询和排序'
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='近期财经热点数据表';

-- 为source字段也创建索引，优化按来源查询
CREATE INDEX IF NOT EXISTS idx_source ON RecentHotTopics(source);

-- 为topic字段创建全文索引，支持主题关键词搜索
ALTER TABLE RecentHotTopics ADD FULLTEXT INDEX ft_idx_topic(topic);



-- 创建ConversationHistory表，记录对话内容
CREATE TABLE IF NOT EXISTS ConversationHistory (
    id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY COMMENT '自增主键',
    session_id VARCHAR(64) NOT NULL COMMENT '会话ID，用于标识同一会话',
    message_id VARCHAR(64) NOT NULL COMMENT '消息ID，在会话内唯一',
    role VARCHAR(20) NOT NULL COMMENT '角色：user/assistant/system',
    content TEXT NOT NULL COMMENT '消息内容',
    task_type VARCHAR(50) DEFAULT NULL COMMENT '任务类型，关联planner中的任务类型',
    STATUS VARCHAR(20) DEFAULT 'sent' COMMENT '消息状态：sent/received/processed',
    metadata JSON DEFAULT NULL COMMENT '附加元数据，JSON格式存储',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL COMMENT '消息创建时间',
    INDEX idx_session_id (session_id) COMMENT '会话ID索引，优化会话查询',
    INDEX idx_created_at (created_at) COMMENT '时间索引，优化时间范围查询',
    UNIQUE KEY uk_session_msg (session_id, message_id) COMMENT '确保会话内消息ID唯一'
) ENGINE=INNODB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='对话历史记录表';

-- 为content字段创建全文索引，支持内容搜索
ALTER TABLE ConversationHistory ADD FULLTEXT INDEX ft_idx_content(content);

-- 为task_type字段创建索引，优化任务类型查询
CREATE INDEX idx_task_type ON ConversationHistory(task_type);
