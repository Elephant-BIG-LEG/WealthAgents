"""
财富Agent - 智能投研分析平台
LangGraph Agent实现模块
基于LangGraph框架的智能Agent系统
TODO
"""

import os
import sys
import logging
from typing import Dict, Any, Optional, Callable, List, TypedDict

# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 定义LangGraph状态模式
class AgentState(TypedDict):
    query: str
    plan: list
    execution_result: dict
    reflection: dict
    next_action: str
    current_step: int
    iterations: int
    history: list
    context: str
    user_profile: dict

# 尝试从agent包导入其他组件
from .planner import Planner
from .executor import Executor
from .reflector import Reflector
from .memory import MemoryManager

# 尝试导入LangGraph相关组件，但使用try-except处理导入失败
LANGGRAPH_AVAILABLE = False
try:
    # 尝试从langgraph包导入
    from langgraph.graph import StateGraph as Graph, END, START
    LANGGRAPH_AVAILABLE = True
    logger.info("LangGraph组件导入成功")
except ImportError:
    logger.warning("LangGraph组件导入失败，某些功能可能不可用")
    # 创建占位符类以保持接口一致性
    class GraphPlaceholder:
        def __init__(self, *args, **kwargs):
            self.name = "placeholder_graph"
        
        def add_node(self, *args, **kwargs):
            pass
        
        def add_edge(self, *args, **kwargs):
            pass
        
        def add_conditional_edges(self, *args, **kwargs):
            pass
        
        def compile(self):
            return CompiledGraphPlaceholder()
    
    class CompiledGraphPlaceholder:
        def __call__(self, *args, **kwargs):
            logger.warning("使用Graph占位符，返回模拟结果")
            return {
                "status": "warning", 
                "message": "LangGraph不可用，使用模拟结果",
                "answer": "这是一个模拟的响应结果。要获得完整功能，请安装langgraph包。"
            }
    
    Graph = GraphPlaceholder
    END = None
    START = None


class LangGraphAgent:
    """
    基于LangGraph的Agent实现
    使用Plan-Act-Reflect决策闭环模式
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None, 
                 template: Optional[str] = "basic"):
        """
        初始化LangGraphAgent
        
        Args:
            config: 配置字典，包含max_iterations、enable_memory等设置
            template: Agent模板类型，如'basic'、'iterative_improvement'等
        """
        # 使用默认配置更新用户配置
        self.config = {
            "max_iterations": 3,
            "enable_memory": False,
            "custom_handlers": {},
            "debug": False
        }
        
        if config:
            self.config.update(config)
        
        self.template = template
        # 先创建MemoryManager（如果启用）
        self.memory = MemoryManager() if self.config["enable_memory"] else None
        
        # 使用memory_manager初始化其他组件
        memory_manager = self.memory  # 使用本地变量确保一致性
        self.executor = Executor(memory_manager=memory_manager)
        self.planner = Planner()
        self.reflector = Reflector(memory_manager=memory_manager)
        
        # 创建计算图
        self.graph = self._build_graph()
        
    def _build_graph(self) -> Graph:
        """
        构建LangGraph计算图
        
        Returns:
            编译后的LangGraph计算图
        """
        # 创建Graph实例，使用AgentState类型作为状态模式
        graph = Graph(name="WealthAgentGraph", state_schema=AgentState)
        
        # 添加节点 TODO 这里就是使用 LangGraph 来管理了
        graph.add_node("plan", self._plan_node)
        graph.add_node("execute", self._execute_node)
        graph.add_node("reflect", self._reflect_node)
        graph.add_node("decide", self._decide_node)
        
        # 添加边
        graph.add_edge(START, "plan")
        graph.add_edge("plan", "execute")
        graph.add_edge("execute", "reflect")
        
        # 添加条件边
        graph.add_conditional_edges(
            "decide",
            self._route_next_step,
            {
                "finish": END,
                "replan": "plan",
                "retry": "execute"
            }
        )
        
        # 完成决策后路由到决策节点
        graph.add_edge("reflect", "decide")
        
        # 编译图
        return graph.compile()
    
    def _plan_node(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """
        规划节点：负责生成执行计划
        """
        user_query = state.get("query", "")
        logger.info(f"Planning for query: {user_query}")

        try:
            # 1. 获取上下文信息
            context = []
            if self.memory:
                try:
                    context = self.memory.get_context(user_query)
                except Exception as e:
                    logger.error(f"Error getting context from memory: {e}")
                    # 使用空上下文继续执行
                    context = []

            # 2. 生成执行计划
            if self.planner:
                try:
                    plan = self.planner.create_plan(user_query, context)
                except Exception as e:
                    logger.error(f"Error creating plan: {e}")
                    # 如果规划失败，创建一个默认的通用查询任务
                    plan = [{
                        "id": "default_task_1",
                        "name": "通用查询",
                        "description": "处理通用查询请求",
                        "tool_name": "general_query",
                        "parameters": {"query": user_query},
                        "dependencies": []
                    }]
            else:
                # 如果没有规划器，创建一个默认的通用查询任务
                plan = [{
                    "id": "default_task_1",
                    "name": "通用查询",
                    "description": "处理通用查询请求",
                    "tool_name": "general_query",
                    "parameters": {"query": user_query},
                    "dependencies": []
                }]

            logger.info(f"Generated plan with {len(plan)} tasks")

            # 3. 更新状态
            state["plan"] = plan
            state["current_task_index"] = 0
            state["task_results"] = []
            state["reflection"] = ""
            state["error"] = None

        except Exception as e:
            logger.error(f"Unexpected error in _plan_node: {e}")
            state["error"] = str(e)
            state["plan"] = []

        return state
    
    def _execute_node(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """
        执行节点
        执行计划中的任务
        """
        logger.info("进入执行节点")
        plan = state.get("plan", [])
        current_step = state.get("current_step", 0)
        
        # 检查计划是否为空或已完成
        if not plan or current_step >= len(plan):
            return {
                **state,
                "status": "completed",
                "execution_result": "计划已执行完成"
            }
        
        # 执行当前步骤
        current_task = plan[current_step]
        logger.info(f"执行任务 {current_step+1}/{len(plan)}: {current_task}")
        
        # 执行任务
        execution_result = self.executor.execute_task(current_task)
        
        # 应用自定义处理函数（如果有）
        if "execution_postprocess" in self.config["custom_handlers"]:
            execution_result = self.config["custom_handlers"]["execution_postprocess"](execution_result)
        
        # 更新状态
        return {
            **state,
            "execution_result": execution_result,
            "current_step": current_step + 1,
            "history": state.get("history", []) + [f"执行任务 {current_step+1}: {execution_result}"]
        }
    
    def _reflect_node(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """
        反思节点
        分析执行结果并提供反馈
        """
        logger.info("进入反思节点")
        execution_result = state.get("execution_result", {})
        plan = state.get("plan", [])
        current_step = state.get("current_step", 0)
        query = state.get("query", "")
        
        # 反思当前执行
        reflection = self.reflector.reflect(
            query=query,
            plan=plan,
            execution_result=execution_result,
            current_step=current_step
        )
        
        # 更新状态
        return {
            **state,
            "reflection": reflection,
            "history": state.get("history", []) + [f"反思: {reflection}"]
        }
    
    def _decide_node(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """
        决策节点
        决定下一步操作
        """
        logger.info("进入决策节点")
        reflection = state.get("reflection", {})
        plan = state.get("plan", [])
        current_step = state.get("current_step", 0)
        iterations = state.get("iterations", 0)
        
        # 决定下一步行动
        next_action = self.reflector.decide_next_step(
            reflection=reflection,
            plan=plan,
            current_step=current_step,
            max_iterations=self.config["max_iterations"],
            current_iteration=iterations
        )
        
        # 更新状态
        return {
            **state,
            "next_action": next_action,
            "iterations": iterations + 1,
            "history": state.get("history", []) + [f"决策: {next_action}"]
        }
    
    def _route_next_step(self, state: Dict[str, Any]) -> str:
        """
        路由函数
        根据决策结果确定下一个节点
        """
        next_action = state.get("next_action", "finish")
        return next_action
    
    def process_request(self, request: Any) -> Dict[str, Any]:
        """
        处理用户请求
        
        Args:
            request: 用户请求，可以是字符串或包含更多上下文的字典
            
        Returns:
            处理结果字典
        """
        logger.info(f"处理请求: {request}")
        
        # 如果langgraph不可用，返回警告信息
        if not LANGGRAPH_AVAILABLE:
            return {
                "status": "warning",
                "message": "LangGraph不可用，返回简化结果",
                "answer": "这是一个简化的响应结果。要获得完整功能，请安装langgraph包。"
            }
        
        # 准备初始状态
        if isinstance(request, dict):
            # 处理复杂请求格式
            query = request.get("user_query", "")
            initial_state = {
                "query": query,
                "context": request.get("context", ""),
                "user_profile": request.get("user_profile", {}),
                "plan": [],
                "execution_result": {},
                "reflection": {},
                "next_action": "",
                "current_step": 0,
                "iterations": 0,
                "history": []
            }
        else:
            # 处理简单字符串请求
            initial_state = {
                "query": str(request),
                "plan": [],
                "execution_result": {},
                "reflection": {},
                "next_action": "",
                "current_step": 0,
                "iterations": 0,
                "history": []
            }
        
        # 执行图计算
        result = self.graph(initial_state)
        
        # 保存到内存（如果启用了memory）
        if self.memory:
            self.memory.save_interaction(
                initial_state["query"], 
                result.get("execution_result", "")
            )
        
        # 应用结果格式化函数（如果有）
        if "result_formatter" in self.config["custom_handlers"]:
            result = self.config["custom_handlers"]["result_formatter"](result)
        
        logger.info("请求处理完成")
        return result


def main():
    """
    主函数，用于测试LangGraphAgent
    """
    # 创建LangGraphAgent实例
    agent = LangGraphAgent()
    
    # 处理测试请求
    result = agent.process_request("分析最近一周的市场行情")
    
    # 打印结果
    print(f"处理结果: {result}")


if __name__ == "__main__":
    main()







