"""
财富 Agent - 智能投研分析平台
增强版执行器模块
支持并行执行、工具链编排、超时控制和熔断机制
"""

import time
import logging
from typing import Dict, Any, List, Optional, Callable
from concurrent.futures import ThreadPoolExecutor, as_completed
import random

logger = logging.getLogger(__name__)


class EnhancedExecutor:
    """
    增强版执行器

    功能特性：
    1. 工具调度优化 - 基于 Adapter 的注册中心、优先级队列
    2. 并行执行支持 - 独立任务并行化、结果聚合
    3. 错误处理增强 - 分级恢复、自动重试（指数退避）、降级方案
    """

    def __init__(self, memory_manager=None, config: Dict[str, Any] = None):
        self.memory_manager = memory_manager
        self.config = config or {}
        self.logger = logging.getLogger(__name__)

        # 可用工具注册表
        self.available_tools = {}

        # 配置参数
        self.max_parallel_tasks = self.config.get('max_parallel_tasks', 5)
        self.default_timeout = self.config.get('tool_timeout', 30)
        self.enable_retry = self.config.get('retry_with_backoff', True)
        self.max_retries = self.config.get('max_retries', 3)
        self.base_delay = self.config.get('base_retry_delay', 1.0)
        self.max_delay = self.config.get('max_retry_delay', 60.0)

    def register_tool(self, tool_name: str, tool_func: Callable):
        """注册工具到执行器"""
        self.available_tools[tool_name] = tool_func
        self.logger.info(f"工具已注册：{tool_name}")

    def execute_parallel(self, tasks: List[Dict[str, Any]], timeout: int = None) -> List[Dict[str, Any]]:
        """
        并行执行多个独立任务

        Args:
            tasks: 任务列表
            timeout: 总超时时间（秒）

        Returns:
            执行结果列表
        """
        if not tasks:
            return []

        timeout = timeout or self.default_timeout
        results = [None] * len(tasks)

        self.logger.info(f"开始并行执行 {len(tasks)} 个任务，超时：{timeout}秒")

        with ThreadPoolExecutor(max_workers=min(len(tasks), self.max_parallel_tasks)) as executor:
            # 提交所有任务
            future_to_index = {}
            for i, task in enumerate(tasks):
                future = executor.submit(
                    self._execute_single_task, task, timeout // len(tasks))
                future_to_index[future] = i

            # 收集结果
            start_time = time.time()
            for future in as_completed(future_to_index, timeout=timeout):
                index = future_to_index[future]
                try:
                    result = future.result()
                    results[index] = result
                except Exception as e:
                    self.logger.error(f"任务执行失败 (index={index}): {str(e)}")
                    results[index] = self._create_error_result(
                        tasks[index], str(e))

                # 检查总超时
                if time.time() - start_time > timeout:
                    self.logger.warning("总超时已到，取消剩余任务")
                    break

        return results

    def execute_with_retry(self, task: Dict[str, Any], max_retries: int = None, timeout: int = None) -> Dict[str, Any]:
        """
        执行单个任务，带指数退避重试机制

        Args:
            task: 任务字典
            max_retries: 最大重试次数
            timeout: 超时时间

        Returns:
            执行结果
        """
        max_retries = max_retries or (
            self.max_retries if self.enable_retry else 0)
        timeout = timeout or self.default_timeout

        last_error = None

        for attempt in range(max_retries + 1):
            try:
                self.logger.info(
                    f"执行任务：{task['name']} (尝试 {attempt+1}/{max_retries+1})")
                result = self._execute_single_task(task, timeout)

                if result.get('status') == 'success':
                    return result

                last_error = result.get('error', 'Unknown error')

            except Exception as e:
                last_error = str(e)
                self.logger.error(f"任务执行异常：{str(e)}")

            # 如果不是最后一次尝试，进行指数退避等待
            if attempt < max_retries:
                delay = min(self.base_delay * (2 ** attempt) +
                            random.uniform(0, 0.1), self.max_delay)
                self.logger.info(f"等待 {delay:.2f}秒后重试...")
                time.sleep(delay)

        # 所有重试都失败，返回错误结果或降级方案
        self.logger.warning(f"任务最终失败：{task['name']}, 尝试降级方案")
        return self._execute_fallback(task, last_error)

    def _execute_single_task(self, task: Dict[str, Any], timeout: int) -> Dict[str, Any]:
        """执行单个任务"""
        import signal

        task_id = task['id']
        tool_name = task.get('tool_name', 'unknown')
        params = task.get('parameters', {})

        # 检查工具是否可用
        if tool_name not in self.available_tools:
            return self._create_error_result(task, f"工具未注册：{tool_name}")

        try:
            # 设置超时（仅 Unix 系统有效）
            if hasattr(signal, 'SIGALRM'):
                def timeout_handler(signum, frame):
                    raise TimeoutError(f"任务执行超时 ({timeout}秒)")

                old_handler = signal.signal(signal.SIGALRM, timeout_handler)
                signal.alarm(timeout)

            # 执行工具
            tool = self.available_tools[tool_name]
            start_time = time.time()
            result = tool(**params)
            execution_time = time.time() - start_time

            # 取消超时
            if hasattr(signal, 'SIGALRM'):
                signal.alarm(0)
                signal.signal(signal.SIGALRM, old_handler)

            # 确保结果是字典
            if not isinstance(result, dict):
                result = {"data": result}

            # 添加执行元数据
            result.update({
                "status": "success",
                "task_id": task_id,
                "task_name": task.get('name', ''),
                "tool_name": tool_name,
                "execution_time": round(execution_time, 2)
            })

            self.logger.info(
                f"任务执行成功：{task['name']}, 耗时：{execution_time:.2f}秒")
            return result

        except TimeoutError as e:
            self.logger.error(f"任务超时：{task['name']}")
            return self._create_error_result(task, str(e))

        except Exception as e:
            self.logger.error(f"任务执行失败：{task['name']}, 错误：{str(e)}")
            return self._create_error_result(task, str(e))

    def _execute_fallback(self, task: Dict[str, Any], error: str) -> Dict[str, Any]:
        """执行降级方案"""
        fallback_tools = task.get('fallback_tools', ['general_query'])

        for fallback_tool_name in fallback_tools:
            if fallback_tool_name in self.available_tools:
                try:
                    self.logger.info(f"使用降级工具：{fallback_tool_name}")
                    tool = self.available_tools[fallback_tool_name]
                    result = tool(query=task.get('description', ''))

                    if isinstance(result, dict):
                        result.update({
                            "status": "partial_success",
                            "fallback_from": task.get('tool_name'),
                            "original_error": error
                        })
                        return result
                except Exception as e:
                    self.logger.error(
                        f"降级工具也失败：{fallback_tool_name}, {str(e)}")

        # 所有降级方案都失败
        return self._create_error_result(task, f"主工具和降级工具都失败：{error}")

    def _create_error_result(self, task: Dict[str, Any], error_message: str) -> Dict[str, Any]:
        """创建错误结果"""
        return {
            "status": "error",
            "task_id": task['id'],
            "task_name": task.get('name', ''),
            "tool_name": task.get('tool_name', 'unknown'),
            "error": error_message,
            "timestamp": time.time()
        }

    def aggregate_results(self, results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        聚合多个执行结果

        Args:
            results: 执行结果列表

        Returns:
            聚合后的结果
        """
        if not results:
            return {"status": "no_results", "data": []}

        total_tasks = len(results)
        success_count = sum(1 for r in results if r.get('status') == 'success')
        partial_count = sum(1 for r in results if r.get(
            'status') == 'partial_success')
        error_count = total_tasks - success_count - partial_count

        # 计算成功率
        success_rate = (success_count + 0.5 * partial_count) / \
            total_tasks if total_tasks > 0 else 0

        # 聚合数据
        aggregated_data = []
        errors = []

        for result in results:
            if result.get('status') in ['success', 'partial_success']:
                aggregated_data.append(result.get('data', result))
            elif result.get('error'):
                errors.append({
                    "task_id": result.get('task_id'),
                    "task_name": result.get('task_name'),
                    "error": result.get('error')
                })

        return {
            "status": "success" if success_rate >= 0.8 else ("partial_success" if success_rate >= 0.5 else "error"),
            "success_rate": round(success_rate, 2),
            "total_tasks": total_tasks,
            "success_count": success_count,
            "partial_count": partial_count,
            "error_count": error_count,
            "data": aggregated_data,
            "errors": errors,
            "timestamp": time.time()
        }


# 为了向后兼容，保留原来的 Executor 类名
Executor = EnhancedExecutor
