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
# 导入统一日志配置
from app.utils.log_config import setup_logger, get_logger, info, error, debug

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
        
        # 初始化可用工具字典
        self.available_tools = {}
        
        # 初始化执行器，传入可用工具字典
        self.executor = Executor(self.available_tools)
        self.reflector = Reflector(self.memory_manager)

        # 初始化日志
        self.logger = get_logger(__name__)

        # 动态加载所有工具
        self._load_all_tools()

    def _load_all_tools(self):
        """
        动态加载所有工具，并为每个工具提供详细的描述和参数说明
        """
        # 定义工具映射 - 包含详细的工具信息
        tool_configs = [
            {
                'name': 'web_scraping_tool',
                'module_path': 'app.agent.tools.web_scraping_tool',
                'function_name': 'web_scraping_tool',
                'description': '网络数据采集工具，用于从网络获取各类数据',
                'parameters': [{'name': 'query', 'type': 'str', 'description': '查询关键词'}]
            },
            {
                'name': 'data_analysis',
                'module_path': 'app.agent.tools.data_parsing_tool',
                'function_name': 'data_parsing_tool',
                'description': '数据解析工具，用于分析和处理金融文本数据',
                'params': {
                    'text': '要解析的文本内容',
                    '**kwargs': '其他可选参数，如解析配置等'
                },
                'usage': '适用于分析报告、新闻文章、公告等文本内容'
            },
            {
                'name': 'news_analysis',
                'module_path': 'app.agent.tools.data_summarization_tool',
                'function_name': 'data_summarization_tool',
                'description': '新闻分析工具，用于摘要和分析新闻内容',
                'params': {
                    'text': '要分析的新闻文本',
                    '**kwargs': '其他可选参数，如摘要长度等'
                },
                'usage': '适用于快速了解新闻要点和关键信息'
            },
            {
                'name': 'risk_assessment',
                'module_path': 'app.agent.tools.database_tool',
                'function_name': 'database_tool',
                'description': '风险评估工具，用于查询数据库中的风险相关数据',
                'params': {
                    'query': '查询语句或关键词',
                    '**kwargs': '其他可选参数，如数据库配置等'
                },
                'usage': '适用于风险分析和历史数据查询'
            },
            {
                'name': 'general_analysis',
                'module_path': 'app.agent.tools.data_parsing_tool',
                'function_name': 'data_parsing_tool',
                'description': '通用分析工具，用于处理各种类型的金融数据',
                'params': {
                    'text': '要分析的文本或数据',
                    '**kwargs': '其他可选参数，如分析配置等'
                },
                'usage': '适用于各种通用的数据分析场景'
            },
            {
                'name': 'knowledge_base_tool',
                'module_path': 'app.agent.tools.data_parsing_tool',
                'function_name': 'data_parsing_tool',
                'description': '知识库查询工具，用于检索和分析知识库中的信息',
                'params': {
                    'text': '查询关键词或问题',
                    '**kwargs': '其他可选参数，如检索配置等'
                },
                'usage': '适用于查询已有知识库中的专业知识'
            },
            {
                'name': 'general_query',
                'module_path': 'app.agent.tools.data_parsing_tool',
                'function_name': 'data_parsing_tool',
                'description': '通用查询工具，用于处理各种用户查询',
                'params': {
                    'text': '用户的查询内容',
                    '**kwargs': '其他可选参数，如查询配置等'
                },
                'usage': '适用于各种通用的用户查询场景'
            },
            {
                'name': 'summary_tool',
                'module_path': 'app.agent.tools.data_summarization_tool',
                'function_name': 'data_summarization_tool',
                'description': '总结工具，用于生成文本内容的摘要',
                'params': {
                    'text': '要总结的文本内容',
                    '**kwargs': '其他可选参数，如摘要长度等'
                },
                'usage': '适用于生成报告摘要、内容概述等'
            }
        ]

        for tool_config in tool_configs:
            try:
                # 动态导入工具模块
                module = importlib.import_module(
                    tool_config['module_path'], package='app.agent.tools')

                # 获取工具函数
                tool_func = getattr(module, tool_config['function_name'])

                # 注册工具到available_tools字典
                self.available_tools[tool_config['name']] = tool_func
                self.logger.info(f"工具 {tool_config['name']} 已从 {tool_config['module_path']} 加载并注册")
                self.logger.debug(f"工具描述: {tool_config['description']}")
                self.logger.debug(f"工具参数: {tool_config['params']}")

            except ImportError as e:
                self.logger.warning(f"无法导入工具模块 {tool_config['module_path']}: {e}")
            except AttributeError as e:
                self.logger.warning(f"工具模块 {tool_config['module_path']} 中未找到函数 {tool_config['function_name']}: {e}")
            except Exception as e:
                self.logger.error(f"加载工具 {tool_config['name']} 时出错: {e}")

    def process_request(self, user_request: str, session_id: Optional[str] = None) -> Dict[str, Any]:
        """
        处理用户请求的主入口
        
        新流程：
        1. 用户输入 → 2. 意图识别+任务拆解(轻量LLM) → 3. 路由决策(是否需要知识及类型) → 
        4. 知识获取(向量/SQL/搜索/工具) → 5. 上下文重组 → 6. 最终大模型生成 → 7. 后处理(格式/校验/记忆)
        
        Args:
            user_request: 用户的请求文本
            session_id: 会话ID，用于维持对话上下文
        
        Returns:
            包含处理结果的字典
        """
        try:
            # 1. 处理会话ID和初始化上下文
            if session_id is None:
                session_id = str(uuid.uuid4())
            
            self.logger.info("开始处理用户请求")
            
            # 获取当前会话上下文
            current_context = self.memory_manager.get_conversation_context(session_id) or {}
            conversation_history = current_context.get("conversation_history", [])
            
            # 2. 意图识别 + 任务拆解（轻量LLM）
            self.logger.info("开始意图识别和任务拆解")
            
            # 使用现有规划器进行意图识别和任务拆解
            planning_context = {
                "user_request": user_request,
                "previous_reflections": [],
                "adjustment_suggestions": []
            }
            
            # 调用规划器生成任务计划，这一步包含了意图识别
            tasks = self.planner.create_plan(
                user_request, 
                conversation_history, 
                planning_context
            )
            
            self.logger.info(f"意图识别和任务拆解完成，生成 {len(tasks)} 个任务")
            
            # 3. 路由决策（是否需要知识及类型）
            self.logger.info("开始路由决策")
            
            # 分析任务类型和所需知识类型
            knowledge_requirements = self._analyze_knowledge_requirements(tasks)
            
            # 4. 知识获取（向量/SQL/搜索/工具）
            self.logger.info("开始知识获取")
            
            # 执行任务获取知识
            task_results = []
            for task in tasks:
                try:
                    # 调用执行器执行单个任务
                    result = self.executor.execute_task(task)
                    task_results.append({
                        "task": task,
                        "result": result
                    })
                except Exception as e:
                    self.logger.error(f"执行任务 {task['name']} 失败: {str(e)}")
                    task_results.append({
                        "task": task,
                        "result": None,
                        "error": str(e)
                    })
            
            # 5. 上下文重组
            # 5. 上下文重组
            reorganized_context = self._reorganize_context(user_request, conversation_history, task_results)
            
            # 6. 最终大模型生成
            self.logger.info("开始最终大模型生成")
            try:
                # 使用response_generator生成最终回复
                response = response_generator.get_response(reorganized_context)
                self.logger.info("大模型生成完成")
            except Exception as e:
                self.logger.error(f"大模型生成失败: {str(e)}", exc_info=True)
                error(self.logger, "大模型生成失败", exception=str(e))
                # 如果生成失败，使用默认响应
                response = "抱歉，我在处理您的请求时遇到了一些问题。请稍后再试。"
            
            # 构建最终结果结构体
            final_result = {
                "status": "success",
                "tasks": task_results,
                "user_request": user_request,
                "session_id": session_id
            }
            
            # 使用ResponseGenerator生成最终响应
            final_result = response_generator.process_task_results(
                final_result, user_request, self.logger
            )
            
            self.logger.info("最终大模型生成完成")
            
            # 7. 后处理（格式/校验/记忆）
            self.logger.info("开始后处理")
            
            # 更新会话历史
            conversation_history.append({
                "user_message": user_request,
                "agent_response": final_result,
                "timestamp": time.time()
            })
            
            # 限制历史记录长度
            if len(conversation_history) > 20:
                conversation_history = conversation_history[-20:]
            
            # 保存最终会话上下文
            final_session_context = {
                "user_request": user_request,
                "execution_history": [
                    {
                        "tasks": tasks,
                        "results": task_results
                    }
                ],
                "final_result": final_result,
                "conversation_history": conversation_history
            }
            
            self.memory_manager.save_conversation_context(
                session_id, final_session_context
            )
            
            self.logger.info(f"请求处理完成，会话ID: {session_id}")
            return final_result
            
        except Exception as e:
            self.logger.error(f"处理请求时发生错误: {str(e)}", exc_info=True)
            return {
                "status": "error",
                "error_message": str(e),
                "session_id": session_id if 'session_id' in locals() else str(uuid.uuid4())
            }

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







    def _analyze_knowledge_requirements(self, tasks: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        路由决策：分析任务所需的知识类型和来源
        
        Args:
            tasks: 任务列表
            
        Returns:
            知识需求分析结果，包含需要的知识类型和来源
        """
        knowledge_requirements = {
            "needs_knowledge": False,
            "knowledge_types": [],  # vector, sql, search, tool
            "vector_queries": [],
            "sql_queries": [],
            "search_queries": [],
            "tool_calls": []
        }
        
        for task in tasks:
            tool_name = task.get("tool_name", "")
            
            if tool_name in ["knowledge_base_tool", "summary_tool"]:
                knowledge_requirements["needs_knowledge"] = True
                knowledge_requirements["knowledge_types"].append("vector")
                knowledge_requirements["vector_queries"].append(task.get("params", {}).get("query", ""))
            
            elif tool_name in ["database_tool", "data_analysis"]:
                knowledge_requirements["needs_knowledge"] = True
                knowledge_requirements["knowledge_types"].append("sql")
                knowledge_requirements["sql_queries"].append(task.get("params", {}).get("search_keyword", ""))
            
            elif tool_name in ["web_scraping_tool", "news_analysis"]:
                knowledge_requirements["needs_knowledge"] = True
                knowledge_requirements["knowledge_types"].append("search")
                knowledge_requirements["search_queries"].append(task.get("params", {}).get("query", ""))
            
            elif tool_name in self.available_tools:
                knowledge_requirements["needs_knowledge"] = True
                knowledge_requirements["knowledge_types"].append("tool")
                knowledge_requirements["tool_calls"].append({
                    "tool_name": tool_name,
                    "params": task.get("params", {})
                })
        
        # 去重知识类型
        knowledge_requirements["knowledge_types"] = list(set(knowledge_requirements["knowledge_types"]))
        
        self.logger.info(f"知识需求分析完成: {knowledge_requirements}")
        return knowledge_requirements
    
    def _reorganize_context(self, user_request: str, conversation_history: List[Dict[str, Any]], 
                           task_results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        上下文重组：将用户请求、对话历史和任务结果整合为统一的上下文
        
        Args:
            user_request: 用户原始请求
            conversation_history: 对话历史
            task_results: 任务执行结果
            
        Returns:
            重组后的上下文
        """
        # 收集所有任务的有效结果
        valid_results = []
        for task_result in task_results:
            if task_result["result"] and task_result["result"].get("status") == "success":
                valid_results.append(task_result)
        
        # 构建上下文结构
        reorganized_context = {
            "user_request": user_request,
            "conversation_history": conversation_history,
            "task_results": valid_results,
            "timestamp": time.time(),
            "result_summary": {
                "total_tasks": len(task_results),
                "successful_tasks": len(valid_results),
                "failed_tasks": len(task_results) - len(valid_results)
            }
        }
        
        # 提取关键信息
        extracted_info = []
        for task_result in valid_results:
            result_data = task_result["result"]
            task_name = task_result["task"].get("name", "未知任务")
            
            # 根据工具类型提取不同格式的结果
            if "parsed_data" in result_data:
                extracted_info.append({
                    "task_name": task_name,
                    "type": "parsed_data",
                    "content": result_data["parsed_data"]
                })
            elif "data" in result_data:
                extracted_info.append({
                    "task_name": task_name,
                    "type": "raw_data",
                    "content": result_data["data"]
                })
            elif "summary" in result_data:
                extracted_info.append({
                    "task_name": task_name,
                    "type": "summary",
                    "content": result_data["summary"]
                })
            else:
                extracted_info.append({
                    "task_name": task_name,
                    "type": "other",
                    "content": result_data
                })
        
        reorganized_context["extracted_info"] = extracted_info
        
        self.logger.info(f"上下文重组完成，提取了 {len(extracted_info)} 条关键信息")
        return reorganized_context