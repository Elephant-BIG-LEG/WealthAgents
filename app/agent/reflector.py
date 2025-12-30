"""
财富Agent - 智能投研分析平台
私人Agent模块 - 反思器组件
负责评估执行结果并优化未来决策
"""
from typing import Dict, Any, List, Optional
from .memory import MemoryManager
import time
import logging
from datetime import datetime


class Reflector:
    """反思器 - 负责评估执行结果并优化未来决策"""

    def __init__(self, memory_manager: MemoryManager):
        self.memory_manager = memory_manager
        self.logger = logging.getLogger(__name__)

    def reflect_on_task_execution(self, task: Dict[str, Any], result: Dict[str, Any]) -> Dict[str, Any]:
        """
        反思单个任务的执行结果

        Args:
            task: 执行的任务（字典格式）
            result: 任务执行结果

        Returns:
            反思结果，包含评估和改进建议
        """
        self.logger.info(f"开始反思任务: {task['name']} (ID: {task['id']})")

        reflection_result = {
            'task_id': task['id'],
            'task_name': task['name'],
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
            
            # 深入评估结果内容
            task_result = result.get('result', {})
            if isinstance(task_result, dict):
                if task_result.get('status') == 'error':
                    reflection_result['evaluation']['result_quality'] = 'poor'
                    reflection_result['improvements'].append(f"工具 {task['tool_name']} 返回了错误结果")
                    reflection_result['learning_points'].append(f"需要检查工具 {task['tool_name']} 的实现逻辑")
                elif task_result.get('data') is None or len(task_result.get('data', [])) == 0:
                    reflection_result['evaluation']['result_quality'] = 'medium'
                    reflection_result['improvements'].append(f"工具 {task['tool_name']} 返回了空数据，考虑优化查询参数或数据源")
                else:
                    # 检查结果的完整性
                    required_fields = ['data', 'source', 'timestamp']
                    missing_fields = [f for f in required_fields if f not in task_result]
                    if missing_fields:
                        reflection_result['improvements'].append(f"工具 {task['tool_name']} 返回的结果缺少关键字段: {missing_fields}")
            
            reflection_result['learning_points'].append(
                f"工具 {task['tool_name']} 对于 {task.get('description', '无描述')} 任务表现良好")
        else:
            reflection_result['evaluation']['result_quality'] = 'poor'
            reflection_result['improvements'].append(
                f"需要改进工具 {task['tool_name']} 的错误处理")
            reflection_result['learning_points'].append(
                f"工具 {task['tool_name']} 在处理 {task.get('description', '无描述')} 任务时失败")

        # 保存反思结果
        self.memory_manager.save_intermediate_result(
            'system',
            f"reflection_{task['id']}",
            reflection_result
        )

        self.logger.info(f"任务 {task['name']} 反思完成")
        return reflection_result

    def reflect_on_plan_execution(self, tasks: List[Dict[str, Any]], results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        反思整个计划的执行结果

        Args:
            tasks: 执行的任务列表（字典格式）
            results: 任务执行结果列表

        Returns:
            计划反思结果
        """
        self.logger.info(f"开始反思计划执行结果，共 {len(tasks)} 个任务")

        # 统计执行情况
        total_tasks = len(tasks)
        success_tasks = sum(1 for r in results if r.get('status') == 'success')
        failed_tasks = total_tasks - success_tasks
        success_rate = success_tasks / total_tasks if total_tasks > 0 else 0

        # 计算总执行时间
        total_execution_time = sum(r.get('execution_time', 0) for r in results)

        # 分析每个任务的反思结果
        task_reflections = []
        for i, task in enumerate(tasks):
            result = next((r for r in results if r['task_id'] == task['id']), None)
            if result:
                task_reflection = self.reflect_on_task_execution(task, result)
                task_reflections.append(task_reflection)

        # 总结改进建议
        all_improvements = []
        for reflection in task_reflections:
            all_improvements.extend(reflection['improvements'])

        # 去重改进建议
        unique_improvements = list(set(all_improvements))

        # 计划级别的评估
        plan_evaluation = {
            'success_rate': success_rate,
            'efficiency': 'medium',
            'robustness': 'medium',
            'completeness': 'medium'
        }

        # 评估成功率
        if success_rate >= 0.9:
            plan_evaluation['success_rate_text'] = '优秀'
        elif success_rate >= 0.7:
            plan_evaluation['success_rate_text'] = '良好'
        elif success_rate >= 0.5:
            plan_evaluation['success_rate_text'] = '一般'
        else:
            plan_evaluation['success_rate_text'] = '较差'

        # 评估整体执行效率
        if total_execution_time > 60:  # 超过1分钟
            plan_evaluation['efficiency'] = '低'
        elif total_execution_time < 10:  # 少于10秒
            plan_evaluation['efficiency'] = '高'

        # 评估鲁棒性
        if failed_tasks == 0:
            plan_evaluation['robustness'] = '高'
        elif failed_tasks / total_tasks > 0.3:
            plan_evaluation['robustness'] = '低'

        # 评估完整性
        if success_tasks == total_tasks:
            plan_evaluation['completeness'] = '高'

        # 生成计划级别的改进建议
        plan_improvements = []
        if success_rate < 0.8:
            plan_improvements.append('需要优化任务规划，考虑减少任务依赖或增加备用执行路径')
        if total_execution_time > 30:
            plan_improvements.append('考虑并行执行独立任务以提高整体效率')
        if len(unique_improvements) > 0:
            plan_improvements.extend(unique_improvements)

        # 生成学习点
        learning_points = []
        for reflection in task_reflections:
            learning_points.extend(reflection['learning_points'])
        unique_learning_points = list(set(learning_points))

        # 生成行动计划
        action_plan = self._generate_action_plan(plan_evaluation, plan_improvements)

        reflection_result = {
            'total_tasks': total_tasks,
            'success_tasks': success_tasks,
            'failed_tasks': failed_tasks,
            'success_rate': success_rate,
            'total_execution_time': total_execution_time,
            'timestamp': time.time(),
            'evaluation': plan_evaluation,
            'improvements': plan_improvements,
            'learning_points': unique_learning_points,
            'task_reflections': task_reflections,
            'action_plan': action_plan
        }

        # 保存计划反思结果
        self.memory_manager.save_intermediate_result(
            'system',
            'plan_reflection',
            reflection_result
        )

        self.logger.info(f"计划反思完成，成功率: {success_rate:.2%}")
        return reflection_result

    def _generate_action_plan(self, evaluation: Dict[str, Any], improvements: List[str]) -> List[Dict[str, Any]]:
        """
        基于评估结果和改进建议生成具体的行动计划

        Args:
            evaluation: 计划评估结果
            improvements: 改进建议列表

        Returns:
            行动计划列表
        """
        action_plan = []

        # 基于成功率生成行动计划
        if evaluation['success_rate'] < 0.7:
            action_plan.append({
                'priority': 'high',
                'action': '优化任务规划算法',
                'description': '减少任务间的强依赖，增加任务执行的灵活性',
                'responsible': 'system',
                'deadline': time.time() + 86400  # 24小时内
            })

        # 基于效率生成行动计划
        if evaluation['efficiency'] == '低':
            action_plan.append({
                'priority': 'medium',
                'action': '优化工具执行效率',
                'description': '对执行时间较长的工具进行性能优化或添加缓存机制',
                'responsible': 'system',
                'deadline': time.time() + 172800  # 48小时内
            })

        # 基于改进建议生成行动计划
        for improvement in improvements:
            if '工具' in improvement and '返回' in improvement:
                action_plan.append({
                    'priority': 'high',
                    'action': '修复工具实现',
                    'description': improvement,
                    'responsible': 'system',
                    'deadline': time.time() + 43200  # 12小时内
                })

        return action_plan

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




