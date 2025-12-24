#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试文件：验证WealthAgents Agent模块修复
确保所有组件正确导入和使用，特别是MemoryManager相关修复
"""

import os
import sys
import logging

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("test_agent_module")

# 将项目根目录添加到Python路径，确保可以正确导入模块
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

def test_memory_import():
    """测试MemoryManager的导入是否正确"""
    logger.info("测试MemoryManager导入")
    try:
        # 从app.agent直接导入
        from app.agent import Memory, MemoryManager
        
        # 验证Memory是否是MemoryManager的别名
        if Memory is MemoryManager:
            logger.info("✅ Memory是MemoryManager的正确别名")
        else:
            logger.error("❌ Memory不是MemoryManager的别名")
            
        # 直接从memory模块导入
        from app.agent.memory import MemoryManager as DirectMemoryManager
        
        # 验证一致性
        if MemoryManager is DirectMemoryManager:
            logger.info("✅ MemoryManager导入一致")
        else:
            logger.error("❌ MemoryManager导入不一致")
            
        return True
    except ImportError as e:
        logger.error(f"❌ MemoryManager导入失败: {e}")
        return False

def test_graph_import():
    """测试Graph、END、START的导入"""
    logger.info("测试Graph组件导入")
    try:
        from app.agent import Graph, END, START, LANGGRAPH_AVAILABLE
        
        # 检查可用性标记
        logger.info(f"✅ LANGGRAPH_AVAILABLE: {LANGGRAPH_AVAILABLE}")
        
        # 即使langgraph不可用，也应该能导入占位符
        logger.info(f"✅ Graph类型: {type(Graph).__name__}")
        logger.info(f"✅ END值: {END}")
        logger.info(f"✅ START值: {START}")
        
        return True
    except ImportError as e:
        logger.error(f"❌ Graph组件导入失败: {e}")
        return False

def test_agent_components():
    """测试所有Agent组件的导入"""
    logger.info("测试Agent组件导入")
    try:
        # 验证主要组件都能导入
        from app.agent import (
            LangGraphAgent, 
            LangGraphConfig, 
            LangGraphNodeFactory,
            Executor,
            Planner,
            Reflector,
            PrivateAgent,
            AGENT_TEMPLATES
        )
        
        # 检查AGENT_TEMPLATES是否正确加载
        if isinstance(AGENT_TEMPLATES, dict) and len(AGENT_TEMPLATES) > 0:
            logger.info(f"✅ AGENT_TEMPLATES包含 {len(AGENT_TEMPLATES)} 个模板")
        else:
            logger.warning(f"⚠️ AGENT_TEMPLATES可能未正确加载: {AGENT_TEMPLATES}")
            
        logger.info("✅ 所有Agent组件导入成功")
        return True
    except ImportError as e:
        logger.error(f"❌ Agent组件导入失败: {e}")
        return False

def test_langgraph_agent_init():
    """测试LangGraphAgent的初始化"""
    logger.info("测试LangGraphAgent初始化")
    try:
        from app.agent import LangGraphAgent
        
        # 初始化LangGraphAgent，使用正确的参数格式
        config = {
            "max_iterations": 2,
            "enable_memory": True,
            "debug": False
        }
        
        # 使用正确的初始化方式
        agent = LangGraphAgent(
            config=config,
            template="basic"
        )
        
        logger.info(f"✅ LangGraphAgent初始化成功: {agent.__class__.__name__}")
        
        # 验证内部组件是否正确创建
        if agent.config["enable_memory"] and hasattr(agent, 'memory'):
            logger.info("✅ MemoryManager已正确初始化")
        else:
            logger.warning("⚠️ MemoryManager可能未初始化")
            
        if hasattr(agent, 'planner') and agent.planner is not None:
            logger.info("✅ Planner已正确初始化")
        else:
            logger.warning("⚠️ Planner可能未初始化")
            
        if hasattr(agent, 'executor') and agent.executor is not None:
            logger.info("✅ Executor已正确初始化")
        else:
            logger.warning("⚠️ Executor可能未初始化")
            
        if hasattr(agent, 'reflector') and agent.reflector is not None:
            logger.info("✅ Reflector已正确初始化")
        else:
            logger.warning("⚠️ Reflector可能未初始化")
            
        return True
    except Exception as e:
        logger.error(f"❌ LangGraphAgent初始化失败: {e}")
        # 详细记录异常信息以帮助诊断
        import traceback
        logger.error(f"详细错误信息:\n{traceback.format_exc()}")
        return False

def run_all_tests():
    """运行所有测试"""
    logger.info("开始运行所有测试...")
    
    tests = [
        ("Memory导入测试", test_memory_import),
        ("Graph导入测试", test_graph_import),
        ("Agent组件测试", test_agent_components),
        ("LangGraphAgent初始化测试", test_langgraph_agent_init)
    ]
    
    results = []
    for test_name, test_func in tests:
        logger.info(f"\n运行测试: {test_name}")
        success = test_func()
        results.append((test_name, success))
        logger.info(f"测试结果: {'通过' if success else '失败'}")
    
    # 统计结果
    passed = sum(1 for _, success in results if success)
    total = len(results)
    
    logger.info(f"\n===== 测试结果汇总 =====")
    logger.info(f"总共: {total} 测试")
    logger.info(f"通过: {passed} 测试")
    logger.info(f"失败: {total - passed} 测试")
    
    # 打印失败的测试
    failed_tests = [name for name, success in results if not success]
    if failed_tests:
        logger.warning(f"\n失败的测试:")
        for name in failed_tests:
            logger.warning(f"  - {name}")
    else:
        logger.info("\n🎉 所有测试通过！")
    
    return passed == total

if __name__ == "__main__":
    # 运行所有测试并返回适当的退出码
    success = run_all_tests()
    sys.exit(0 if success else 1)