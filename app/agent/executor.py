"""
财富Agent - 智能投研分析平台
私人Agent模块 - 执行器组件
负责执行规划器生成的任务
"""
from typing import Dict, Any, List, Optional
from .planner import Task
from .memory import MemoryManager
import time
import logging


class ToolNotFoundError(Exception):
    """工具未找到异常"""
    pass


class Executor:
    """任务执行器 - 负责执行规划器生成的任务"""

    def __init__(self, memory_manager: MemoryManager):
        self.memory_manager = memory_manager
        self.tools = {}  # 工具注册表
        self.logger = logging.getLogger(__name__)

    def register_tool(self, name: str, tool_func):
        """
        注册工具函数

        Args:
            name: 工具名称
            tool_func: 工具函数
        """
        self.tools[name] = tool_func
        self.logger.info(f"工具 {name} 已注册")

    def execute_task(self, task: Task) -> Dict[str, Any]:
        """
        执行单个任务

        Args:
            task: 要执行的任务

        Returns:
            执行结果
        """
        self.logger.info(f"开始执行任务: {task.name} (ID: {task.id})")

        # 检查所需工具是否存在
        if task.tool_name not in self.tools:
            raise ToolNotFoundError(f"工具 '{task.tool_name}' 未注册")

        try:
            # 获取依赖任务的结果
            dependency_results = {}
            for dep_id in task.dependencies:
                dep_result = self.memory_manager.get_task_result(dep_id)
                if dep_result is not None:
                    dependency_results[dep_id] = dep_result

            # 执行工具函数
            tool_func = self.tools[task.tool_name]

            # 合并参数：依赖结果 + 任务参数
            execution_params = {**task.parameters}
            if dependency_results:
                execution_params['dependency_results'] = dependency_results

            start_time = time.time()
            result = tool_func(**execution_params)
            execution_time = time.time() - start_time

            # 保存执行结果到记忆管理器
            task_result = {
                'task_id': task.id,
                'task_name': task.name,
                'result': result,
                'execution_time': execution_time,
                'status': 'success',
                'timestamp': time.time()
            }

            self.memory_manager.save_task_result(task.id, task_result)

            self.logger.info(f"任务 {task.name} 执行成功，耗时 {execution_time:.2f} 秒")
            return task_result

        except Exception as e:
            self.logger.error(f"任务 {task.name} 执行失败: {str(e)}")

            # 记录失败结果
            error_result = {
                'task_id': task.id,
                'task_name': task.name,
                'result': None,
                'execution_time': 0,
                'status': 'error',
                'error_message': str(e),
                'timestamp': time.time()
            }

            self.memory_manager.save_task_result(task.id, error_result)
            raise e

    def execute_plan(self, tasks: List[Task]) -> List[Dict[str, Any]]:
        """
        执行任务计划

        Args:
            tasks: 任务列表

        Returns:
            所有任务的执行结果
        """
        self.logger.info(f"开始执行任务计划，共 {len(tasks)} 个任务")

        results = []

        for i, task in enumerate(tasks):
            try:
                # 检查依赖任务是否已完成
                missing_deps = []
                for dep_id in task.dependencies:
                    if self.memory_manager.get_task_result(dep_id) is None:
                        missing_deps.append(dep_id)

                if missing_deps:
                    raise Exception(f"任务 {task.name} 依赖的任务未完成: {missing_deps}")

                # 执行当前任务
                result = self.execute_task(task)
                results.append(result)

                # 更新进度（在实际应用中可以发送给前端）
                progress = (i + 1) / len(tasks) * 100
                self.logger.info(f"任务执行进度: {progress:.1f}%")

            except Exception as e:
                self.logger.error(f"执行任务 {task.name} 时发生错误: {str(e)}")
                # 在实际应用中，可以选择继续执行后续任务或停止
                raise e

        self.logger.info("任务计划执行完成")
        return results
