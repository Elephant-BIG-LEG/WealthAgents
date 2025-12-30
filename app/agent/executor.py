"""
财富Agent - 智能投研分析平台
执行器模块
"""
import time
import logging
from typing import Dict, Any, List, Optional
from .utils.error_handler import create_error, ErrorCodes


class Executor:
    """执行器类，负责执行任务计划"""

    def __init__(self, available_tools: Dict[str, Any]):
        """
        初始化执行器

        Args:
            available_tools: 可用工具字典
        """
        self.logger = logging.getLogger(__name__)
        self.available_tools = available_tools

    def execute_plan(self, plan: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        执行任务计划

        Args:
            plan: 任务计划列表

        Returns:
            执行结果列表
        """
        execution_results = []
        task_id_to_result = {}
        success_count = 0

        # 按时间顺序执行任务
        sorted_tasks = sorted(plan, key=lambda x: x.get('timestamp', 0))

        for task in sorted_tasks:
            task_id = task['id']
            tool_name = task['tool_name']
            # 获取任务参数 - 兼容'params'和'parameters'两种字段名
            params = task.get('params', task.get('parameters', {}))
            dependencies = task.get('dependencies', [])
            task_name = task.get('name', '')

            self.logger.info(f"执行任务: {task_name} (ID: {task_id}, 工具: {tool_name})")

            # 检查依赖任务是否完成
            all_dependencies_met = True
            dependency_results = {}

            for dep_task_id in dependencies:
                if dep_task_id not in task_id_to_result:
                    self.logger.error(f"依赖任务未完成: {dep_task_id} (用于任务: {task_id})")
                    all_dependencies_met = False
                    break
                dependency_results[dep_task_id] = task_id_to_result[dep_task_id]

            if not all_dependencies_met:
                error_result = create_error(
                    error_code=ErrorCodes.EXECUTION_ERROR,
                    error_message=f"依赖任务未完成，无法执行当前任务",
                    task_id=task_id,
                    task_name=task_name,
                    tool_name=tool_name,
                    dependencies=dependencies,
                    missing_dependencies=[dep for dep in dependencies if dep not in task_id_to_result]
                )
                execution_results.append(error_result)
                task_id_to_result[task_id] = error_result
                continue

            # 检查工具是否可用
            if tool_name not in self.available_tools:
                error_result = create_error(
                    error_code=ErrorCodes.TOOL_NOT_FOUND,
                    error_message=f"工具 {tool_name} 未注册",
                    task_id=task_id,
                    task_name=task_name,
                    tool_name=tool_name
                )
                execution_results.append(error_result)
                task_id_to_result[task_id] = error_result
                continue

            try:
                # 获取工具
                tool = self.available_tools[tool_name]

                # 准备工具参数
                tool_params = params.copy()
                if dependency_results:
                    tool_params['dependency_results'] = dependency_results

                # 执行任务
                start_time = time.time()
                result = tool(**tool_params)
                execution_time = time.time() - start_time

                # 确保结果是字典类型
                if not isinstance(result, dict):
                    result = {
                        "data": result,
                        "execution_time": execution_time,
                        "task_id": task_id,
                        "task_name": task_name,
                        "tool_name": tool_name
                    }
                else:
                    # 补充任务信息
                    result['execution_time'] = execution_time
                    result['task_id'] = task_id
                    result['task_name'] = task_name
                    result['tool_name'] = tool_name

                # 记录结果
                execution_results.append(result)
                task_id_to_result[task_id] = result

                # 统计成功任务
                if result.get('status') == 'success':
                    success_count += 1

                self.logger.info(f"任务执行完成: {task_name} (ID: {task_id})，耗时: {execution_time:.2f}秒")

            except Exception as e:
                self.logger.error(f"任务执行失败: {task_name} (ID: {task_id}), 错误: {str(e)}")
                error_result = create_error(
                    error_code=ErrorCodes.TOOL_EXECUTION_ERROR,
                    error_message=f"任务执行失败: {str(e)}",
                    task_id=task_id,
                    task_name=task_name,
                    tool_name=tool_name,
                    exception=str(e)
                )
                execution_results.append(error_result)
                task_id_to_result[task_id] = error_result

        self.logger.info(f"任务计划执行完成，共 {len(sorted_tasks)} 个任务，成功 {success_count} 个")
        return execution_results


    def execute_task(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """
        执行单个任务的便捷方法

        Args:
            task: 要执行的任务（字典格式）

        Returns:
            执行结果
        """
        results = self.execute_plan([task])
        return results[0] if results else {}


def execute_task(task: Dict[str, Any], available_tools: Dict[str, Any]) -> Dict[str, Any]:
    """
    执行单个任务的便捷函数

    Args:
        task: 任务字典
        available_tools: 可用工具字典

    Returns:
        执行结果
    """
    executor = Executor(available_tools)
    return executor.execute_plan([task])[0] if task else {}