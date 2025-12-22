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

-- 可选：为source字段也创建索引，优化按来源查询
CREATE INDEX IF NOT EXISTS idx_source ON RecentHotTopics(source);

-- 可选：为topic字段创建全文索引，支持主题关键词搜索
ALTER TABLE RecentHotTopics ADD FULLTEXT INDEX ft_idx_topic(topic);
