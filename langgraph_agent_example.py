"""
财富Agent - 智能投研分析平台
LangGraph Agent使用示例
演示如何使用基于LangGraph实现的Agent系统
"""
import os
import sys
import logging
from typing import Dict, Any

# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# 从agent模块导入所有必要的组件
from app.agent import (
    LangGraphAgent,
    LangGraphConfig,
    LangGraphNodeFactory,
    AGENT_TEMPLATES,
    Graph,  # 使用从__init__.py导出的Graph别名
    END, 
    START
)

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def example_basic_usage():
    """
    示例1: 基础使用方式
    使用默认配置创建并使用LangGraphAgent
    """
    logger.info("===== 示例1: 基础使用方式 =====")
    
    try:
        # 创建LangGraphAgent实例
        agent = LangGraphAgent()
        
        # 处理用户请求
        result = agent.process_request("分析最近一周特斯拉股票的走势和影响因素")
        
        # 输出结果
        logger.info(f"请求处理完成，状态: {result.get('status')}")
        logger.info(f"最终答案: {result.get('answer')}")
        
        return result
    except Exception as e:
        logger.error(f"基础示例执行失败: {str(e)}")
        return {"status": "error", "message": str(e)}


def example_custom_config():
    """
    示例2: 自定义配置
    通过自定义配置调整Agent行为
    """
    logger.info("\n===== 示例2: 自定义配置 =====")
    
    try:
        # 创建自定义配置
        custom_config = {
            "max_iterations": 5,
            "enable_memory": True,
            "custom_handlers": {
                "plan_preprocess": lambda plan: [t for t in plan if t.name != "unwanted_task"],
                "execution_postprocess": lambda result: {**result, "custom_flag": True}
            }
        }
        
        # 使用自定义配置创建Agent
        agent = LangGraphAgent(config=custom_config)
        
        # 处理用户请求
        result = agent.process_request("分析苹果公司最近的财报数据")
        
        logger.info(f"自定义配置Agent执行完成，状态: {result.get('status')}")
        return result
    except Exception as e:
        logger.error(f"自定义配置示例执行失败: {str(e)}")
        return {"status": "error", "message": str(e)}


def example_template_usage():
    """
    示例3: 使用预定义模板
    通过选择不同的Agent模板来调整行为模式
    """
    logger.info("\n===== 示例3: 使用预定义模板 =====")
    
    try:
        # 使用迭代改进型模板创建Agent
        agent = LangGraphAgent(template="iterative_improvement")
        
        # 处理用户请求
        result = agent.process_request("研究新能源行业的发展趋势")
        
        logger.info(f"模板Agent执行完成，状态: {result.get('status')}")
        logger.info(f"迭代次数: {result.get('iteration_count', 0)}")
        return result
    except Exception as e:
        logger.error(f"模板使用示例执行失败: {str(e)}")
        return {"status": "error", "message": str(e)}


def example_batch_processing():
    """
    示例4: 批量处理
    一次性处理多个相关请求
    """
    logger.info("\n===== 示例4: 批量处理 =====")
    
    try:
        # 创建Agent实例
        agent = LangGraphAgent()
        
        # 批量请求列表
        requests = [
            "分析微软公司的基本面情况",
            "评估亚马逊的竞争优势",
            "了解谷歌的最新业务发展"
        ]
        
        # 存储结果
        results = []
        
        # 逐个处理请求
        for i, req in enumerate(requests, 1):
            logger.info(f"处理请求 {i}/{len(requests)}: {req}")
            result = agent.process_request(req)
            results.append(result)
        
        logger.info(f"批量处理完成，共处理 {len(results)} 个请求")
        return results
    except Exception as e:
        logger.error(f"批量处理示例执行失败: {str(e)}")
        return {"status": "error", "message": str(e)}


def example_system_integration():
    """
    示例5: 系统集成
    演示如何与现有系统集成
    """
    logger.info("\n===== 示例5: 系统集成 =====")
    
    try:
        # 创建集成配置
        integration_config = {
            "enable_memory": True,
            "session_id": "user-12345",
            "custom_handlers": {
                "result_formatter": lambda result: {
                    "response": result.get("answer"),
                    "metadata": {
                        "timestamp": "2023-06-15T10:30:00Z",
                        "source": "LangGraph-Agent",
                        "version": "1.0.0"
                    }
                }
            }
        }
        
        # 创建Agent实例
        agent = LangGraphAgent(config=integration_config)
        
        # 构建上下文请求
        context_enriched_request = {
            "user_query": "分析当前市场的投资机会",
            "user_profile": {"risk_level": "medium", "investment_horizon": "long"},
            "market_context": "牛市"
        }
        
        # 处理请求
        result = agent.process_request(context_enriched_request)
        
        # 应用自定义格式化
        if "result_formatter" in integration_config["custom_handlers"]:
            formatted_result = integration_config["custom_handlers"]["result_formatter"](result)
            logger.info("已应用自定义格式化器")
            return formatted_result
        
        return result
    except Exception as e:
        logger.error(f"系统集成示例执行失败: {str(e)}")
        return {"status": "error", "message": str(e)}


if __name__ == "__main__":
    # 依次运行所有示例
    example_basic_usage()
    example_custom_config()
    example_template_usage()
    example_batch_processing()
    example_system_integration()
    
    logger.info("\n所有示例执行完毕！")
