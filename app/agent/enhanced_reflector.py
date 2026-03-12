"""
财富 Agent - 智能投研分析平台
增强版反思器模块
支持深度评估、根因分析、学习机制
"""

import time
import logging
from typing import Dict, Any, List, Optional
import statistics

logger = logging.getLogger(__name__)


class EnhancedReflector:
    """
    增强版反思器

    功能特性：
    1. 深度评估维度 - 工具效果评估、任务完成度、用户满意度预测
    2. 根因分析 - 失败归因、偏差检测、模式识别
    3. 学习机制 - 工具选择偏好、参数调优、最佳实践沉淀
    """

    def __init__(self, memory_manager=None):
        self.memory_manager = memory_manager
        self.logger = logging.getLogger(__name__)

        # 历史学习数据
        self.tool_performance_history = []
        self.success_patterns = []
        self.failure_patterns = []

    def deep_reflect(
        self,
        query: str,
        plan: List[Dict[str, Any]],
        execution_result: Dict[str, Any],
        tool_call_history: List[Dict[str, Any]],
        convergence_threshold: float = 0.8
    ) -> Dict[str, Any]:
        """
        深度反思执行结果

        Args:
            query: 用户查询
            plan: 原始计划
            execution_result: 执行结果
            tool_call_history: 工具调用历史
            convergence_threshold: 收敛阈值

        Returns:
            深度反思结果
        """
        self.logger.info("[深度反思] 开始分析")

        reflection = {
            "timestamp": time.time(),
            "query": query,
            "success_rate": 0.0,
            "evaluation": {},
            "root_cause_analysis": {},
            "key_findings": [],
            "recommendations": [],
            "learning_points": [],
            "convergence_status": False,
            # 预留给规划器的结构化调整建议
            "planning_adjustments": {}
        }

        # Step 1: 计算成功率
        success_rate = execution_result.get('success_rate', 0)
        reflection['success_rate'] = success_rate

        # Step 2: 多维度评估
        evaluation = self._multi_dimensional_evaluation(
            plan, execution_result, tool_call_history
        )
        reflection['evaluation'] = evaluation

        # Step 3: 根因分析
        root_cause = self._root_cause_analysis(
            plan, execution_result, tool_call_history
        )
        reflection['root_cause_analysis'] = root_cause

        # Step 4: 提取关键发现
        key_findings = self._extract_key_findings(evaluation, root_cause)
        reflection['key_findings'] = key_findings

        # Step 5: 生成改进建议
        recommendations = self._generate_recommendations(
            evaluation, root_cause, key_findings
        )
        reflection['recommendations'] = recommendations

        # Step 6: 沉淀学习点
        learning_points = self._extract_learning_points(
            tool_call_history, execution_result
        )
        reflection['learning_points'] = learning_points

        # Step 7: 判断是否收敛
        reflection['convergence_status'] = success_rate >= convergence_threshold

        # Step 8: 为规划器生成结构化的调整建议（工具选择 + 是否需要重规划）
        planning_adjustments = self._build_planning_adjustments(
            success_rate=success_rate,
            root_cause=root_cause,
            tool_call_history=tool_call_history
        )
        reflection['planning_adjustments'] = planning_adjustments

        # 保存到记忆
        if self.memory_manager:
            self.memory_manager.save_intermediate_result(
                'system', 'deep_reflection', reflection)

        self.logger.info(
            f"[深度反思] 完成，成功率：{success_rate:.2%}, 收敛：{reflection['convergence_status']}")
        return reflection

    def _build_planning_adjustments(
        self,
        success_rate: float,
        root_cause: Dict[str, Any],
        tool_call_history: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        为规划器生成结构化的调整建议

        - avoid_tools: 错误率较高、应优先避开的工具
        - prefer_tools: 表现稳定、可优先选择的工具
        - needs_replan: 是否建议整体重规划
        """
        adjustments: Dict[str, Any] = {
            "avoid_tools": [],
            "prefer_tools": [],
            "needs_replan": False
        }

        # 汇总每个工具的成功/失败情况
        tool_stats: Dict[str, Dict[str, int]] = {}
        for record in tool_call_history or []:
            tool_name = record.get("tool_name")
            result = record.get("result", {})
            status = result.get("status")

            if not tool_name:
                continue

            stats = tool_stats.setdefault(
                tool_name, {"success": 0, "error": 0})
            if status == "success":
                stats["success"] += 1
            elif status == "error":
                stats["error"] += 1

        # 计算每个工具的错误率/成功率
        for tool_name, stats in tool_stats.items():
            total = stats["success"] + stats["error"]
            if total == 0:
                continue

            error_ratio = stats["error"] / total
            success_ratio = stats["success"] / total

            # 错误率超过 50% 的工具，标记为需要规避
            if error_ratio >= 0.5:
                adjustments["avoid_tools"].append(tool_name)

            # 成功率高且有一定样本的工具，标记为优先选择
            if success_ratio >= 0.8 and stats["success"] >= 2:
                adjustments["prefer_tools"].append(tool_name)

        # 结合整体成功率和规划问题，判断是否建议重规划
        if success_rate < 0.5 or root_cause.get("planning_issue", False):
            adjustments["needs_replan"] = True

        return adjustments

    def intelligent_decision(
        self,
        reflection: Dict[str, Any],
        plan: List[Dict[str, Any]],
        current_iteration: int,
        max_iterations: int,
        tool_call_history: List[Dict[str, Any]],
        convergence_threshold: float = 0.8
    ) -> Dict[str, Any]:
        """
        智能决策下一步行动

        Args:
            reflection: 反思结果
            plan: 原始计划
            current_iteration: 当前迭代次数
            max_iterations: 最大迭代次数
            tool_call_history: 工具调用历史
            convergence_threshold: 收敛阈值

        Returns:
            决策结果
        """
        self.logger.info("[智能决策] 制定决策")

        decision = {
            "timestamp": time.time(),
            "action": "finish",
            "reason": "",
            "confidence": 0.0,
            "next_steps": []
        }

        success_rate = reflection.get('success_rate', 0)
        convergence_status = reflection.get('convergence_status', False)

        # 决策逻辑

        # 1. 如果已收敛（成功率达标），结束
        if convergence_status and success_rate >= convergence_threshold:
            decision.update({
                "action": "finish",
                "reason": f"已达到收敛标准，成功率：{success_rate:.2%}",
                "confidence": 0.9
            })
            return decision

        # 2. 如果达到最大迭代次数，强制结束
        if current_iteration >= max_iterations - 1:
            decision.update({
                "action": "finish",
                "reason": f"已达到最大迭代次数 ({max_iterations})",
                "confidence": 0.7
            })
            return decision

        # 3. 如果有严重错误，需要重新规划
        root_cause = reflection.get('root_cause_analysis', {})
        if root_cause.get('planning_issue', False):
            decision.update({
                "action": "replan",
                "reason": "规划存在问题，需要重新设计任务链",
                "confidence": 0.85,
                "suggestions": reflection.get('recommendations', [])
            })
            return decision

        # 4. 如果是工具执行问题，重试或降级
        if root_cause.get('tool_execution_issue', False):
            failed_tools = root_cause.get('failed_tools', [])

            if len(failed_tools) > 0:
                decision.update({
                    "action": "retry",
                    "reason": f"工具执行失败：{', '.join(failed_tools)}",
                    "confidence": 0.75,
                    "suggested_tools": ["general_query"]  # 使用备选工具
                })
            else:
                decision.update({
                    "action": "retry",
                    "reason": "临时执行错误，建议重试",
                    "confidence": 0.6
                })
            return decision

        # 5. 部分成功，继续反思优化
        if success_rate >= 0.5:
            decision.update({
                "action": "partial",
                "reason": "部分成功，继续优化",
                "confidence": 0.65,
                "optimization_areas": reflection.get('key_findings', [])
            })
            return decision

        # 6. 成功率很低，重新规划
        decision.update({
            "action": "replan",
            "reason": f"成功率过低 ({success_rate:.2%})，需要重新规划",
            "confidence": 0.8,
            "suggestions": reflection.get('recommendations', [])
        })

        return decision

    def _multi_dimensional_evaluation(
        self,
        plan: List[Dict[str, Any]],
        execution_result: Dict[str, Any],
        tool_call_history: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """多维度评估"""
        evaluation = {
            "quality": "unknown",
            "efficiency": "unknown",
            "robustness": "unknown",
            "completeness": "unknown"
        }

        success_rate = execution_result.get('success_rate', 0)

        # 质量评估
        if success_rate >= 0.9:
            evaluation['quality'] = 'excellent'
        elif success_rate >= 0.7:
            evaluation['quality'] = 'good'
        elif success_rate >= 0.5:
            evaluation['quality'] = 'fair'
        else:
            evaluation['quality'] = 'poor'

        # 效率评估
        total_time = sum(r.get('execution_time', 0) for r in tool_call_history)
        avg_time = total_time / \
            len(tool_call_history) if tool_call_history else 0

        if avg_time < 2:
            evaluation['efficiency'] = 'high'
        elif avg_time < 10:
            evaluation['efficiency'] = 'medium'
        else:
            evaluation['efficiency'] = 'low'

        # 鲁棒性评估
        error_count = execution_result.get('error_count', 0)
        total_tasks = execution_result.get('total_tasks', 1)

        if error_count == 0:
            evaluation['robustness'] = 'high'
        elif error_count / total_tasks < 0.2:
            evaluation['robustness'] = 'medium'
        else:
            evaluation['robustness'] = 'low'

        # 完整性评估
        if success_rate == 1.0:
            evaluation['completeness'] = 'complete'
        elif success_rate >= 0.8:
            evaluation['completeness'] = 'mostly_complete'
        else:
            evaluation['completeness'] = 'incomplete'

        return evaluation

    def _root_cause_analysis(
        self,
        plan: List[Dict[str, Any]],
        execution_result: Dict[str, Any],
        tool_call_history: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """根因分析"""
        analysis = {
            "planning_issue": False,
            "tool_execution_issue": False,
            "parameter_issue": False,
            "timing_issue": False,
            "failed_tools": [],
            "failure_pattern": None
        }

        errors = execution_result.get('errors', [])

        for error in errors:
            error_msg = error.get('error', '').lower()
            task_name = error.get('task_name', '')

            # 分析失败原因
            if '未注册' in error_msg or 'not found' in error_msg:
                analysis['planning_issue'] = True
                analysis['failed_tools'].append(error.get('tool_name'))

            elif '超时' in error_msg or 'timeout' in error_msg:
                analysis['tool_execution_issue'] = True
                analysis['timing_issue'] = True

            elif '参数' in error_msg or 'parameter' in error_msg:
                analysis['parameter_issue'] = True

            else:
                analysis['tool_execution_issue'] = True
                analysis['failed_tools'].append(error.get('tool_name'))

            # 识别失败模式
            if len(errors) > 0:
                analysis['failure_pattern'] = self._identify_failure_pattern(
                    errors)

        return analysis

    def _identify_failure_pattern(self, errors: List[Dict[str, Any]]) -> str:
        """识别失败模式"""
        # 简单模式识别
        tool_errors = [
            e for e in errors if 'tool' in e.get('error', '').lower()]
        timeout_errors = [
            e for e in errors if 'timeout' in e.get('error', '').lower()]

        if len(tool_errors) > len(errors) * 0.5:
            return "系统性工具故障"
        elif len(timeout_errors) > len(errors) * 0.5:
            return "性能瓶颈导致的超时"
        else:
            return "偶发性错误"

    def _extract_key_findings(self, evaluation: Dict[str, Any], root_cause: Dict[str, Any]) -> List[str]:
        """提取关键发现"""
        findings = []

        quality = evaluation.get('quality', 'unknown')
        if quality in ['poor', 'fair']:
            findings.append("执行质量不佳，需要改进")

        efficiency = evaluation.get('efficiency', 'unknown')
        if efficiency == 'low':
            findings.append("执行效率低下，考虑优化或缓存")

        if root_cause.get('planning_issue'):
            findings.append("任务规划存在问题，需要调整策略")

        if root_cause.get('tool_execution_issue'):
            failed_tools = root_cause.get('failed_tools', [])
            if failed_tools:
                findings.append(f"工具执行失败：{', '.join(failed_tools)}")

        return findings

    def _generate_recommendations(
        self,
        evaluation: Dict[str, Any],
        root_cause: Dict[str, Any],
        key_findings: List[str]
    ) -> List[str]:
        """生成改进建议"""
        recommendations = []

        if evaluation.get('quality') in ['poor', 'fair']:
            recommendations.append("提高任务拆解的粒度，减少复杂度")

        if evaluation.get('efficiency') == 'low':
            recommendations.append("考虑并行执行独立任务以提高效率")
            recommendations.append("添加结果缓存机制减少重复计算")

        if root_cause.get('planning_issue'):
            recommendations.append("优化任务依赖关系设计")
            recommendations.append("增加备选工具方案")

        if root_cause.get('tool_execution_issue'):
            recommendations.append("增强工具的错误处理和重试机制")
            recommendations.append("设置合理的超时时间")

        return recommendations

    def _extract_learning_points(
        self,
        tool_call_history: List[Dict[str, Any]],
        execution_result: Dict[str, Any]
    ) -> List[str]:
        """提取学习点"""
        learning_points = []

        # 记录工具表现
        for record in tool_call_history:
            tool_name = record.get('tool_name')
            result = record.get('result', {})

            self.tool_performance_history.append({
                "tool_name": tool_name,
                "success": result.get('status') == 'success',
                "execution_time": result.get('execution_time', 0),
                "timestamp": time.time()
            })

        # 从成功经验中学习
        if execution_result.get('success_rate', 0) >= 0.8:
            successful_tools = [
                r.get('tool_name') for r in tool_call_history
                if r.get('result', {}).get('status') == 'success'
            ]
            if successful_tools:
                learning_points.append(f"推荐工具组合：{', '.join(successful_tools)}")

            # 从失败教训中学习
            if execution_result.get('success_rate', 0) < 0.5:
                failed_tools = [
                    r.get('tool_name') for r in tool_call_history
                    if r.get('result', {}).get('status') == 'error'
                ]
                if failed_tools:
                    learning_points.append(
                        f"避免使用的工具：{', '.join(failed_tools)}")

            return learning_points

            # 为了向后兼容，保留原来的 Reflector 类名
            Reflector = EnhancedReflector
