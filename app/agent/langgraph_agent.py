"""
财富Agent - 智能投研分析平台
LangGraph Agent实现模块
基于LangGraph框架的智能Agent系统
TODO
"""

from .memory import MemoryManager
from .reflector import Reflector
from .executor import Executor
from .planner import Planner
import os
import sys
import time
import logging
from typing import Dict, Any, Optional, Callable, List, TypedDict

# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.dirname(
    os.path.dirname(os.path.abspath(__file__)))))

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 定义增强的 LangGraph 状态模式


class AgentState(TypedDict):
    """增强的 Agent 状态定义"""
    query: str                              # 用户查询
    plan: List[Dict[str, Any]]             # 任务计划列表
    execution_result: Dict[str, Any]       # 执行结果
    reflection: Dict[str, Any]             # 反思结果
    decision: Dict[str, Any]               # 决策结果
    next_action: str                       # 下一步行动
    current_step: int                      # 当前步骤
    iterations: int                        # 迭代次数
    history: List[Dict[str, Any]]          # 历史记录
    context: str                           # 上下文
    user_profile: Dict[str, Any]           # 用户画像
    tool_call_history: List[Dict[str, Any]]  # 工具调用历史
    context_memory: Dict[str, Any]         # 上下文记忆
    decision_trace: List[Dict[str, Any]]   # 决策轨迹
    max_iterations: int                    # 最大迭代次数
    convergence_criteria: Dict[str, Any]   # 收敛条件
    state: str                             # 当前状态


# 尝试从 agent 包导入其他组件

# 导入增强版组件
try:
    from .enhanced_planner import EnhancedPlanner
    from .enhanced_executor import EnhancedExecutor
    from .enhanced_reflector import EnhancedReflector
    logger.info("增强版组件导入成功")
except ImportError as e:
    logger.warning(f"增强版组件导入失败：{e}, 将使用基础版本")
    # 如果导入失败，使用原版本作为后备
    EnhancedPlanner = Planner
    EnhancedExecutor = Executor
    EnhancedReflector = Reflector

# 尝试导入 LangGraph 相关组件，但使用 try-except 处理导入失败
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
        初始化 LangGraphAgent

        Args:
            config: 配置字典，包含 max_iterations、enable_memory 等设置
            template: Agent 模板类型，如'basic'、'iterative_improvement'等
        """
        # 使用默认配置更新用户配置
        self.config = {
            "max_iterations": 5,              # 增加最大迭代次数
            "enable_memory": True,            # 默认启用记忆
            "custom_handlers": {},
            "debug": True,                    # 启用调试模式
            "parallel_execution": True,       # 支持并行执行
            "convergence_threshold": 0.8,     # 收敛阈值（成功率）
            "retry_with_backoff": True,       # 启用指数退避重试
            "tool_timeout": 30                # 工具调用超时时间（秒）
        }

        if config:
            self.config.update(config)

        self.template = template
        # 先创建 MemoryManager（如果启用）
        self.memory = MemoryManager() if self.config["enable_memory"] else None

        # 使用 memory_manager 初始化其他组件
        memory_manager = self.memory  # 使用本地变量确保一致性
        self.executor = Executor(
            memory_manager=memory_manager, config=self.config)
        self.planner = EnhancedPlanner(
            memory_manager=memory_manager)  # 使用增强版规划器
        self.reflector = EnhancedReflector(
            memory_manager=memory_manager)  # 使用增强版反思器

        # 创建计算图
        self.graph = self._build_graph()

    def _build_graph(self) -> Graph:
        """
        构建增强的 LangGraph 计算图
        实现 Plan → Act → Reflect → Decision → Replan 闭环

        Returns:
            编译后的 LangGraph 计算图
        """
        # 创建 Graph 实例，使用 AgentState 类型作为状态模式
        graph = Graph(name="WealthAgentGraph", state_schema=AgentState)

        # 添加增强的节点
        graph.add_node("plan", self._enhanced_plan_node)
        graph.add_node("execute", self._parallel_execute_node)
        graph.add_node("reflect", self._deep_reflect_node)
        graph.add_node("decide", self._intelligent_decide_node)

        # 添加边 - 完整的循环流程
        graph.add_edge(START, "plan")                    # 从开始到规划
        graph.add_edge("plan", "execute")                # 规划后执行
        graph.add_edge("execute", "reflect")             # 执行后反思
        graph.add_edge("reflect", "decide")              # 反思后决策

        # 添加条件边 - 根据决策结果路由
        graph.add_conditional_edges(
            "decide",
            self._route_next_step,
            {
                "finish": END,                           # 完成，结束
                "replan": "plan",                        # 重新规划
                "retry": "execute",                      # 重试执行
                "partial": "reflect"                     # 部分成功，继续反思
            }
        )

        # 编译图
        return graph.compile()

    def _enhanced_plan_node(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """
        增强的规划节点：负责任务拆解和依赖管理
        支持动态重规划和备选方案生成
        """
        user_query = state.get("query", "")
        logger.info(f"[规划节点] 处理查询：{user_query}")

        try:
            # 1. 获取增强的上下文信息
            context = []
            tool_call_history = state.get("tool_call_history", [])
            decision_trace = state.get("decision_trace", [])

            if self.memory:
                try:
                    context = self.memory.get_context(user_query)
                    logger.info(f"从记忆获取上下文：{len(context)} 条记录")
                except Exception as e:
                    logger.error(f"Error getting context from memory: {e}")
                    context = []

            # 2. 检查是否需要重新规划
            is_replan = state.get("iterations", 0) > 0
            previous_reflection = state.get("reflection", {})

            # 3. 生成或调整执行计划
            if self.planner:
                try:
                    # 使用增强版规划器
                    plan = self.planner.create_enhanced_plan(
                        user_query=user_query,
                        context=context,
                        tool_call_history=tool_call_history,
                        previous_reflection=previous_reflection if is_replan else None,
                        is_replan=is_replan
                    )
                    logger.info(
                        f"{'重新' if is_replan else ''}生成计划，包含 {len(plan)} 个任务")
                except Exception as e:
                    logger.error(f"Error creating plan: {e}")
                    # 创建默认计划
                    plan = [{
                        "id": "default_task_1",
                        "name": "通用查询",
                        "description": "处理通用查询请求",
                        "tool_name": "general_query",
                        "parameters": {"query": user_query},
                        "dependencies": [],
                        "priority": "high"
                    }]
            else:
                plan = [{
                    "id": "default_task_1",
                    "name": "通用查询",
                    "description": "处理通用查询请求",
                    "tool_name": "general_query",
                    "parameters": {"query": user_query},
                    "dependencies": [],
                    "priority": "high"
                }]

            # 4. 更新状态
            state["plan"] = plan
            state["current_step"] = 0
            state["state"] = "planning_complete"

            # 记录规划历史
            planning_record = {
                "timestamp": time.time(),
                "action": "plan_created" if not is_replan else "plan_revised",
                "task_count": len(plan),
                "is_replan": is_replan
            }
            state["history"] = state.get("history", []) + [planning_record]

        except Exception as e:
            logger.error(f"Unexpected error in _enhanced_plan_node: {e}")
            state["error"] = str(e)
            state["plan"] = []
            state["state"] = "planning_failed"

        return state

    def _parallel_execute_node(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """
        增强的执行节点：支持并行执行和工具链编排
        实现超时控制和熔断机制
        """
        logger.info("[执行节点] 开始执行任务")
        plan = state.get("plan", [])
        current_step = state.get("current_step", 0)

        # 任务优先级与依赖调度
        try:
            from .state_machine import schedule_tasks_by_priority_and_dependency
            plan = schedule_tasks_by_priority_and_dependency(plan)
            state["plan"] = plan
        except Exception as e:
            logger.debug(f"优先级调度未应用: {e}")

        # 检查计划是否为空或已完成
        if not plan or current_step >= len(plan):
            return {
                **state,
                "status": "completed",
                "execution_result": {"message": "计划已执行完成"},
                "state": "execution_complete"
            }

        # 识别可并行执行的任务
        parallel_tasks = []
        sequential_tasks = []

        for task in plan[current_step:]:
            if not task.get("dependencies", []):
                parallel_tasks.append(task)
            else:
                sequential_tasks.append(task)

        # 执行任务
        execution_results = []
        tool_call_history = state.get("tool_call_history", [])

        # 1. 并行执行独立任务
        if parallel_tasks and self.config.get("parallel_execution", True):
            logger.info(f"并行执行 {len(parallel_tasks)} 个独立任务")
            parallel_results = self.executor.execute_parallel(
                parallel_tasks,
                timeout=self.config.get("tool_timeout", 30)
            )
            execution_results.extend(parallel_results)

            # 记录工具调用历史
            for task, result in zip(parallel_tasks, parallel_results):
                tool_call_history.append({
                    "task_id": task["id"],
                    "tool_name": task["tool_name"],
                    "result": result,
                    "timestamp": time.time()
                })

        # 2. 顺序执行依赖任务
        for task in sequential_tasks:
            logger.info(f"顺序执行任务：{task['name']}")
            result = self.executor.execute_with_retry(
                task,
                max_retries=3 if self.config.get(
                    "retry_with_backoff", True) else 1,
                timeout=self.config.get("tool_timeout", 30)
            )
            execution_results.append(result)

            # 记录工具调用历史
            tool_call_history.append({
                "task_id": task["id"],
                "tool_name": task["tool_name"],
                "result": result,
                "timestamp": time.time()
            })

        # 聚合执行结果
        aggregated_result = self.executor.aggregate_results(execution_results)

        # 更新状态
        new_state = {
            **state,
            "execution_result": aggregated_result,
            "current_step": current_step + len(plan),  # 跳过所有已执行任务
            "tool_call_history": tool_call_history,
            "state": "execution_complete"
        }

        # 应用自定义处理函数（如果有）
        if "execution_postprocess" in self.config.get("custom_handlers", {}):
            new_state["execution_result"] = self.config["custom_handlers"]["execution_postprocess"](
                new_state["execution_result"]
            )

        return new_state

    def _deep_reflect_node(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """
        增强的反思节点：深度评估执行效果
        实现根因分析和模式识别
        """
        logger.info("[反思节点] 开始深度反思")
        execution_result = state.get("execution_result", {})
        plan = state.get("plan", [])
        query = state.get("query", "")
        tool_call_history = state.get("tool_call_history", [])

        # 使用增强版反思器进行深度评估
        if self.reflector:
            try:
                reflection = self.reflector.deep_reflect(
                    query=query,
                    plan=plan,
                    execution_result=execution_result,
                    tool_call_history=tool_call_history,
                    convergence_threshold=self.config.get(
                        "convergence_threshold", 0.8)
                )

                logger.info(
                    f"反思完成，成功率：{reflection.get('success_rate', 0):.2%}")

            except Exception as e:
                logger.error(f"Error in reflection: {e}")
                reflection = {
                    "success_rate": 0,
                    "evaluation": {"quality": "poor"},
                    "root_cause_analysis": f"反思过程出错：{str(e)}",
                    "recommendations": ["检查系统状态后重试"]
                }
        else:
            reflection = {
                "success_rate": 0,
                "evaluation": {"quality": "unknown"},
                "recommendations": ["反思器未初始化"]
            }

        # 更新状态
        state["reflection"] = reflection
        state["state"] = "reflection_complete"

        # 记录反思历史
        reflection_record = {
            "timestamp": time.time(),
            "action": "deep_reflection",
            "success_rate": reflection.get("success_rate", 0),
            "key_findings": reflection.get("key_findings", [])
        }
        state["history"] = state.get("history", []) + [reflection_record]

        return state

    def _intelligent_decide_node(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """
        增强的决策节点：智能路由决策
        基于多维度评估决定下一步行动
        """
        logger.info("[决策节点] 制定决策")
        reflection = state.get("reflection", {})
        plan = state.get("plan", [])
        iterations = state.get("iterations", 0)
        max_iterations = self.config.get("max_iterations", 5)
        tool_call_history = state.get("tool_call_history", [])

        # 使用增强版反思器进行智能决策
        if self.reflector:
            try:
                decision = self.reflector.intelligent_decision(
                    reflection=reflection,
                    plan=plan,
                    current_iteration=iterations,
                    max_iterations=max_iterations,
                    tool_call_history=tool_call_history,
                    convergence_threshold=self.config.get(
                        "convergence_threshold", 0.8)
                )

                logger.info(f"决策结果：{decision.get('action', 'unknown')}")

            except Exception as e:
                logger.error(f"Error in decision making: {e}")
                decision = {
                    "action": "finish",
                    "reason": f"决策过程出错：{str(e)}",
                    "confidence": 0.0
                }
        else:
            decision = {
                "action": "finish",
                "reason": "反思器未初始化",
                "confidence": 0.0
            }

        # 更新状态
        state["decision"] = decision
        state["next_action"] = decision.get("action", "finish")
        state["iterations"] = iterations + 1
        state["state"] = "decision_complete"

        # 记录决策轨迹
        decision_trace = state.get("decision_trace", [])
        decision_trace.append({
            "timestamp": time.time(),
            "iteration": iterations,
            "action": decision.get("action"),
            "reason": decision.get("reason"),
            "confidence": decision.get("confidence", 0)
        })
        state["decision_trace"] = decision_trace

        # 记录决策历史
        decision_record = {
            "timestamp": time.time(),
            "action": "intelligent_decision",
            "decision": decision
        }
        state["history"] = state.get("history", []) + [decision_record]

        return state

    def _route_next_step(self, state: Dict[str, Any]) -> str:
        """
        增强的路由函数
        根据决策结果确定下一个节点，支持部分成功场景

        Args:
            state: 当前状态

        Returns:
            下一个节点名称
        """
        next_action = state.get("next_action", "finish")
        decision = state.get("decision", {})

        # 记录路由决策
        logger.info(f"[路由] 选择下一步行动：{next_action}")
        logger.info(f"决策详情：{decision.get('reason', 'unknown')}")

        return next_action

    def process_request(self, request: Any) -> Dict[str, Any]:
        """
        处理用户请求的增强版本

        Args:
            request: 用户请求，可以是字符串或包含更多上下文的字典

        Returns:
            处理结果字典
        """
        logger.info(f"[Agent] 处理请求：{request}")

        # 如果 langgraph 不可用，返回警告信息
        if not LANGGRAPH_AVAILABLE:
            return {
                "status": "warning",
                "message": "LangGraph 不可用，返回简化结果",
                "answer": "这是一个简化的响应结果。要获得完整功能，请安装 langgraph 包。"
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
                "decision": {},
                "next_action": "",
                "current_step": 0,
                "iterations": 0,
                "history": [],
                "tool_call_history": [],
                "context_memory": {},
                "decision_trace": [],
                "max_iterations": self.config["max_iterations"],
                "convergence_criteria": {
                    "success_rate_threshold": self.config.get("convergence_threshold", 0.8),
                    "min_iterations": 1,
                    "max_iterations": self.config["max_iterations"]
                },
                "state": "initial"
            }
        else:
            # 处理简单字符串请求
            initial_state = {
                "query": str(request),
                "plan": [],
                "execution_result": {},
                "reflection": {},
                "decision": {},
                "next_action": "",
                "current_step": 0,
                "iterations": 0,
                "history": [],
                "tool_call_history": [],
                "context_memory": {},
                "decision_trace": [],
                "max_iterations": self.config["max_iterations"],
                "convergence_criteria": {
                    "success_rate_threshold": self.config.get("convergence_threshold", 0.8),
                    "min_iterations": 1,
                    "max_iterations": self.config["max_iterations"]
                },
                "state": "initial"
            }

        # 执行图计算
        result = self.graph(initial_state)

        # 保存到内存（如果启用了 memory）
        if self.memory:
            self.memory.save_interaction(
                initial_state["query"],
                result.get("execution_result", "")
            )

        # 应用结果格式化函数（如果有）
        if "result_formatter" in self.config.get("custom_handlers", {}):
            result = self.config["custom_handlers"]["result_formatter"](result)

        logger.info("[Agent] 请求处理完成")
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
