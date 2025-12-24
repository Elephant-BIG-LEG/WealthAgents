"""
财富Agent - 智能投研分析平台
私人Agent模块 - 规划器组件
实现任务规划和分解功能
"""
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
import re

"""
私人Agent任务规划期
TODO
修改规划、智能规划
"""

@dataclass
class Task:
    """任务数据类"""
    id: str
    name: str
    description: str
    tool_name: str
    parameters: Dict[str, Any]
    dependencies: List[str]  # 依赖的任务ID列表


class Planner:
    """任务规划器 - 负责将用户请求分解为可执行任务"""

    def __init__(self):
        self.task_counter = 0

    def plan(self, user_request: str, available_tools: List[str]) -> List[Task]:
        """
        根据用户请求和可用工具生成执行计划

        Args:
            user_request: 用户的请求描述
            available_tools: 可用工具列表

        Returns:
            任务列表，按执行顺序排列
        """
        # 分析用户请求，确定需要执行的步骤
        tasks = []

        # 简化的请求分析逻辑
        if any(keyword in user_request.lower() for keyword in ['分析', '趋势', '股票', '市场']):
            # 需要先采集数据
            if 'web_scraping' in available_tools:
                task_id = f"task_{self.task_counter}"
                self.task_counter += 1
                tasks.append(Task(
                    id=task_id,
                    name="数据采集",
                    description="从财经网站采集相关数据",
                    tool_name="web_scraping",
                    parameters={"query": self._extract_query(user_request)},
                    dependencies=[]
                ))

            # 然后分析数据
            if 'data_analysis' in available_tools:
                task_id = f"task_{self.task_counter}"
                self.task_counter += 1
                tasks.append(Task(
                    id=task_id,
                    name="数据分析",
                    description="分析采集到的数据",
                    tool_name="data_analysis",
                    parameters={
                        "previous_task_id": tasks[-1].id if tasks else None},
                    dependencies=[tasks[-1].id] if tasks else []
                ))

        elif any(keyword in user_request.lower() for keyword in ['新闻', '资讯', '热点']):
            # 新闻分析流程
            if 'news_analysis' in available_tools:
                task_id = f"task_{self.task_counter}"
                self.task_counter += 1
                tasks.append(Task(
                    id=task_id,
                    name="新闻分析",
                    description="分析财经新闻",
                    tool_name="news_analysis",
                    parameters={"query": self._extract_query(user_request)},
                    dependencies=[]
                ))

        elif any(keyword in user_request.lower() for keyword in ['风险', '评估', '风险评估']):
            # 风险评估流程
            if 'risk_assessment' in available_tools:
                task_id = f"task_{self.task_counter}"
                self.task_counter += 1
                tasks.append(Task(
                    id=task_id,
                    name="风险评估",
                    description="评估投资风险",
                    tool_name="risk_assessment",
                    parameters={"query": self._extract_query(user_request)},
                    dependencies=[]
                ))

        else:
            # 默认处理：使用通用分析工具
            if 'general_analysis' in available_tools:
                task_id = f"task_{self.task_counter}"
                self.task_counter += 1
                tasks.append(Task(
                    id=task_id,
                    name="通用分析",
                    description="通用分析任务",
                    tool_name="general_analysis",
                    parameters={"query": user_request},
                    dependencies=[]
                ))

        return tasks

    def _extract_query(self, user_request: str) -> str:
        """
        从用户请求中提取查询关键词

        Args:
            user_request: 用户请求文本

        Returns:
            提取的查询关键词
        """
        # 简化的关键词提取逻辑
        # 移除常见的询问词，保留核心关键词
        common_words = ['请', '帮我', '帮我分析', '帮我查询',
                        '我想知道', '如何', '怎么样', '什么', '哪个', '哪些']
        query = user_request.strip()

        for word in common_words:
            query = query.replace(word, '').strip()

        # 只保留中英文字符和数字
        query = re.sub(r'[^\w\s\u4e00-\u9fff]', ' ', query)
        query = ' '.join(query.split())  # 清理多余空格

        return query if query else user_request[:50]  # 如果处理后为空，返回原请求的前50个字符
