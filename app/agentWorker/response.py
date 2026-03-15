from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import JsonOutputParser
import dotenv
from langchain_openai import ChatOpenAI
import os
import logging
from typing import Dict, List, Any, Optional

dotenv.load_dotenv()
logger = logging.getLogger(__name__)

"""
利用大模型来处理任务结果，生成友好的用户回答
将多个任务的结果整合成自然、连贯的用户回复
"""


class ResponseGenerator:
    def __init__(self, model="qwen-plus"):
        # 初始化模型和提示模板
        self.llm = ChatOpenAI(
            model=model,
            base_url=os.getenv("DASHSCOPE_BASE_URL"),
            api_key=os.getenv("DASHSCOPE_API_KEY")
        )

        # 创建提示模板，要求将任务结果整合成友好回答
        self.prompt = ChatPromptTemplate.from_messages([
            (
                "system",
                "你是一位专业的金融助手，负责将多个任务的执行结果整合成自然、友好、连贯的用户回答。"
                "请基于提供的任务结果，为用户的问题生成一个全面而简洁的回复。"
            ),
            (
                "user",
                """
                请根据以下任务执行结果，为用户提供一个自然、友好、连贯的回答。
                
                用户的原始问题是：{user_request}
                
                任务执行结果：
                {task_outputs}
                
                请以自然语言形式回答，不要添加额外的信息，也不要进行不必要的评论。
                """
            )
        ])

        # 使用Json输出解析器（虽然我们主要需要文本输出，但保持与其他文件一致的模式）
        self.output_parser = JsonOutputParser()
        # 构建链
        self.chain = self.prompt | self.llm

    def collect_task_outputs(self, tasks: List[Dict[str, Any]]) -> List[str]:
        """
        从任务列表中收集成功任务的结果文本，去除重复内容

        参数：
        - tasks (List[Dict]): 任务列表

        返回：
        - List[str]: 收集到的任务输出文本列表
        """
        task_outputs = []
        seen_contents = set()  # 用于跟踪已见过的任务内容，实现去重

        for task in tasks:
            try:
                # 检查任务状态和结果格式
                # 任务结构可能是直接包含结果，或者是执行器返回的完整结果
                task_result_data = None

                if "result" in task and isinstance(task["result"], dict):
                    # 情况1：直接在task["result"]中包含结果
                    if "parsed_data" in task["result"]:
                        task_result_data = task["result"]
                    # 情况2：执行器返回的格式，实际结果在task["result"]["result"]中
                    elif "result" in task["result"] and isinstance(task["result"]["result"], dict):
                        task_result_data = task["result"]["result"]
                    # 情况3：web_scraping_tool直接返回的结果格式
                    elif "status" in task["result"] and "data" in task["result"]:
                        task_result_data = task["result"]

                if task_result_data:
                    # 处理不同工具的返回格式
                    if "parsed_data" in task_result_data:
                        # 处理标准parsed_data格式
                        data_items = task_result_data["parsed_data"]
                        content_field = "summary"  # 默认使用summary字段
                    elif "data" in task_result_data and task_result_data["status"] == "success":
                        # 处理web_scraping_tool返回的data格式
                        data_items = task_result_data["data"]
                        content_field = "content"  # web_scraping_tool使用content字段
                    else:
                        # 不支持的格式，跳过
                        continue

                    # 确保data_items是列表格式
                    if not isinstance(data_items, list):
                        data_items = [data_items]

                    # 处理数据项列表
                    for item in data_items:
                        if isinstance(item, dict) and "title" in item:
                            # 获取内容字段，优先使用content_field，否则尝试其他可能的字段
                            content = item.get(content_field, item.get("summary", item.get("content", "")))
                            
                            # 创建任务内容的唯一标识符（基于标题和内容的组合）
                            content_identifier = f"{item['title']}|{content[:100]}"  # 使用前100个字符作为标识

                            # 检查是否已存在相同内容的任务结果
                            if content_identifier not in seen_contents:
                                seen_contents.add(content_identifier)
                                # 使用统一的格式添加任务输出
                                task_outputs.append(
                                    f"标题: {item['title']}\n内容: {content}")
                                logger.debug(f"添加任务输出: {item['title']}")
                            else:
                                logger.debug(f"跳过重复任务结果: {item['title']}")
            except Exception as e:
                logger.debug(f"收集任务输出时出错: {str(e)}")
                continue

        return task_outputs

    def get_response(self, user_input: Dict[str, Any]) -> Dict[str, Any]:
        """
        给定用户输入，返回处理后的响应。

        参数：
        - user_input (Dict): 包含final_result和user_request的字典
            - final_result: 包含任务结果的最终数据字典
            - user_request: 用户的原始请求
            - logger_instance: 可选的日志记录器实例

        返回：
        - Dict: 处理后的结果字典，包含response字段
        """
        try:
            # 提取输入参数
            final_result = user_input.get("final_result", {})
            user_request = user_input.get("user_request", "")
            logger_instance = user_input.get("logger_instance", logger)

            # 收集任务输出
            task_outputs = self.collect_task_outputs(
                final_result.get("tasks", []))

            if task_outputs:
                logger_instance.info(f"成功收集到 {len(task_outputs)} 个任务结果，开始生成响应")

                # 构建任务输出文本
                task_outputs_text = "\n\n".join(task_outputs)

                # 调用链生成响应
                response_content = self.chain.invoke({
                    "user_request": user_request,
                    "task_outputs": task_outputs_text
                })

                # 提取内容（从AIMessage对象中）
                llm_response = response_content.content if hasattr(
                    response_content, 'content') else str(response_content)
                final_result["response"] = llm_response
            else:
                # 无任务结果时的默认响应
                final_result["response"] = f"关于您的问题 '{user_request}'，我未能找到相关信息。请尝试提供更具体的问题或关键词，以便我能更好地为您服务。"
                logger_instance.info("未收集到任务结果，使用默认响应")

            return final_result

        except Exception as e:
            logger.error(f"处理任务结果时发生错误: {str(e)}")
            # 错误情况下的安全响应
            final_result = user_input.get("final_result", {})
            final_result["response"] = "我已完成任务执行，但在生成回答时遇到了技术问题。请稍后再试或提供更具体的问题。"
            return final_result

    def process_task_results(self, final_result: Dict[str, Any],
                             user_request: str,
                             logger_instance: Optional[logging.Logger] = None) -> Dict[str, Any]:
        """
        处理任务结果的便捷方法

        参数：
        - final_result: 包含任务结果的最终数据字典
        - user_request: 用户的原始请求
        - logger_instance: 可选的日志记录器实例

        返回：
        - 更新后的final_result字典，包含生成的响应
        """
        return self.get_response({
            "final_result": final_result,
            "user_request": user_request,
            "logger_instance": logger_instance
        })


# 创建全局实例供外部直接使用
response_generator = ResponseGenerator()
