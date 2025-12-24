"""
财富Agent - 智能投研分析平台
私人Agent模块 - 反思器组件
负责评估执行结果并优化未来决策
"""
from typing import Dict, Any, List, Optional
from .memory import MemoryManager
from .planner import Task
import time
import logging
from datetime import datetime


class Reflector:
    """反思器 - 负责评估执行结果并优化未来决策"""

    def __init__(self, memory_manager: MemoryManager):
        self.memory_manager = memory_manager
        self.logger = logging.getLogger(__name__)

    def reflect_on_task_execution(self, task: Task, result: Dict[str, Any]) -> Dict[str, Any]:
        """
        反思单个任务的执行结果

        Args:
            task: 执行的任务
            result: 任务执行结果

        Returns:
            反思结果，包含评估和改进建议
        """
        self.logger.info(f"开始反思任务: {task.name} (ID: {task.id})")

        reflection_result = {
            'task_id': task.id,
            'task_name': task.name,
            'execution_time': result.get('execution_time', 0),
            'status': result.get('status', 'unknown'),
            'timestamp': time.time(),
            'evaluation': {},
            'improvements': [],
            'learning_points': []
        }

        # 评估执行效率
        execution_time = result.get('execution_time', 0)
        if execution_time > 10:  # 如果执行时间超过10秒
            reflection_result['evaluation']['efficiency'] = 'low'
            reflection_result['improvements'].append('考虑优化工具执行效率或使用缓存')
        elif execution_time < 1:  # 如果执行时间少于1秒
            reflection_result['evaluation']['efficiency'] = 'high'
        else:
            reflection_result['evaluation']['efficiency'] = 'medium'

        # 评估结果质量
        if result.get('status') == 'success':
            reflection_result['evaluation']['result_quality'] = 'good'
            reflection_result['learning_points'].append(
                f"工具 {task.tool_name} 对于 {task.description} 任务表现良好")
        else:
            reflection_result['evaluation']['result_quality'] = 'poor'
            reflection_result['improvements'].append(
                f"需要改进工具 {task.tool_name} 的错误处理")
            reflection_result['learning_points'].append(
                f"工具 {task.tool_name} 在处理 {task.description} 任务时失败")

        # 保存反思结果
        self.memory_manager.save_intermediate_result(
            'system',
            f"reflection_{task.id}",
            reflection_result
        )

        self.logger.info(f"任务 {task.name} 反思完成")
        return reflection_result

    def reflect_on_plan_execution(self, tasks: List[Task], results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        反思整个计划的执行结果

        Args:
            tasks: 执行的任务列表
            results: 任务执行结果列表

        Returns:
            计划执行的反思结果
        """
        self.logger.info(f"开始反思计划执行，共 {len(tasks)} 个任务")

        total_tasks = len(tasks)
        successful_tasks = sum(1 for r in results if r.get('status') == 'success')
        failed_tasks = total_tasks - successful_tasks

        total_execution_time = sum(r.get('execution_time', 0) for r in results)
        avg_execution_time = total_execution_time / \
            total_tasks if total_tasks > 0 else 0

        reflection_result = {
            'plan_reflection_id': f"plan_reflection_{int(time.time())}",
            'total_tasks': total_tasks,
            'successful_tasks': successful_tasks,
            'failed_tasks': failed_tasks,
            'success_rate': successful_tasks / total_tasks if total_tasks > 0 else 0,
            'total_execution_time': total_execution_time,
            'avg_execution_time': avg_execution_time,
            'timestamp': time.time(),
            'overall_evaluation': {},
            'system_improvements': [],
            'learning_points': []
        }

        # 整体评估
        if successful_tasks == total_tasks:
            reflection_result['overall_evaluation']['success'] = 'excellent'
            reflection_result['learning_points'].append("整个任务计划执行成功，当前规划策略有效")
        elif successful_tasks / total_tasks >= 0.8:
            reflection_result['overall_evaluation']['success'] = 'good'
            reflection_result['learning_points'].append("任务计划大部分成功执行，规划策略基本有效")
        elif successful_tasks / total_tasks >= 0.5:
            reflection_result['overall_evaluation']['success'] = 'fair'
            reflection_result['system_improvements'].append(
                "需要改进任务依赖关系或错误恢复机制")
        else:
            reflection_result['overall_evaluation']['success'] = 'poor'
            reflection_result['system_improvements'].append("需要重新评估任务规划策略")

        # 执行效率评估
        if avg_execution_time > 5:  # 平均执行时间超过5秒
            reflection_result['overall_evaluation']['efficiency'] = 'low'
            reflection_result['system_improvements'].append("考虑并行执行任务或优化工具性能")
        elif avg_execution_time < 2:  # 平均执行时间少于2秒
            reflection_result['overall_evaluation']['efficiency'] = 'high'
        else:
            reflection_result['overall_evaluation']['efficiency'] = 'medium'

        # 识别常见失败模式
        failed_tools = {}
        for i, result in enumerate(results):
            if result.get('status') == 'error':
                tool_name = tasks[i].tool_name
                if tool_name not in failed_tools:
                    failed_tools[tool_name] = 0
                failed_tools[tool_name] += 1

        if failed_tools:
            reflection_result['system_improvements'].append(
                f"工具失败统计: {failed_tools}")
            reflection_result['learning_points'].append(
                f"需要特别关注以下工具的稳定性: {list(failed_tools.keys())}")

        # 保存计划反思结果
        self.memory_manager.save_intermediate_result(
            'system',
            reflection_result['plan_reflection_id'],
            reflection_result
        )

        self.logger.info(
            f"计划执行反思完成，成功率: {reflection_result['success_rate']:.2%}")
        return reflection_result

    def decide_next_step(self, plan_reflection: Dict[str, Any], max_retries: int = 3, current_retry: int = 0) -> Dict[str, Any]:
        """
        决定下一步行动
        
        Args:
            plan_reflection: 计划反思结果
            max_retries: 最大重试次数
            current_retry: 当前重试次数
            
        Returns:
            下一步行动建议
        """
        if current_retry >= max_retries:
            return {"action": "FINISH", "reason": "已达到最大重试次数"}
            
        success_rate = plan_reflection.get('success_rate', 0)
        
        if success_rate == 1.0:
            return {"action": "FINISH", "reason": "所有任务执行成功"}
            
        if success_rate >= 0.8:
            return {"action": "FINISH", "reason": "大部分任务成功，可以接受"}
            
        # 如果成功率低，建议重试或重新规划
        return {
            "action": "RETRY", 
            "reason": "部分任务失败，建议重试",
            "failed_tasks": plan_reflection.get('failed_tasks', 0)
        }

    def update_planning_strategy(self, plan_reflection: Dict[str, Any], user_request: str = ""):
        """
        根据反思结果更新规划策略

        Args:
            plan_reflection: 计划反思结果
            user_request: 用户请求（可选，用于上下文学习）
        """
        self.logger.info("开始更新规划策略")

        # 基于反思结果调整规划策略
        success_rate = plan_reflection.get('success_rate', 0)
        avg_time = plan_reflection.get('avg_execution_time', 0)

        # 学习改进点
        improvements = plan_reflection.get('system_improvements', [])

        # 保存学习到的策略调整
        strategy_update = {
            'timestamp': time.time(),
            'success_rate': success_rate,
            'avg_execution_time': avg_time,
            'improvements': improvements,
            'recommendations': []
        }

        # 根据成功率调整策略
        if success_rate < 0.5:
            strategy_update['recommendations'].append("降低任务复杂度或增加错误处理")
        elif success_rate < 0.8:
            strategy_update['recommendations'].append("优化任务依赖关系")

        # 根据执行时间调整策略
        if avg_time > 5:
            strategy_update['recommendations'].append("考虑并行执行或缓存策略")

        # 保存策略更新到记忆
        self.memory_manager.save_intermediate_result(
            'system',
            'strategy_update',
            strategy_update
        )

        self.logger.info("规划策略更新完成")

    def get_historical_insights(self, user_id: str = "default") -> Dict[str, Any]:
        """
        获取历史洞察，用于改进未来的决策

        Args:
            user_id: 用户ID

        Returns:
            历史洞察数据
        """
        self.logger.info(f"获取用户 {user_id} 的历史洞察")

        # 这里可以实现更复杂的逻辑来分析历史数据
        insights = {
            'user_preferences': self.memory_manager.get_user_preferences(user_id) or {},
            'common_request_patterns': [],
            'effective_strategies': [],
            'improvement_areas': [],
            'timestamp': time.time()
        }

        # 示例：分析历史请求模式
        # 在实际实现中，这里会查询历史数据并进行分析

        return insights
