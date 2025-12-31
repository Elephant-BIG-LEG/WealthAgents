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
CREATE INDEX idx_source ON RecentHotTopics(source);

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



-- 创建Company表，存储公司基本信息
CREATE TABLE IF NOT EXISTS Company (
    id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY COMMENT '自增主键',
    company_name VARCHAR(255) NOT NULL COMMENT '公司名称',
    english_name VARCHAR(255) DEFAULT NULL COMMENT '公司英文名',
    stock_code VARCHAR(20) DEFAULT NULL COMMENT '股票代码',
    industry VARCHAR(100) DEFAULT NULL COMMENT '所属行业',
    founded_year INT DEFAULT NULL COMMENT '成立年份',
    headquarters VARCHAR(255) DEFAULT NULL COMMENT '总部地点',
    website VARCHAR(255) DEFAULT NULL COMMENT '公司官网',
    knowledge_base_path VARCHAR(500) NOT NULL COMMENT '知识库存储路径',
    document_count INT UNSIGNED DEFAULT 0 COMMENT '文档数量',
    chunk_count INT UNSIGNED DEFAULT 0 COMMENT '文本块数量',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL COMMENT '创建时间',
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP NOT NULL COMMENT '更新时间',
    UNIQUE KEY uk_company_name (company_name) COMMENT '确保公司名称唯一',
    INDEX idx_industry (industry) COMMENT '行业索引',
    INDEX idx_stock_code (stock_code) COMMENT '股票代码索引'
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='公司基本信息表';

-- 创建CompanyVersion表，存储公司知识库版本历史
CREATE TABLE IF NOT EXISTS CompanyVersion (
    id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY COMMENT '自增主键',
    company_id BIGINT UNSIGNED NOT NULL COMMENT '关联的公司ID',
    document_count INT UNSIGNED NOT NULL COMMENT '文档数量',
    chunk_count INT UNSIGNED NOT NULL COMMENT '文本块数量',
    version_note TEXT DEFAULT NULL COMMENT '版本说明',
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '版本创建时间',

    INDEX idx_company_id (company_id),
    CONSTRAINT fk_company_version_company
        FOREIGN KEY (company_id)
        REFERENCES Company(id)
        ON DELETE CASCADE
) ENGINE=InnoDB
DEFAULT CHARSET=utf8mb4
COLLATE=utf8mb4_unicode_ci
COMMENT='公司知识库版本历史表';
