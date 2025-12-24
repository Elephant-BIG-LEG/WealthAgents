"""
财富Agent - 智能投研分析平台
LangGraph节点和边配置模块
提供灵活的节点和边定义，支持自定义Agent行为
"""
from typing import Dict, Any, List, Callable, Optional
import logging

# 配置日志
logger = logging.getLogger(__name__)

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

# 延迟导入，避免循环导入
from .langgraph_agent import LangGraphAgent

class LangGraphConfig:
    """
    LangGraph配置管理类
    提供灵活的节点和边定义接口
    """
    
    def __init__(self):
        """
        初始化配置管理器
        """
        self.nodes = {}
        self.edges = []
        self.conditional_edges = []
        self.custom_routes = {}
    
    def add_node(self, node_name: str, node_function: Callable, description: str = ""):
        """
        添加自定义节点
        
        Args:
            node_name: 节点名称
            node_function: 节点执行函数
            description: 节点描述（可选）
        """
        self.nodes[node_name] = {
            "function": node_function,
            "description": description
        }
        logger.info(f"添加自定义节点: {node_name}")
    
    def add_edge(self, from_node: str, to_node: str):
        """
        添加自定义边
        
        Args:
            from_node: 起始节点
            to_node: 目标节点
        """
        self.edges.append((from_node, to_node))
        logger.info(f"添加边: {from_node} -> {to_node}")
    
    def add_conditional_edge(self, from_node: str, router_function: Callable, description: str = ""):
        """
        添加条件边
        
        Args:
            from_node: 起始节点
            router_function: 路由函数
            description: 边描述（可选）
        """
        self.conditional_edges.append({
            "from_node": from_node,
            "router": router_function,
            "description": description
        })
        logger.info(f"添加条件边: {from_node}")
    
    def add_custom_route(self, route_name: str, route_function: Callable):
        """
        添加自定义路由
        
        Args:
            route_name: 路由名称
            route_function: 路由函数
        """
        self.custom_routes[route_name] = route_function
        logger.info(f"添加自定义路由: {route_name}")
    
    def build_custom_graph(self) -> Graph:
        """
        构建自定义计算图
        
        Returns:
            构建好的Graph实例
        """
        logger.info("构建自定义计算图")
        
        # 创建计算图
        graph = Graph()
        
        # 添加所有节点
        for node_name, node_info in self.nodes.items():
            graph.add_node(node_name, node_info["function"])
        
        # 添加所有普通边
        for from_node, to_node in self.edges:
            graph.add_edge(from_node, to_node)
        
        # 添加所有条件边
        for edge_info in self.conditional_edges:
            from_node = edge_info["from_node"]
            router = edge_info["router"]
            graph.add_conditional_edges(from_node, router)
        
        return graph


class LangGraphNodeFactory:
    """
    LangGraph节点工厂类
    提供预定义节点实现
    """
    
    @staticmethod
    def create_plan_node(agent: LangGraphAgent) -> Callable:
        """
        创建规划节点
        
        Args:
            agent: LangGraphAgent实例
            
        Returns:
            规划节点函数
        """
        def plan_node(state: Dict[str, Any]) -> Dict[str, Any]:
            """规划节点实现"""
            logger.info("[自定义Plan节点] 开始规划任务")
            
            user_request = state.get("user_request")
            if not user_request:
                raise ValueError("用户请求不能为空")
                
            # 调用planner生成计划
            try:
                plan = agent.planner.plan(user_request)
                logger.info(f"[自定义Plan节点] 成功生成计划，包含 {len(plan)} 个任务")
                
                # 支持自定义预处理
                if "plan_preprocess" in state.get("custom_handlers", {}):
                    preprocess_func = state["custom_handlers"]["plan_preprocess"]
                    plan = preprocess_func(plan)
                
                return {
                    **state,
                    "plan": plan,
                    "current_iteration": 0,
                    "execution_history": []
                }
            except Exception as e:
                logger.error(f"[自定义Plan节点] 规划失败: {str(e)}")
                return {
                    **state,
                    "error": str(e),
                    "status": "failed"
                }
        
        return plan_node
    
    @staticmethod
    def create_execute_node(agent: LangGraphAgent) -> Callable:
        """
        创建执行节点
        
        Args:
            agent: LangGraphAgent实例
            
        Returns:
            执行节点函数
        """
        def execute_node(state: Dict[str, Any]) -> Dict[str, Any]:
            """执行节点实现"""
            logger.info("[自定义Execute节点] 开始执行计划")
            
            plan = state.get("plan")
            if not plan:
                raise ValueError("任务计划不存在")
                
            # 支持自定义计划修改
            if "plan_modifier" in state.get("custom_handlers", {}):
                modifier_func = state["custom_handlers"]["plan_modifier"]
                plan = modifier_func(plan, state)
            
            # 调用executor执行计划
            try:
                execution_result = agent.executor.execute_plan(plan)
                logger.info(f"[自定义Execute节点] 计划执行完成")
                
                # 支持自定义结果处理
                if "execution_postprocess" in state.get("custom_handlers", {}):
                    postprocess_func = state["custom_handlers"]["execution_postprocess"]
                    execution_result = postprocess_func(execution_result)
                
                # 更新执行历史
                execution_history = state.get("execution_history", [])
                execution_history.append({
                    "iteration": state.get("current_iteration", 0),
                    "execution_time": agent._format_result.__globals__["time"].time(),  # 访问time模块
                    "result": execution_result
                })
                
                return {
                    **state,
                    "execution_result": execution_result,
                    "execution_history": execution_history
                }
            except Exception as e:
                logger.error(f"[自定义Execute节点] 执行失败: {str(e)}")
                return {
                    **state,
                    "error": str(e),
                    "status": "failed"
                }
        
        return execute_node
    
    @staticmethod
    def create_reflect_node(agent: LangGraphAgent) -> Callable:
        """
        创建反思节点
        
        Args:
            agent: LangGraphAgent实例
            
        Returns:
            反思节点函数
        """
        def reflect_node(state: Dict[str, Any]) -> Dict[str, Any]:
            """反思节点实现"""
            logger.info("[自定义Reflect节点] 开始反思执行结果")
            
            execution_result = state.get("execution_result")
            plan = state.get("plan")
            
            if not execution_result or not plan:
                raise ValueError("执行结果或计划不存在")
                
            # 调用reflector进行反思
            try:
                # 任务执行反思
                task_reflection = agent.reflector.reflect_on_task_execution(
                    execution_result['tasks_results'],
                    execution_result['execution_time']
                )
                
                # 计划执行反思
                plan_reflection = agent.reflector.reflect_on_plan_execution(
                    plan, 
                    execution_result['tasks_results'],
                    task_reflection
                )
                
                # 支持自定义反思增强
                if "reflection_enhancer" in state.get("custom_handlers", {}):
                    enhancer_func = state["custom_handlers"]["reflection_enhancer"]
                    plan_reflection = enhancer_func(plan_reflection, state)
                
                logger.info(f"[自定义Reflect节点] 反思完成，成功率: {plan_reflection['success_rate']:.2%}")
                
                return {
                    **state,
                    "task_reflection": task_reflection,
                    "plan_reflection": plan_reflection,
                    "current_iteration": state.get("current_iteration", 0) + 1
                }
            except Exception as e:
                logger.error(f"[自定义Reflect节点] 反思失败: {str(e)}")
                return {
                    **state,
                    "error": str(e),
                    "status": "failed"
                }
        
        return reflect_node
    
    @staticmethod
    def create_decide_router(agent: LangGraphAgent) -> Callable:
        """
        创建决策路由器
        
        Args:
            agent: LangGraphAgent实例
            
        Returns:
            决策路由函数
        """
        def decide_router(state: Dict[str, Any]) -> str:
            """决策路由实现"""
            plan_reflection = state.get("plan_reflection")
            current_iteration = state.get("current_iteration", 0)
            max_iterations = state.get("max_iterations", 3)
            
            if not plan_reflection:
                return END
            
            # 决定下一步
            decision = agent.reflector.decide_next_step(
                plan_reflection,
                max_retries=max_iterations,
                current_retry=current_iteration - 1
            )
            
            # 调用自定义路由逻辑（如果有）
            if "custom_router" in state.get("custom_handlers", {}):
                custom_router_func = state["custom_handlers"]["custom_router"]
                return custom_router_func(state, decision)
            
            # 默认路由逻辑
            if decision["action"] == "FINISH" or current_iteration >= max_iterations:
                return "decide"
            else:
                return "execute"
        
        return decide_router


# 预定义的Agent配置模板
AGENT_TEMPLATES = {
    "basic_plan_act_reflect": {
        "description": "基础的Plan-Act-Reflect决策闭环",
        "nodes": ["plan", "execute", "reflect", "decide"],
        "edges": [
            (START, "plan"),
            ("plan", "execute"),
            ("execute", "reflect"),
        ],
        "conditional_edges": [
            ("reflect", "decide_router")
        ],
        "default_router": "decide_router"
    },
    
    "iterative_improvement": {
        "description": "迭代改进型Agent，支持自动重试失败任务",
        "nodes": ["plan", "execute", "reflect", "decide", "improve"],
        "edges": [
            (START, "plan"),
            ("plan", "execute"),
            ("execute", "reflect"),
            ("improve", "execute"),
        ],
        "conditional_edges": [
            ("reflect", "advanced_router")
        ],
        "default_router": "advanced_router"
    },
    
    "multi_step_plan": {
        "description": "多步骤规划型Agent，支持复杂任务分解",
        "nodes": ["plan", "execute_main", "execute_subtasks", "reflect", "decide"],
        "edges": [
            (START, "plan"),
            ("plan", "execute_main"),
            ("execute_main", "execute_subtasks"),
            ("execute_subtasks", "reflect"),
        ],
        "conditional_edges": [
            ("reflect", "decide_router")
        ],
        "default_router": "decide_router"
    }
}