"""
财富 Agent - 智能投研分析平台
增强版规划器模块
支持任务类型扩展、依赖管理增强、动态重规划
"""

from typing import Dict, List, Any, Optional, Set
from dataclasses import dataclass, field
import logging
from datetime import datetime
import time

logger = logging.getLogger(__name__)


@dataclass
class EnhancedTask:
    """增强版任务数据类"""
    id: str
    name: str
    description: str
    tool_name: str
    parameters: Dict[str, Any]
    dependencies: List[str] = field(default_factory=list)
    priority: str = "medium"  # low, medium, high, critical
    # market_data, financial_report, risk_assessment, etc.
    task_type: str = "general"
    estimated_duration: int = 30  # 预计执行时间（秒）
    retry_count: int = 0
    max_retries: int = 3
    status: str = "pending"  # pending, running, completed, failed, skipped
    result: Optional[Dict[str, Any]] = None
    created_at: float = field(default_factory=time.time)
    started_at: Optional[float] = None
    completed_at: Optional[float] = None


class EnhancedPlanner:
    """
    增强版规划器

    功能特性：
    1. 任务类型扩展 - 支持行情检索、财报分析、风险评估等专业任务
    2. 依赖管理增强 - DAG 依赖图、条件依赖、并行任务识别
    3. 动态重规划 - 根据反思结果调整计划、备选方案生成
    """

    def __init__(self, memory_manager=None):
        self.memory_manager = memory_manager
        self.task_counter = 0
        self.logger = logging.getLogger(__name__)

        # 任务类型定义
        self.task_types = {
            'market_data': {
                'keywords': ['行情', '股价', '实时', '涨跌', '涨停', '跌停'],
                'tools': ['market_data_adapter', 'web_scraping_tool'],
                'priority': 'high'
            },
            'financial_report': {
                'keywords': ['财报', '年报', '季报', '财务', '营收', '利润'],
                'tools': ['financial_report_adapter', 'database_tool'],
                'priority': 'high'
            },
            'risk_assessment': {
                'keywords': ['风险', '评估', '波动', '回撤', 'var'],
                'tools': ['risk_assessment_adapter', 'data_analysis'],
                'priority': 'critical'
            },
            'technical_analysis': {
                'keywords': ['技术面', 'K 线', '均线', 'MACD', 'KDJ'],
                'tools': ['data_analysis', 'visualization_tool'],
                'priority': 'medium'
            },
            'fundamental_analysis': {
                'keywords': ['基本面', '估值', 'pe', 'pb', '现金流'],
                'tools': ['financial_report_adapter', 'data_analysis'],
                'priority': 'medium'
            },
            'data_collection': {
                'keywords': ['收集', '采集', '获取', '下载'],
                'tools': ['web_scraping_tool', 'database_tool'],
                'priority': 'low'
            },
            'general': {
                'keywords': [],
                'tools': ['general_query'],
                'priority': 'low'
            }
        }

    def create_enhanced_plan(
        self,
        user_query: str,
        context: List[Dict[str, Any]],
        tool_call_history: List[Dict[str, Any]] = None,
        previous_reflection: Dict[str, Any] = None,
        is_replan: bool = False
    ) -> List[Dict[str, Any]]:
        """
        创建增强版任务计划

        Args:
            user_query: 用户查询
            context: 上下文历史
            tool_call_history: 工具调用历史
            previous_reflection: 之前的反思结果
            is_replan: 是否是重新规划

        Returns:
            任务计划列表
        """
        self.logger.info(f"{'[重规划]' if is_replan else '[规划]'} 开始创建计划")

        plan = []

        # Step 1: 分析任务类型
        task_type = self._analyze_task_type(user_query)
        self.logger.info(f"识别任务类型：{task_type}")

        # Step 2: 检查是否需要多步骤处理
        requires_multi_step = self._check_multi_step_requirement(
            user_query, task_type)

        # Step 3: 构建任务 DAG（有向无环图）
        if requires_multi_step:
            plan = self._build_task_dag(
                user_query, task_type, tool_call_history)
        else:
            plan = self._create_simple_plan(user_query, task_type)

        # Step 4: 如果有之前的反思结果，应用调整建议
        if previous_reflection and is_replan:
            plan = self._apply_reflection_adjustments(
                plan, previous_reflection)

        # Step 5: 优化任务顺序（基于优先级和依赖关系）
        plan = self._optimize_task_order(plan)

        # Step 6: 为每个任务添加元数据
        for task in plan:
            task['timestamp'] = datetime.now().isoformat()
            task['session_id'] = self._generate_session_id(context)
            task['is_replan'] = is_replan

        self.logger.info(f"计划创建完成，共 {len(plan)} 个任务")
        return plan

    def _analyze_task_type(self, query: str) -> str:
        """分析任务类型"""
        query_lower = query.lower()
        scores = {task_type: 0 for task_type in self.task_types.keys()}

        for task_type, config in self.task_types.items():
            for keyword in config['keywords']:
                if keyword.lower() in query_lower:
                    scores[task_type] += 1

        # 返回得分最高的任务类型
        best_match = max(scores, key=scores.get)
        return best_match if scores[best_match] > 0 else 'general'

    def _check_multi_step_requirement(self, query: str, task_type: str) -> bool:
        """检查是否需要多步骤处理"""
        multi_step_keywords = ['分析', '评估', '对比', '预测', '为什么', '如何']
        return any(kw in query.lower() for kw in multi_step_keywords)

    def _build_task_dag(self, user_query: str, task_type: str, tool_call_history: List[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """
        构建任务 DAG（有向无环图）

        实现复杂依赖关系管理：
        - 数据采集 → 数据分析 → 风险评估
        - 支持条件依赖
        - 识别可并行任务
        """
        tasks = []

        # 根据任务类型构建不同的任务链
        if task_type == 'market_data':
            # 行情分析任务链
            tasks = self._build_market_data_tasks(user_query)
        elif task_type == 'financial_report':
            # 财报分析任务链
            tasks = self._build_financial_tasks(user_query)
        elif task_type == 'risk_assessment':
            # 风险评估任务链
            tasks = self._build_risk_tasks(user_query)
        else:
            # 通用任务链
            tasks = self._build_general_tasks(user_query, task_type)

        # 检查是否有之前失败的任务，添加备选方案
        if tool_call_history:
            tasks = self._add_fallback_tasks(tasks, tool_call_history)

        return tasks

    def _build_market_data_tasks(self, query: str) -> List[Dict[str, Any]]:
        """构建行情数据任务链"""
        tasks = []

        # Task 1: 获取实时行情
        task1 = self._create_task(
            name="获取实时行情",
            description="从多个数据源获取实时行情数据",
            tool_name="market_data_adapter",
            parameters={"query": query, "data_source": "sina"},
            dependencies=[],
            priority="high",
            task_type="market_data"
        )
        tasks.append(task1)

        # Task 2: 行情数据分析
        task2 = self._create_task(
            name="行情数据分析",
            description="分析行情数据的趋势和模式",
            tool_name="data_analysis",
            parameters={"previous_task_id": task1['id']},
            dependencies=[task1['id']],
            priority="medium",
            task_type="data_analysis"
        )
        tasks.append(task2)

        return tasks

    def _build_financial_tasks(self, query: str) -> List[Dict[str, Any]]:
        """构建财报分析任务链"""
        tasks = []

        # Task 1: 获取财报数据
        task1 = self._create_task(
            name="获取财报数据",
            description="从数据库或 API 获取财报数据",
            tool_name="financial_report_adapter",
            parameters={"query": query},
            dependencies=[],
            priority="high",
            task_type="financial_report"
        )
        tasks.append(task1)

        # Task 2: 财务指标计算
        task2 = self._create_task(
            name="财务指标计算",
            description="计算关键财务指标（ROE、毛利率等）",
            tool_name="data_analysis",
            parameters={"previous_task_id": task1['id']},
            dependencies=[task1['id']],
            priority="medium",
            task_type="fundamental_analysis"
        )
        tasks.append(task2)

        return tasks

    def _build_risk_tasks(self, query: str) -> List[Dict[str, Any]]:
        """构建风险评估任务链"""
        tasks = []

        # Task 1: 获取基础数据
        task1 = self._create_task(
            name="获取风险数据",
            description="获取用于风险评估的历史数据",
            tool_name="market_data_adapter",
            parameters={"query": query},
            dependencies=[],
            priority="high",
            task_type="market_data"
        )
        tasks.append(task1)

        # Task 2: 风险指标计算
        task2 = self._create_task(
            name="风险指标计算",
            description="计算波动率、VaR、最大回撤等风险指标",
            tool_name="risk_assessment_adapter",
            parameters={"previous_task_id": task1['id']},
            dependencies=[task1['id']],
            priority="critical",
            task_type="risk_assessment"
        )
        tasks.append(task2)

        return tasks

    def _build_general_tasks(self, query: str, task_type: str) -> List[Dict[str, Any]]:
        """构建通用任务链"""
        tasks = []

        task = self._create_task(
            name="通用查询处理",
            description=f"处理{task_type}类型的查询",
            tool_name="general_query",
            parameters={"query": query},
            dependencies=[],
            priority="low",
            task_type=task_type
        )
        tasks.append(task)

        return tasks

    def _create_task(
        self,
        name: str,
        description: str,
        tool_name: str,
        parameters: Dict[str, Any],
        dependencies: List[str] = None,
        priority: str = "medium",
        task_type: str = "general"
    ) -> Dict[str, Any]:
        """创建单个任务"""
        task_id = f"task_{self.task_counter}"
        self.task_counter += 1

        return {
            "id": task_id,
            "name": name,
            "description": description,
            "tool_name": tool_name,
            "parameters": parameters,
            "dependencies": dependencies or [],
            "priority": priority,
            "task_type": task_type,
            "estimated_duration": 30,
            "status": "pending"
        }

    def _apply_reflection_adjustments(self, plan: List[Dict[str, Any]], reflection: Dict[str, Any]) -> List[Dict[str, Any]]:
        """根据反思结果调整计划（工具选择优化 + 任务规划优化）"""
        # 文本型建议（向后兼容）
        recommendations = reflection.get('recommendations', []) or []
        # 结构化的规划调整建议（由 EnhancedReflector 提供）
        planning_adjustments = reflection.get(
            'planning_adjustments', {}) or {}

        # 拷贝一份计划，避免原地修改
        adjusted_plan: List[Dict[str, Any]] = [dict(task) for task in plan]

        # 1) 工具选择优化：根据 avoid_tools / prefer_tools 调整任务
        avoid_tools = set(planning_adjustments.get('avoid_tools', []))
        prefer_tools = set(planning_adjustments.get('prefer_tools', []))

        if avoid_tools:
            for task in adjusted_plan:
                if task.get('tool_name') in avoid_tools:
                    # 标记该工具应当规避，并提供兜底工具
                    task['avoid'] = True
                    fallback = task.get('fallback_tools') or []
                    if 'general_query' not in fallback:
                        fallback.append('general_query')
                    task['fallback_tools'] = fallback

        if prefer_tools:
            for task in adjusted_plan:
                if task.get('tool_name') in prefer_tools:
                    # 提高优先级，让表现好的工具先执行
                    current_priority = task.get('priority', 'medium')
                    if current_priority in ['low', 'medium']:
                        task['priority'] = 'high'

        # 2) 从文本建议中抽取「效率优化」信号，推动更多任务并行化
        for text in recommendations:
            text_str = str(text)
            if '效率' in text_str or '并行' in text_str:
                for task in adjusted_plan:
                    if not task.get('dependencies'):
                        task['can_parallel'] = True

        return adjusted_plan

    def _optimize_task_order(self, plan: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """优化任务顺序"""
        # 按优先级排序
        priority_order = {'critical': 0, 'high': 1, 'medium': 2, 'low': 3}
        return sorted(plan, key=lambda t: priority_order.get(t.get('priority', 'medium'), 2))

    def _add_fallback_tasks(self, tasks: List[Dict[str, Any]], tool_call_history: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """添加备选任务"""
        # 检查历史中失败的任务
        failed_tools = set()
        for record in tool_call_history:
            if record.get('result', {}).get('status') == 'error':
                failed_tools.add(record.get('tool_name'))

        # 为失败的工具添加备选
        enhanced_tasks = []
        for task in tasks:
            enhanced_tasks.append(task)

            if task.get('tool_name') in failed_tools:
                # 添加备选任务
                fallback_task = task.copy()
                fallback_task['id'] = f"{task['id']}_fallback"
                fallback_task['tool_name'] = 'general_query'
                fallback_task['dependencies'] = [task['id']]
                fallback_task['priority'] = 'low'
                enhanced_tasks.append(fallback_task)

        return enhanced_tasks

    def _summarize_context(self, context: List[Dict[str, Any]]) -> str:
        """总结上下文"""
        if not context:
            return ""

        recent_exchanges = []
        for msg in reversed(context[-6:]):
            if msg.get('role') in ['user', 'assistant']:
                recent_exchanges.insert(
                    0, f"{msg.get('role', 'unknown')}: {msg.get('content', '')}")

        return "\n".join(recent_exchanges)

    def _generate_session_id(self, context: List[Dict[str, Any]]) -> str:
        """生成会话 ID"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        return f"session_{timestamp}_{hash(str(context)) % 10000}"


# 为了向后兼容，保留原来的 Planner 类名
Planner = EnhancedPlanner
