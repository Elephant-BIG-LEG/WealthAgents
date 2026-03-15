#!/usr/bin/env python3
# 测试优化后的ToolRouter功能

import sys
import os

# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.agent.tool_router import ToolRouter

def test_tool_router():
    """测试优化后的ToolRouter功能"""
    print("=== 测试优化后的ToolRouter功能 ===")
    
    # 创建ToolRouter实例
    router = ToolRouter(enable_llm_selection=True)
    
    # 测试数据
    test_query = "查询苹果公司的最新股价和财务报表"
    available_tools = ["market_data_adapter", "financial_report_adapter", "web_scraping_tool", "data_analysis", "general_query"]
    
    # 工具定义（模拟完整的工具描述）
    tool_definitions = [
        {
            "name": "market_data_adapter",
            "description": "获取实时市场数据，包括股价、涨跌幅、成交量等信息"
        },
        {
            "name": "financial_report_adapter", 
            "description": "获取公司财务报表数据，包括年报、季报、营收、利润等信息"
        },
        {
            "name": "web_scraping_tool",
            "description": "从网页抓取数据，支持各种网站的数据采集"
        },
        {
            "name": "data_analysis",
            "description": "对数据进行分析处理，生成分析报告和可视化结果"
        },
        {
            "name": "general_query",
            "description": "处理通用查询，提供基础信息和回答"
        }
    ]
    
    print(f"\n测试查询: {test_query}")
    print(f"可用工具: {available_tools}")
    
    # 测试1：只使用关键词匹配（旧模式）
    print("\n1. 只使用关键词匹配:")
    keyword_only_tools = router.recommend_tools(
        query=test_query,
        available_tools=available_tools,
        tool_definitions=tool_definitions,
        use_llm=False
    )
    print(f"结果: {keyword_only_tools}")
    
    # 测试2：优先使用LLM选择（新模式）
    print("\n2. 优先使用LLM选择:")
    try:
        llm_tools = router.recommend_tools(
            query=test_query,
            available_tools=available_tools,
            tool_definitions=tool_definitions,
            use_llm=True
        )
        print(f"结果: {llm_tools}")
        
        if llm_tools:
            print("✓ LLM工具选择成功")
        else:
            print("! LLM工具选择返回空列表，可能是因为没有配置API密钥")
    except Exception as e:
        print(f"! LLM工具选择失败: {e}")
    
    # 测试3：检查关键词过滤功能
    print("\n3. 关键词过滤功能测试:")
    keyword_filtered = router.route_by_keywords(test_query, available_tools)
    print(f"结果: {keyword_filtered}")
    
    print("\n=== 测试完成 ===")

if __name__ == "__main__":
    test_tool_router()
