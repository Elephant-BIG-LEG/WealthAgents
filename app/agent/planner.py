"""
财富Agent - 智能投研分析平台
私人Agent模块 - 规划器组件
实现任务规划和分解功能
TODO 将用户的话翻译成Plan
"""
from typing import Dict, List, Any, Tuple
from dataclasses import dataclass
import string
from datetime import datetime

# 导入知识库和向量化相关组件
from app.Embedding.Vectorization import TextVectorizer
from app.store.faiss_store import FaissVectorStore


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
        # 初始化向量化器和知识库
        self.vectorizer = TextVectorizer(vector_dim=128)
        try:
            self.vector_store = FaissVectorStore(dimension=128)
            print(f"知识库初始化完成，包含 {self.vector_store.get_vector_count()} 条向量数据")
        except Exception as e:
            print(f"知识库初始化失败: {str(e)}")
            self.vector_store = None

        # 定义任务类型关键词
        self.task_type_keywords = {
            'data_collection': ['收集', '采集', '获取', '下载', '抓取', '搜集'],
            'data_analysis': ['分析', '趋势', '走势', '对比', '统计', '预测', '评估'],
            'market_research': ['市场', '行业', '板块', '产业链', '竞争格局', '市场份额'],
            'stock_analysis': ['股票', '股价', '行情', 'A股', '港股', '美股', '指数'],
            'news_analysis': ['新闻', '资讯', '热点', '报道', '事件', '动态'],
            'risk_assessment': ['风险', '评估', '预警', '隐患', '不确定', '波动性'],
            'investment_advice': ['建议', '推荐', '投资策略', '配置', '买入', '卖出'],
            'general_query': ['查询', '什么', '如何', '是否', '为什么', '解释', '含义']
        }

    def create_plan(self, user_query: str, context: List[Dict[str, Any]], planning_context: Dict[str, Any] = None) -> List[Dict[str, Any]]:
        """
        增强版任务规划方法，支持多轮对话、知识库匹配和智能任务类型识别
        新增: 支持从planning_context中获取之前的反思结果和调整建议

        Args:
            user_query: 用户查询
            context: 上下文历史列表，包含之前的对话记录
            planning_context: 规划上下文，包含之前的反思结果和调整建议

        Returns:
            任务计划列表，适配LangGraphAgent的调用方式
        """
        # 初始化返回的计划列表
        plan = []
        
        # 如果没有提供planning_context，初始化一个空字典
        if planning_context is None:
            planning_context = {
                "user_request": user_query,
                "previous_reflections": [],
                "adjustment_suggestions": []
            }

        # 分析任务类型和对话阶段
        task_type = self._analyze_task_type(user_query, context)
        conversation_stage = self._detect_conversation_stage(context)

        print(f"分析结果 - 任务类型: {task_type}, 对话阶段: {conversation_stage}")

        # 获取推荐的工具列表
        recommended_tools = self._get_available_tools(task_type)
        
        # 检查是否有调整建议，根据建议优化推荐工具
        adjustment_suggestions = planning_context.get("adjustment_suggestions", [])
        if adjustment_suggestions:
            print(f"应用调整建议: {adjustment_suggestions}")
            # 根据调整建议过滤或优先选择工具
            for suggestion in adjustment_suggestions:
                if '工具' in suggestion:
                    # 如果建议提到了特定工具，确保该工具在推荐列表中
                    for tool in recommended_tools:
                        if tool in suggestion:
                            # 将提到的工具移到列表首位
                            recommended_tools.remove(tool)
                            recommended_tools.insert(0, tool)
                            break

        # 1. 首先尝试从知识库检索相关信息
        knowledge_base_results = self._retrieve_from_knowledge_base(user_query)

        # 根据对话阶段和知识库结果选择不同的处理策略
        if conversation_stage == 'initial':
            # 初始查询阶段
            if knowledge_base_results:
                # 如果知识库有相关信息，先使用知识库信息处理
                task_id = f"task_{self.task_counter}"
                self.task_counter += 1
                plan.append({
                    "id": task_id,
                    "name": "知识库检索",
                    "description": "从本地知识库检索相关信息",
                    "tool_name": "knowledge_base_tool",
                    "parameters": {
                        "query": user_query,
                        # 传递最相关的前2条结果
                        "search_results": knowledge_base_results[:2]
                    },
                    "dependencies": [],
                    "task_type": task_type
                })

                # 根据任务类型添加后续处理任务
                if task_type in ['data_analysis', 'stock_analysis',
                                 'market_research'] and 'data_analysis' in recommended_tools:
                    task_id = f"task_{self.task_counter}"
                    self.task_counter += 1
                    plan.append({
                        "id": task_id,
                        "name": "深度数据分析",
                        "description": f"对{user_query}进行深度数据分析",
                        "tool_name": "data_analysis",
                        "parameters": {
                            "query": user_query,
                            "previous_task_id": plan[0]["id"]
                        },
                        "dependencies": [plan[0]["id"]],
                        "task_type": task_type
                    })
            else:
                # 知识库没有相关信息，使用网络搜索或数据库查询
                if task_type in ['data_collection', 'market_research'] and 'web_scraping_tool' in recommended_tools:
                    task_id = f"task_{self.task_counter}"
                    self.task_counter += 1
                    plan.append({
                        "id": task_id,
                        "name": "网络数据采集",
                        "description": f"从网络采集关于{user_query}的数据",
                        "tool_name": "web_scraping_tool",
                        "parameters": {
                            "query": user_query,
                            "search_type": task_type
                        },
                        "dependencies": [],
                        "task_type": task_type
                    })
                elif 'database_tool' in recommended_tools:
                    # 尝试从数据库查询
                    task_id = f"task_{self.task_counter}"
                    self.task_counter += 1
                    plan.append({
                        "id": task_id,
                        "name": "数据库查询",
                        "description": f"从本地数据库查询关于{user_query}的信息",
                        "tool_name": "database_tool",
                        "parameters": {
                            "query_params": {
                                "table": "RecentHotTopics",
                                "conditions": {}
                            },
                            "search_keyword": user_query
                        },
                        "dependencies": [],
                        "task_type": task_type
                    })
                else:
                    # 使用通用查询作为后备
                    task_id = f"task_{self.task_counter}"
                    self.task_counter += 1
                    plan.append({
                        "id": task_id,
                        "name": "通用查询处理",
                        "description": f"处理关于{user_query}的查询",
                        "tool_name": "general_query",
                        "parameters": {
                            "query": user_query,
                            "context_summary": self._summarize_context(context)
                        },
                        "dependencies": [],
                        "task_type": task_type
                    })

        elif conversation_stage == 'follow_up':
            # 跟进问题阶段
            if knowledge_base_results:
                # 使用知识库结果回答跟进问题
                task_id = f"task_{self.task_counter}"
                self.task_counter += 1
                plan.append({
                    "id": task_id,
                    "name": "知识库跟进查询",
                    "description": "基于之前的对话从知识库检索更多信息",
                    "tool_name": "knowledge_base_tool",
                    "parameters": {
                        "query": user_query,
                        "search_results": knowledge_base_results,
                        "context_summary": self._summarize_context(context)
                    },
                    "dependencies": [],
                    "task_type": task_type
                })
            else:
                # 使用之前结果的延伸查询
                task_id = f"task_{self.task_counter}"
                self.task_counter += 1
                plan.append({
                    "id": task_id,
                    "name": "跟进问题处理",
                    "description": "处理用户的跟进问题",
                    "tool_name": "general_query",
                    "parameters": {
                        "query": user_query,
                        "context_summary": self._summarize_context(context),
                        "follow_up": True
                    },
                    "dependencies": [],
                    "task_type": task_type
                })

        elif conversation_stage == 'clarification':
            # 澄清问题阶段，直接使用通用查询处理
            task_id = f"task_{self.task_counter}"
            self.task_counter += 1
            plan.append({
                "id": task_id,
                "name": "概念解释",
                "description": "解释用户询问的概念或术语",
                "tool_name": "general_query",
                "parameters": {
                    "query": user_query,
                    "clarification": True
                },
                "dependencies": [],
                "task_type": "general_query"
            })

        elif conversation_stage == 'summary':
            # 总结阶段
            task_id = f"task_{self.task_counter}"
            self.task_counter += 1
            plan.append({
                "id": task_id,
                "name": "对话总结",
                "description": "总结之前的对话内容和分析结果",
                "tool_name": "summary_tool",
                "parameters": {
                    "query": user_query,
                    "full_context": context,
                    "time_range": "recent"  # 最近的对话
                },
                "dependencies": [],
                "task_type": "general_query"
            })

        # 2. 根据任务类型添加必要的额外任务
        if task_type == 'risk_assessment' and len(plan) > 0 and 'risk_assessment' in recommended_tools:
            # 添加风险评估任务
            task_id = f"task_{self.task_counter}"
            self.task_counter += 1
            plan.append({
                "id": task_id,
                "name": "风险评估分析",
                "description": "对投资风险进行专业评估",
                "tool_name": "risk_assessment",
                "parameters": {
                    "query": user_query,
                    "previous_task_id": plan[-1]["id"] if plan else None
                },
                "dependencies": [plan[-1]["id"]] if plan else [],
                "task_type": task_type
            })

        # 3. 如果没有生成任何计划，创建一个默认的通用查询任务
        if not plan:
            task_id = f"task_{self.task_counter}"
            self.task_counter += 1
            plan.append({
                "id": task_id,
                "name": "通用查询",
                "description": "处理通用查询请求",
                "tool_name": "general_query",
                "parameters": {
                    "query": user_query,
                    "context": context
                },
                "dependencies": [],
                "task_type": task_type
            })

        # 添加时间戳和会话信息
        for task in plan:
            task["timestamp"] = datetime.now().isoformat()
            task["session_id"] = self._generate_session_id(context)

        return plan

    def _analyze_task_type(self, query: str, context: List[Dict[str, Any]]) -> str:
        """
        分析查询的任务类型

        Args:
            query: 用户查询
            context: 上下文历史

        Returns:
            任务类型字符串
        """
        query_lower = query.lower()
        scores = {task_type: 0 for task_type in self.task_type_keywords.keys()}

        # 计算每种任务类型的关键词匹配分数
        for task_type, keywords in self.task_type_keywords.items():
            for keyword in keywords:
                if keyword in query_lower:
                    scores[task_type] += 1

        # 特殊处理：如果查询同时包含"市场"和"热点"，优先考虑market_research或news_analysis
        if '市场' in query_lower and '热点' in query_lower:
            # 市场热点分析应该优先进行网络数据采集
            if scores['market_research'] > 0 or scores['news_analysis'] > 0:
                return 'market_research' if scores['market_research'] >= scores['news_analysis'] else 'news_analysis'

        # 考虑上下文历史中的任务类型连贯性
        if context:
            for msg in reversed(context[-3:]):  # 查看最近3条消息
                if 'task_type' in msg:
                    scores[msg['task_type']] += 0.5  # 给历史任务类型增加权重

        # 返回得分最高的任务类型
        return max(scores, key=scores.get)

    def _retrieve_from_knowledge_base(self, query: str, top_k: int = 5) -> List[Tuple[str, float, Dict[str, Any]]]:
        """
        从知识库检索相关信息
        
        Args:
            query: 查询文本
            top_k: 返回最相关的k条结果
        
        Returns:
            (文本, 相似度, 元数据)元组列表
        """
        if not self.vector_store or self.vector_store.get_vector_count() == 0:
            print(f"知识库检索失败：向量存储不存在或为空")
            return []

        try:
            # 向量化查询文本
            print(f"正在向量化查询文本: {query}")
            query_vector = self.vectorizer.vectorize_text(query)
            print(f"查询向量生成成功，维度: {len(query_vector)}")
            
            # 从知识库检索
            print(f"正在从知识库检索，top_k={top_k}")
            results = self.vector_store.search_similar(query_vector, top_k)
            print(f"原始检索结果: {results}")
            
            # 降低相似度阈值，提高检索成功率
            filtered_results = [(text, sim, meta)
                                for text, sim, meta in results if sim > 0.1]
            print(f"过滤后结果（相似度>0.1）: {filtered_results}")
            
            return filtered_results
        except Exception as e:
            print(f"知识库检索失败: {str(e)}")
            import traceback
            traceback.print_exc()
            return []

    def _get_available_tools(self, task_type: str) -> List[str]:
        """
        根据任务类型返回推荐的工具列表

        Args:
            task_type: 任务类型

        Returns:
            推荐工具列表
        """
        tool_mapping = {
            'data_collection': ['web_scraping_tool', 'database_tool'],
            'data_analysis': ['data_analysis', 'visualization_tool'],
            'market_research': ['web_scraping_tool', 'data_analysis', 'database_tool'],
            'stock_analysis': ['stock_data_tool', 'data_analysis'],
            'news_analysis': ['web_scraping_tool', 'news_analysis'],
            'risk_assessment': ['risk_assessment', 'data_analysis'],
            'investment_advice': ['investment_advisor', 'risk_assessment'],
            'general_query': ['general_query', 'web_search']
        }

        return tool_mapping.get(task_type, ['general_query'])

    def _extract_query(self, text: str) -> str:
        """
        从文本中提取查询关键词

        Args:
            text: 包含查询的文本

        Returns:
            提取出的查询字符串
        """
        # 简单的关键词提取逻辑
        # 去除常见的限定词和标点符号
        text = text.lower().strip()
        # TODO 提起问题
        # 去除一些常见的前缀词
        for prefix in ['请', '帮我', '帮', '是否可以', '是否能', '能否', '我想', '我要']:
            if text.startswith(prefix):
                text = text[len(prefix):].strip()

        # 去除标点符号
        text = text.translate(str.maketrans('', '', string.punctuation))

        return text.strip()

    def _detect_conversation_stage(self, context: List[Dict[str, Any]]) -> str:
        """
        检测对话阶段

        Args:
            context: 对话上下文

        Returns:
            对话阶段: 'initial' | 'follow_up' | 'clarification' | 'summary'
        """
        if not context or len(context) == 0:
            return 'initial'

        # 分析最后一条用户消息
        last_user_msg = None
        for msg in reversed(context):
            if msg.get('role') == 'user':
                last_user_msg = msg['content'].lower()
                break

        if not last_user_msg:
            return 'initial'

        # 检查是否为澄清问题
        clarification_words = ['是什么', '什么是', '解释', '如何理解', '具体', '详细']
        for word in clarification_words:
            if word in last_user_msg:
                return 'clarification'

        # 检查是否为总结请求
        summary_words = ['总结', '概括', '汇总', '总结一下', '概括一下']
        for word in summary_words:
            if word in last_user_msg:
                return 'summary'

        # 默认是跟进问题
        return 'follow_up'

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
            if 'web_scraping_tool' in available_tools:
                task_id = f"task_{self.task_counter}"
                self.task_counter += 1
                tasks.append(Task(
                    id=task_id,
                    name="数据采集",
                    description="从财经网站采集相关数据",
                    tool_name="web_scraping_tool",
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

        # 如果没有特定流程，创建一个通用查询任务
        if not tasks and 'general_query' in available_tools:
            task_id = f"task_{self.task_counter}"
            self.task_counter += 1
            tasks.append(Task(
                id=task_id,
                name="通用查询",
                description="处理通用查询请求",
                tool_name="general_query",
                parameters={"query": user_request},
                dependencies=[]
            ))

        return tasks

    def _summarize_context(self, context: List[Dict[str, Any]]) -> str:
        """
        生成上下文的摘要

        Args:
            context: 上下文历史

        Returns:
            上下文摘要字符串
        """
        if not context:
            return ""

        # 获取最近3条用户消息和助手回复
        recent_exchanges = []
        for msg in reversed(context[-6:]):  # 最多查看最近6条消息（3轮对话）
            if msg.get('role') in ['user', 'assistant']:
                recent_exchanges.insert(
                    0, f"{msg.get('role', 'unknown')}: {msg.get('content', '')}")

        return "\n".join(recent_exchanges)

    def _generate_session_id(self, context: List[Dict[str, Any]]) -> str:
        """
        生成或获取会话ID

        Args:
            context: 上下文历史

        Returns:
            会话ID字符串
        """
        # 尝试从上下文中获取会话ID
        for msg in context:
            if 'session_id' in msg:
                return msg['session_id']

        # 如果没有，生成一个新的会话ID
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        return f"session_{timestamp}_{hash(str(context)) % 10000}"








