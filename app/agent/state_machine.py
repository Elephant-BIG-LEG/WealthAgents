"""
Agent 状态机：显式状态与转换规则，便于复杂场景下的状态流转与优先级调度
"""
from enum import Enum
from typing import Dict, Any, List, Optional
import logging

logger = logging.getLogger(__name__)


class AgentStateEnum(str, Enum):
    """Agent 显式状态"""
    INIT = "initial"
    PLANNING = "planning"
    PLANNING_DONE = "planning_complete"
    EXECUTING = "executing"
    EXECUTION_DONE = "execution_complete"
    REFLECTING = "reflecting"
    REFLECTION_DONE = "reflection_complete"
    DECIDING = "deciding"
    DECISION_DONE = "decision_complete"
    REPLANNING = "replanning"
    FINISHED = "finished"
    FAILED = "failed"


# 合法状态转换
VALID_TRANSITIONS: Dict[AgentStateEnum, List[AgentStateEnum]] = {
    AgentStateEnum.INIT: [AgentStateEnum.PLANNING],
    AgentStateEnum.PLANNING: [AgentStateEnum.PLANNING_DONE, AgentStateEnum.FAILED],
    AgentStateEnum.PLANNING_DONE: [AgentStateEnum.EXECUTING],
    AgentStateEnum.EXECUTING: [AgentStateEnum.EXECUTION_DONE, AgentStateEnum.FAILED],
    AgentStateEnum.EXECUTION_DONE: [AgentStateEnum.REFLECTING],
    AgentStateEnum.REFLECTING: [AgentStateEnum.REFLECTION_DONE],
    AgentStateEnum.REFLECTION_DONE: [AgentStateEnum.DECIDING],
    AgentStateEnum.DECIDING: [
        AgentStateEnum.DECISION_DONE,
        AgentStateEnum.REPLANNING,
        AgentStateEnum.FINISHED,
    ],
    AgentStateEnum.DECISION_DONE: [AgentStateEnum.PLANNING, AgentStateEnum.EXECUTING, AgentStateEnum.REFLECTING, AgentStateEnum.FINISHED],
    AgentStateEnum.REPLANNING: [AgentStateEnum.PLANNING],
    AgentStateEnum.FINISHED: [],
    AgentStateEnum.FAILED: [AgentStateEnum.PLANNING, AgentStateEnum.FINISHED],
}


class AgentStateMachine:
    """简单状态机：校验转换并记录当前状态"""

    def __init__(self, initial: AgentStateEnum = AgentStateEnum.INIT):
        self.current = initial
        self.history: List[AgentStateEnum] = [initial]

    def can_transition_to(self, target: AgentStateEnum) -> bool:
        allowed = VALID_TRANSITIONS.get(self.current, [])
        return target in allowed

    def transition(self, target: AgentStateEnum) -> bool:
        if not self.can_transition_to(target):
            logger.warning(f"非法状态转换: {self.current} -> {target}")
            return False
        self.current = target
        self.history.append(target)
        return True

    def get_state(self) -> AgentStateEnum:
        return self.current


def schedule_tasks_by_priority_and_dependency(
    tasks: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    """
    按优先级与依赖关系调度任务顺序。
    优先级: critical > high > medium > low；
    同优先级内按 dependencies 拓扑序。
    """
    priority_order = {"critical": 0, "high": 1, "medium": 2, "low": 3}
    id_to_task = {t["id"]: t for t in tasks}

    def sort_key(t):
        pri = t.get("priority", "medium")
        return (priority_order.get(pri, 2), t["id"])

    sorted_by_pri = sorted(tasks, key=sort_key)
    result: List[Dict[str, Any]] = []
    added = set()

    def add_with_deps(task: Dict[str, Any]):
        if task["id"] in added:
            return
        for dep_id in task.get("dependencies") or []:
            if dep_id in id_to_task and dep_id not in added:
                add_with_deps(id_to_task[dep_id])
        result.append(task)
        added.add(task["id"])

    for t in sorted_by_pri:
        add_with_deps(t)
    return result
