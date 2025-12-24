"""
财富Agent - 智能投研分析平台
私人Agent模块 - 私人Agent主类
整合Plan → Act → Reflect决策闭环
TODO 修改私人Agent前端响应结果
"""
from typing import Dict, Any, List, Optional
from .planner import Planner, Task
from .executor import Executor
from .reflector import Reflector
from .memory import MemoryManager
import logging
import uuid
import time
import importlib

"""
私人Agent - 实现Plan → Act → Reflect决策闭环
TODO
集合各大功能组件
修改执行逻辑

"""

class PrivateAgent:
    """私人Agent - 实现Plan → Act → Reflect决策闭环"""

    def __init__(self):
        # 初始化记忆管理器
        self.memory_manager = MemoryManager()

        # 初始化各组件
        self.planner = Planner()
        self.executor = Executor(self.memory_manager)
        self.reflector = Reflector(self.memory_manager)

        # 初始化日志
        self.logger = logging.getLogger(__name__)

        # 动态加载所有工具
        self._load_all_tools()

    def _load_all_tools(self):
        """动态加载所有工具"""
        # 定义工具映射
        tool_modules = {
            'web_scraping': 'app.agent.tools.web_scraping_tool',
            'data_analysis': 'app.agent.tools.data_parsing_tool',
            'news_analysis': 'app.agent.tools.data_summarization_tool',
            'risk_assessment': 'app.agent.tools.database_tool',
            'general_analysis': 'app.agent.tools.data_parsing_tool'
        }

        for tool_name, module_path in tool_modules.items():
            try:
                # 动态导入工具模块
                module = importlib.import_module(
                    module_path, package='app.agent.tools')

                # 获取工具函数
                if tool_name == 'web_scraping':
                    tool_func = getattr(module, 'web_scraping_tool')
                elif tool_name == 'data_analysis':
                    tool_func = getattr(module, 'data_parsing_tool')
                elif tool_name == 'news_analysis':
                    tool_func = getattr(module, 'data_summarization_tool')
                elif tool_name == 'risk_assessment':
                    tool_func = getattr(module, 'database_tool')
                elif tool_name == 'general_analysis':
                    tool_func = getattr(module, 'data_parsing_tool')

                # 注册工具
                self.executor.register_tool(tool_name, tool_func)
                self.logger.info(f"工具 {tool_name} 已从 {module_path} 加载并注册")

            except ImportError as e:
                self.logger.warning(f"无法导入工具模块 {module_path}: {e}")
            except AttributeError as e:
                self.logger.warning(f"工具模块 {module_path} 中未找到相应函数: {e}")
            except Exception as e:
                self.logger.error(f"加载工具 {tool_name} 时出错: {e}")

    def process_request(self, user_request: str, session_id: Optional[str] = None) -> Dict[str, Any]:
        """
        处理用户请求 - Plan → Act → Reflect 完整流程

        Args:
            user_request: 用户请求
            session_id: 会话ID（可选）

        Returns:
            处理结果
        """
        if session_id is None:
            session_id = str(uuid.uuid4())

        self.logger.info(f"开始处理用户请求 (会话ID: {session_id}): {user_request}")

        # 1. Plan (规划阶段)
        self.logger.info("开始规划阶段")
        available_tools = list(self.executor.tools.keys())
        tasks = self.planner.plan(user_request, available_tools)

        self.logger.info(
            f"生成 {len(tasks)} 个任务: {[task.name for task in tasks]}")

        # 2. Act (执行阶段)
        # TODO 修改执行阶段
        self.logger.info("开始执行阶段")
        try:
            task_results = self.executor.execute_plan(tasks)
            self.logger.info("执行阶段完成")
        except Exception as e:
            self.logger.error(f"执行阶段失败: {str(e)}")
            return {
                "status": "error",
                "error_message": str(e),
                "session_id": session_id,
                "timestamp": time.time()
            }

        # 3. Reflect (反思阶段)
        self.logger.info("开始反思阶段")

        # 反思每个任务
        task_reflections = []
        for i, task in enumerate(tasks):
            reflection = self.reflector.reflect_on_task_execution(
                task, task_results[i])
            task_reflections.append(reflection)

        # 反思整个计划
        plan_reflection = self.reflector.reflect_on_plan_execution(
            tasks, task_results)

        # 根据反思结果更新策略
        self.reflector.update_planning_strategy(plan_reflection, user_request)

        # 4. 整理最终结果
        final_result = {
            "status": "success",
            "session_id": session_id,
            "user_request": user_request,
            "task_count": len(tasks),
            "successful_tasks": len([r for r in task_results if r.get('status') == 'success']),
            "tasks": [
                {
                    "id": task.id,
                    "name": task.name,
                    "description": task.description,
                    "tool_used": task.tool_name,
                    "result": result.get('result'),
                    "execution_time": result.get('execution_time'),
                    "status": result.get('status')
                }
                for task, result in zip(tasks, task_results)
            ],
            "plan_reflection": {
                "success_rate": plan_reflection.get('success_rate'),
                "total_execution_time": plan_reflection.get('total_execution_time'),
                "overall_evaluation": plan_reflection.get('overall_evaluation'),
                "improvements": plan_reflection.get('system_improvements'),
                "learning_points": plan_reflection.get('learning_points')
            },
            "timestamp": time.time()
        }

        # 保存会话上下文
        session_context = {
            "user_request": user_request,
            "tasks": [task.__dict__ for task in tasks],
            "results": task_results,
            "reflections": task_reflections,
            "plan_reflection": plan_reflection,
            "final_result": final_result
        }

        self.memory_manager.save_conversation_context(
            session_id, session_context)

        self.logger.info(f"请求处理完成，会话ID: {session_id}")
        return final_result

    def chat(self, user_message: str, session_id: Optional[str] = None) -> Dict[str, Any]:
        """
        聊天接口 - 为前端对话界面提供服务

        Args:
            user_message: 用户消息
            session_id: 会话ID（可选）

        Returns:
            聊天响应
        """
        if session_id is None:
            session_id = str(uuid.uuid4())

        # 获取当前会话上下文
        context_obj = self.memory_manager.get_conversation_context(session_id)
        if context_obj is None:
            conversation_history = []
        else:
            conversation_history = context_obj.get("conversation_history", [])

        # 处理用户请求
        result = self.process_request(user_message, session_id)

        # 更新会话历史
        conversation_history.append({
            "user_message": user_message,
            "agent_response": result,
            "timestamp": time.time()
        })

        # 限制历史记录长度，避免内存占用过多
        if len(conversation_history) > 20:  # 保留最近20条记录
            conversation_history = conversation_history[-20:]

        # 保存更新后的会话上下文
        session_data = {
            "conversation_history": conversation_history,
            "last_update": time.time()
        }

        # 更新 memory
        self.memory_manager.save_conversation_context(session_id, session_data)

        # 准备返回给前端的响应
        if result["status"] == "success":
            # 提取有用的信息作为AI的回复
            ai_response_parts = []

            for task in result["tasks"]:
                if task["result"]:
                    task_result = task["result"]
                    if isinstance(task_result, dict):
                        if "summary" in task_result:
                            ai_response_parts.append(task_result["summary"])
                        elif "parsed_data" in task_result:
                            ai_response_parts.append(
                                str(task_result["parsed_data"]))
                        elif "data" in task_result and isinstance(task_result["data"], str):
                            ai_response_parts.append(task_result["data"])
                        elif "analysis" in task_result:
                            ai_response_parts.append(task_result["analysis"])
                        else:
                            ai_response_parts.append(str(task_result))
                    else:
                        ai_response_parts.append(str(task_result))

            ai_response = "；".join(
                ai_response_parts) if ai_response_parts else "分析完成，未获得具体结果。"
        else:
            ai_response = f"处理请求时出现错误: {result.get('error_message', '未知错误')}"

        return {
            "status": "success",
            "session_id": session_id,
            "response": ai_response,
            "detailed_result": result,
            "timestamp": time.time()
        }

    def register_tool(self, name: str, tool_func):
        """
        注册新工具

        Args:
            name: 工具名称
            tool_func: 工具函数
        """
        self.executor.register_tool(name, tool_func)
        self.logger.info(f"新工具已注册: {name}")

    def get_available_tools(self) -> List[str]:
        """
        获取可用工具列表

        Returns:
            可用工具名称列表
        """
        return list(self.executor.tools.keys())

    def get_session_history(self, session_id: str) -> Optional[List[Dict[str, Any]]]:
        """
        获取会话历史

        Args:
            session_id: 会话ID

        Returns:
            会话历史列表
        """
        context = self.memory_manager.get_conversation_context(session_id)
        if context:
            return context.get("conversation_history", [])
        return None
