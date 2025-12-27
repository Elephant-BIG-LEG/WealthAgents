"""
财富Agent - 智能投研分析平台
私人Agent模块 - 私人Agent主类
整合Plan → Act → Reflect决策闭环
TODO
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
# 导入response_generator
from app.agentWorker.response import response_generator

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
            'general_analysis': 'app.agent.tools.data_parsing_tool',
            'knowledge_base_tool': 'app.agent.tools.data_parsing_tool',  # 添加知识库工具
            'general_query': 'app.agent.tools.data_parsing_tool',  # 添加通用查询工具
            'summary_tool': 'app.agent.tools.data_summarization_tool'  # 添加总结工具
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
                elif tool_name == 'knowledge_base_tool':
                    # 对于知识库工具，我们可以复用data_parsing_tool功能
                    tool_func = getattr(module, 'data_parsing_tool')
                elif tool_name == 'general_query':
                    # 对于通用查询工具，使用数据解析工具
                    tool_func = getattr(module, 'data_parsing_tool')
                elif tool_name == 'summary_tool':
                    # 对于总结工具，使用数据总结工具
                    tool_func = getattr(module, 'data_summarization_tool')

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
        处理用户请求 - Plan → Act → Reflect 完整流程 (Iterative Loop)

        Args:
            user_request: 用户请求
            session_id: 会话ID（可选）

        Returns:
            处理结果
        """
        if session_id is None:
            session_id = str(uuid.uuid4())

        self.logger.info(f"开始处理用户请求 (会话ID: {session_id}): {user_request}")

        max_iterations = 3
        current_iteration = 0
        final_result = None

        # 记录每轮执行的状态
        execution_history = []

        while current_iteration < max_iterations:
            current_iteration += 1
            self.logger.info(f"进入第 {current_iteration} 轮处理循环")

            # 1. Plan (规划阶段)
            self.logger.info("开始规划阶段")
            available_tools = list(self.executor.tools.keys())
            # 获取对话历史上下文
            conversation_context_dict = self.memory_manager.get_conversation_context(
                session_id) or {}
            # 确保传递给create_plan的是列表格式的对话上下文
            # 如果返回的是字典，从中提取conversation_history字段或使用空列表
            conversation_context = conversation_context_dict.get(
                "conversation_history", [])
            # 使用真实的对话上下文作为参数
            tasks = self.planner.create_plan(
                user_request, conversation_context)

            self.logger.info(
                f"生成 {len(tasks)} 个任务: {[task['name'] for task in tasks]}")

            # 2. Act (执行阶段)
            self.logger.info("开始执行阶段")
            try:
                task_results = self.executor.execute_plan(tasks)
                self.logger.info("执行阶段完成")
            except Exception as e:
                self.logger.error(f"执行阶段失败: {str(e)}")
                # 如果执行过程抛出严重异常，终止循环
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
            self.reflector.update_planning_strategy(
                plan_reflection, user_request)

            # 记录本轮执行情况
            current_round_result = {
                "iteration": current_iteration,
                "tasks": tasks,
                "task_results": task_results,
                "plan_reflection": plan_reflection
            }
            execution_history.append(current_round_result)

            # 4. Decide (决策阶段)
            # 决定下一步行动
            decision = self.reflector.decide_next_step(
                plan_reflection, max_iterations, current_iteration)
            self.logger.info(f"决策结果: {decision}")

            if decision['action'] == 'FINISH':
                self.logger.info(f"任务完成，原因: {decision['reason']}")
                break
            elif decision['action'] == 'RETRY':
                self.logger.info(f"准备重试，原因: {decision['reason']}")
                # 简单延时后重试
                time.sleep(1)
                continue
            else:
                self.logger.info("未知决策，默认结束")
                break

        # 整理最终结果（使用最后一轮的结果）
        last_round = execution_history[-1]
        last_tasks = last_round['tasks']
        last_results = last_round['task_results']
        last_reflection = last_round['plan_reflection']

        # 生成最终响应
        final_result = {
            "status": "success",
            "session_id": session_id,
            "user_request": user_request,
            "iterations": len(execution_history),
            "task_count": sum(len(h["tasks"]) for h in execution_history),
            "successful_tasks": sum(
                1 for h in execution_history for result in h["task_results"]
                if result.get("status") == "success"
            ),
            "tasks": [
                {
                    "id": task["id"],
                    "name": task["name"],
                    "description": task.get("description", ""),
                    "tool_used": task["tool_name"],
                    "result": h["task_results"][i],
                    "execution_time": h["task_results"][i].get("execution_time", 0),
                    "status": "success" if h["task_results"][i].get("status") == "success" else "failed"
                }
                for h in execution_history
                for i, task in enumerate(h["tasks"])
            ],
            "plan_reflection": execution_history[-1]["plan_reflection"],
            "timestamp": time.time(),
            "response": "科技股推荐信息已处理完成。由于本地知识库检索未能获取到有效数据，请尝试更具体的查询，如'推荐2023年增长最快的5支科技股'或指定特定领域的科技股。"
        }

        # 使用新的response_generator处理最终结果
        try:
            self.logger.info("开始使用response_generator处理任务结果")
            final_result = response_generator.process_task_results(
                final_result, user_request, self.logger)
            self.logger.info("response_generator处理完成")
        except Exception as e:
            self.logger.error(f"response_generator处理失败: {str(e)}")
            # 如果处理失败，保持原有的默认响应
            final_result["response"] = "科技股推荐信息已处理完成。由于本地知识库检索未能获取到有效数据，请尝试更具体的查询，如'推荐2023年增长最快的5支科技股'或指定特定领域的科技股。"

        # 保存会话上下文
        session_context = {
            "user_request": user_request,
            "execution_history": [
                {
                    "iteration": h["iteration"],
                    "tasks": h["tasks"],
                    "results": h["task_results"],
                    "plan_reflection": h["plan_reflection"]
                } for h in execution_history
            ],
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

        # 检查是否response_generator已经生成了响应
        if result.get("response") and result["response"] != "科技股推荐信息已处理完成。由于本地知识库检索未能获取到有效数据，请尝试更具体的查询，如'推荐2023年增长最快的5支科技股'或指定特定领域的科技股。":
            # 使用response_generator生成的响应
            ai_response = result["response"]
        else:
            # 准备返回给前端的响应 - 原有逻辑作为后备
            if result["status"] == "success":
                # 提取有用的信息作为AI的回复
                ai_response_parts = []

                for task in result["tasks"]:
                    if task["result"]:
                        task_result = task["result"]
                        if isinstance(task_result, dict):
                            # 尝试获取自然语言描述字段
                            content = task_result.get("summary") or \
                                task_result.get("analysis") or \
                                task_result.get("conclusion") or \
                                task_result.get("market_summary") or \
                                task_result.get("investment_advice")

                            if content:
                                if isinstance(content, dict):
                                    # 处理字典格式的内容
                                    title = content.get("title", "")
                                    summary_text = content.get(
                                        "summary", "") or content.get("content", "")
                                    if title or summary_text:
                                        formatted_content = ""
                                        if title:
                                            formatted_content += f"**{title}**<br>"
                                        formatted_content += str(summary_text)
                                        ai_response_parts.append(
                                            formatted_content)
                                else:
                                    ai_response_parts.append(str(content))
                            elif "parsed_data" in task_result:
                                parsed = task_result["parsed_data"]
                                if isinstance(parsed, list):
                                    items = []
                                    for item in parsed:
                                        if isinstance(item, dict):
                                            item_str = item.get('content') or item.get(
                                                'summary') or str(item)
                                            items.append(item_str)
                                        else:
                                            items.append(str(item))
                                    ai_response_parts.append(
                                        "<br>".join(items))
                                else:
                                    ai_response_parts.append(str(parsed))
                            elif "data" in task_result:
                                data_val = task_result["data"]
                                if isinstance(data_val, str):
                                    ai_response_parts.append(data_val)
                                elif isinstance(data_val, list):
                                    if not data_val:
                                        source = task_result.get(
                                            "source", "数据源")
                                        query = task_result.get(
                                            "query", "未知查询")
                                        ai_response_parts.append(
                                            f"从 {source} 未找到关于 '{query}' 的相关数据。")
                                    else:
                                        ai_response_parts.append(
                                            f"找到 {len(data_val)} 条相关数据。")
                                else:
                                    ai_response_parts.append(str(data_val))
                            else:
                                # 最后的兜底，尝试格式化字典
                                # 如果字典中包含 title 和 summary 且都为空，忽略
                                if "title" in task_result and "summary" in task_result and not task_result["title"] and not task_result["summary"]:
                                    continue
                                ai_response_parts.append(str(task_result))
                        else:
                            ai_response_parts.append(str(task_result))

                ai_response = "<br><br>".join(
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
