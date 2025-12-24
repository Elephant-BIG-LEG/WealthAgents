"""
财富Agent - 智能投研分析平台
LangGraph Agent测试模块
验证LangGraphAgent和相关组件的功能正确性
"""
import unittest
from unittest.mock import MagicMock, patch
from typing import Dict, Any, List
from langgraph.graph import StateGraph as Graph, END, START
from app.agent.langgraph_agent import LangGraphAgent
from app.agent.langgraph_config import LangGraphConfig, LangGraphNodeFactory, AGENT_TEMPLATES

import sys
import os
from unittest.mock import patch, MagicMock
from typing import Dict, Any, List

# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class TestLangGraphAgent(unittest.TestCase):
    """
    LangGraphAgent测试类
    """
    
    def setUp(self):
        """
        测试前的初始化
        """
        # 使用mock来避免实际调用外部服务
        with patch('app.agent.langgraph_agent.Planner') as mock_planner, \
             patch('app.agent.langgraph_agent.Executor') as mock_executor, \
             patch('app.agent.langgraph_agent.Reflector') as mock_reflector, \
             patch('app.agent.langgraph_agent.MemoryManager') as mock_memory_manager:
            
            # 设置mock对象的行为
            self.mock_planner_instance = mock_planner.return_value
            self.mock_executor_instance = mock_executor.return_value
            self.mock_reflector_instance = mock_reflector.return_value
            self.mock_memory_manager_instance = mock_memory_manager.return_value
            
            # 创建LangGraphAgent实例
            self.agent = LangGraphAgent(template_name="basic_plan_act_reflect")
            
    def test_agent_initialization(self):
        """
        测试LangGraphAgent初始化功能
        """
        # 验证初始化是否成功
        self.assertIsNotNone(self.agent)
        self.assertIsNotNone(self.agent.planner)
        self.assertIsNotNone(self.agent.executor)
        self.assertIsNotNone(self.agent.reflector)
        self.assertIsNotNone(self.agent.memory_manager)
        
        # 验证默认参数是否正确设置
        self.assertEqual(self.agent.max_iterations, 3)
        self.assertFalse(self.agent.debug_mode)
    
    def test_initialization_with_custom_params(self):
        """
        测试使用自定义参数初始化
        """
        # 使用mock来避免实际调用外部服务
        with patch('app.agent.langgraph_agent.Planner'), \
             patch('app.agent.langgraph_agent.Executor'), \
             patch('app.agent.langgraph_agent.Reflector'), \
             patch('app.agent.langgraph_agent.MemoryManager'):
            
            # 使用自定义参数创建实例
            custom_agent = LangGraphAgent(
                max_iterations=5,
                debug_mode=True,
                template_name="iterative_improvement"
            )
            
            # 验证自定义参数是否生效
            self.assertEqual(custom_agent.max_iterations, 5)
            self.assertTrue(custom_agent.debug_mode)
    
    def test_get_current_timestamp(self):
        """
        测试获取当前时间戳功能
        """
        timestamp = self.agent._get_current_timestamp()
        self.assertIsNotNone(timestamp)
        self.assertTrue(isinstance(timestamp, str))
    
    def test_format_result(self):
        """
        测试结果格式化功能
        """
        # 准备测试数据
        state = {
            "user_request": "test request",
            "plan": ["task1", "task2"],
            "execution_result": {
                "tasks_results": ["result1", "result2"],
                "execution_time": 2.5
            },
            "plan_reflection": {
                "success_rate": 1.0,
                "avg_execution_time": 1.25,
                "suggestions": ["建议1"]
            },
            "execution_history": ["history1", "history2"],
            "status": "success"
        }
        
        # 调用格式化方法
        formatted_result = self.agent._format_result(state)
        
        # 验证格式化结果
        self.assertIn("user_request", formatted_result)
        self.assertIn("plan", formatted_result)
        self.assertIn("execution_result", formatted_result)
        self.assertIn("plan_reflection", formatted_result)
        self.assertIn("execution_history", formatted_result)
        self.assertIn("status", formatted_result)
        self.assertIn("timestamp", formatted_result)
        self.assertIn("result_summary", formatted_result)
    
    @patch('app.agent.langgraph_agent.Graph')
    def test_create_default_graph(self, mock_graph):
        """
        测试创建默认计算图功能
        """
        # 设置mock对象
        mock_graph_instance = mock_graph.return_value
        mock_graph_instance.add_node = MagicMock()
        mock_graph_instance.add_edge = MagicMock()
        mock_graph_instance.add_conditional_edges = MagicMock()
        
        # 调用创建计算图方法
        graph = self.agent._create_default_graph()
        
        # 验证方法调用
        mock_graph_instance.add_node.assert_any_call("plan", unittest.mock.ANY)
        mock_graph_instance.add_node.assert_any_call("execute", unittest.mock.ANY)
        mock_graph_instance.add_node.assert_any_call("reflect", unittest.mock.ANY)
        mock_graph_instance.add_node.assert_any_call("decide", unittest.mock.ANY)
        
        mock_graph_instance.add_edge.assert_any_call("plan", "execute")
        mock_graph_instance.add_edge.assert_any_call("execute", "reflect")
        
        mock_graph_instance.add_conditional_edges.assert_any_call("reflect", unittest.mock.ANY)
    
    @patch('app.agent.langgraph_agent.LangGraphAgent._create_default_graph')
    @patch('app.agent.langgraph_agent.Graph')
    def test_process_request_success(self, mock_graph, mock_create_graph):
        """
        测试处理请求成功的情况
        """
        # 设置mock对象行为
        mock_graph_instance = mock_graph.return_value
        mock_create_graph.return_value = mock_graph_instance
        
        # 模拟execute返回结果
        mock_result = {
            "user_request": "test request",
            "plan": ["task1"],
            "execution_result": {
                "tasks_results": ["result1"],
                "execution_time": 1.0
            },
            "plan_reflection": {
                "success_rate": 1.0
            },
            "status": "success"
        }
        mock_graph_instance.execute = MagicMock(return_value=mock_result)
        
        # 设置其他mock对象的行为
        self.mock_planner_instance.plan.return_value = ["task1"]
        self.mock_executor_instance.execute_plan.return_value = {
            "tasks_results": ["result1"],
            "execution_time": 1.0
        }
        self.mock_reflector_instance.reflect_on_task_execution.return_value = {}
        self.mock_reflector_instance.reflect_on_plan_execution.return_value = {
            "success_rate": 1.0
        }
        self.mock_reflector_instance.decide_next_step.return_value = {
            "action": "FINISH"
        }
        
        # 调用处理请求方法
        result = self.agent.process_request("test request")
        
        # 验证结果
        self.assertEqual(result["status"], "success")
        self.assertEqual(result["user_request"], "test request")
        mock_graph_instance.execute.assert_called_once()
    
    @patch('app.agent.langgraph_agent.LangGraphAgent._create_default_graph')
    @patch('app.agent.langgraph_agent.Graph')
    def test_process_request_with_error(self, mock_graph, mock_create_graph):
        """
        测试处理请求失败的情况
        """
        # 设置mock对象行为
        mock_graph_instance = mock_graph.return_value
        mock_create_graph.return_value = mock_graph_instance
        
        # 模拟execute抛出异常
        mock_graph_instance.execute = MagicMock(side_effect=Exception("测试错误"))
        
        # 调用处理请求方法
        with self.assertRaises(Exception) as context:
            self.agent.process_request("test request")
        
        # 验证异常信息
        self.assertIn("测试错误", str(context.exception))
    
    def test_process_request_with_custom_handlers(self):
        """
        测试使用自定义处理器处理请求
        """
        # 准备自定义处理器
        def custom_plan_preprocess(plan):
            return plan + ["custom_task"]
        
        custom_handlers = {
            "plan_preprocess": custom_plan_preprocess
        }
        
        # 使用mock来避免实际调用外部服务
        with patch('app.agent.langgraph_agent.LangGraphAgent._create_default_graph') as mock_create_graph, \
             patch('app.agent.langgraph_agent.Graph') as mock_graph:
            
            # 设置mock对象
            mock_graph_instance = mock_graph.return_value
            mock_create_graph.return_value = mock_graph_instance
            
            mock_result = {
                "user_request": "test request",
                "status": "success"
            }
            mock_graph_instance.execute = MagicMock(return_value=mock_result)
            
            # 调用处理请求方法
            result = self.agent.process_request(
                "test request",
                custom_handlers=custom_handlers
            )
            
            # 验证结果
            self.assertEqual(result["status"], "success")


class TestLangGraphConfig(unittest.TestCase):
    """
    LangGraphConfig测试类
    """
    
    def setUp(self):
        """
        测试前的初始化
        """
        self.config = LangGraphConfig()
    
    def test_config_initialization(self):
        """
        测试LangGraphConfig初始化
        """
        self.assertIsNotNone(self.config)
        self.assertEqual(len(self.config.nodes), 0)
        self.assertEqual(len(self.config.edges), 0)
        self.assertEqual(len(self.config.conditional_edges), 0)
    
    def test_add_node(self):
        """
        测试添加节点功能
        """
        # 定义测试函数
        def test_node(state):
            return state
        
        # 添加节点
        self.config.add_node("test_node", test_node, "测试节点")
        
        # 验证节点是否添加成功
        self.assertIn("test_node", self.config.nodes)
        self.assertEqual(self.config.nodes["test_node"]["description"], "测试节点")
    
    def test_add_edge(self):
        """
        测试添加边功能
        """
        # 添加边
        self.config.add_edge("node1", "node2")
        
        # 验证边是否添加成功
        self.assertIn(("node1", "node2"), self.config.edges)
    
    def test_add_conditional_edge(self):
        """
        测试添加条件边功能
        """
        # 定义路由函数
        def test_router(state):
            return "node1"
        
        # 添加条件边
        self.config.add_conditional_edge("node1", test_router, "测试条件边")
        
        # 验证条件边是否添加成功
        self.assertEqual(len(self.config.conditional_edges), 1)
        self.assertEqual(self.config.conditional_edges[0]["from_node"], "node1")
        self.assertEqual(self.config.conditional_edges[0]["description"], "测试条件边")
    
    @patch('app.agent.langgraph_config.Graph')
    def test_build_custom_graph(self, mock_graph):
        """
        测试构建自定义计算图功能
        """
        # 设置mock对象
        mock_graph_instance = mock_graph.return_value
        mock_graph_instance.add_node = MagicMock()
        mock_graph_instance.add_edge = MagicMock()
        mock_graph_instance.add_conditional_edges = MagicMock()
        
        # 添加节点和边
        def test_node(state): return state
        def test_router(state): return "node1"
        
        self.config.add_node("node1", test_node)
        self.config.add_node("node2", test_node)
        self.config.add_edge("node1", "node2")
        self.config.add_conditional_edge("node2", test_router)
        
        # 构建计算图
        graph = self.config.build_custom_graph()
        
        # 验证方法调用
        self.assertEqual(mock_graph_instance.add_node.call_count, 2)
        mock_graph_instance.add_edge.assert_called_once_with("node1", "node2")
        mock_graph_instance.add_conditional_edges.assert_called_once()


class TestLangGraphNodeFactory(unittest.TestCase):
    """
    LangGraphNodeFactory测试类
    """
    
    def setUp(self):
        """
        测试前的初始化
        """
        # 使用mock来避免实际调用外部服务
        with patch('app.agent.langgraph_agent.Planner'), \
             patch('app.agent.langgraph_agent.Executor'), \
             patch('app.agent.langgraph_agent.Reflector'), \
             patch('app.agent.langgraph_agent.MemoryManager'):
            
            # 创建LangGraphAgent实例
            self.agent = LangGraphAgent()
    
    def test_create_plan_node(self):
        """
        测试创建规划节点功能
        """
        # 创建规划节点
        plan_node = LangGraphNodeFactory.create_plan_node(self.agent)
        
        # 验证节点函数是否为可调用对象
        self.assertTrue(callable(plan_node))
        
        # 模拟planner.plan方法
        self.agent.planner.plan = MagicMock(return_value=["task1"])
        
        # 调用规划节点函数
        result = plan_node({"user_request": "test request"})
        
        # 验证结果
        self.assertIn("plan", result)
        self.assertEqual(result["plan"], ["task1"])
    
    def test_create_execute_node(self):
        """
        测试创建执行节点功能
        """
        # 创建执行节点
        execute_node = LangGraphNodeFactory.create_execute_node(self.agent)
        
        # 验证节点函数是否为可调用对象
        self.assertTrue(callable(execute_node))
        
        # 模拟executor.execute_plan方法
        self.agent.executor.execute_plan = MagicMock(return_value={
            "tasks_results": ["result1"],
            "execution_time": 1.0
        })
        
        # 调用执行节点函数
        result = execute_node({"plan": ["task1"], "execution_history": []})
        
        # 验证结果
        self.assertIn("execution_result", result)
        self.assertIn("execution_history", result)
    
    def test_create_reflect_node(self):
        """
        测试创建反思节点功能
        """
        # 创建反思节点
        reflect_node = LangGraphNodeFactory.create_reflect_node(self.agent)
        
        # 验证节点函数是否为可调用对象
        self.assertTrue(callable(reflect_node))
        
        # 模拟reflector方法
        self.agent.reflector.reflect_on_task_execution = MagicMock(return_value={"task_quality": 0.9})
        self.agent.reflector.reflect_on_plan_execution = MagicMock(return_value={"success_rate": 1.0})
        
        # 调用反思节点函数
        result = reflect_node({
            "execution_result": {
                "tasks_results": ["result1"],
                "execution_time": 1.0
            },
            "plan": ["task1"],
            "current_iteration": 0
        })
        
        # 验证结果
        self.assertIn("task_reflection", result)
        self.assertIn("plan_reflection", result)
        self.assertEqual(result["current_iteration"], 1)
    
    def test_create_decide_router(self):
        """
        测试创建决策路由器功能
        """
        # 创建决策路由器
        decide_router = LangGraphNodeFactory.create_decide_router(self.agent)
        
        # 验证路由器函数是否为可调用对象
        self.assertTrue(callable(decide_router))
        
        # 模拟reflector.decide_next_step方法
        self.agent.reflector.decide_next_step = MagicMock(return_value={"action": "FINISH"})
        
        # 调用决策路由器函数
        result = decide_router({
            "plan_reflection": {"success_rate": 1.0},
            "current_iteration": 1,
            "max_iterations": 3
        })
        
        # 验证结果
        self.assertEqual(result, "decide")


if __name__ == '__main__':
    unittest.main()