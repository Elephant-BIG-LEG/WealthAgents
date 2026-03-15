"""
A2A 辩论机制：冲突检测、证据交换、质疑、多轮辩论流程
"""
from typing import Dict, Any, List, Optional, Tuple
import logging
import uuid

from .messages import AgentMessage, MessageType
from .bus import get_bus

logger = logging.getLogger(__name__)


def detect_conflicts(conclusions: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    检测结论间的冲突点。
    返回 [{ "roles": [r1, r2], "description": "...", "severity": "high"|"medium"|"low" }, ...]
    """
    conflicts = []
    for i, a in enumerate(conclusions):
        for j, b in enumerate(conclusions):
            if i >= j or not a.get("role") or not b.get("role"):
                continue
            conf_a = a.get("confidence", 0)
            conf_b = b.get("confidence", 0)
            concl_a = (a.get("conclusion") or str(a.get("raw", "")))[:300]
            concl_b = (b.get("conclusion") or str(b.get("raw", "")))[:300]
            if not concl_a or not concl_b:
                continue
            # 简单启发式：双方置信度都较高且结论文本差异大
            if conf_a >= 0.5 and conf_b >= 0.5:
                if concl_a != concl_b:
                    severity = "high" if (conf_a > 0.7 and conf_b > 0.7) else "medium"
                    conflicts.append({
                        "roles": [a["role"], b["role"]],
                        "description": f"{a['role']} 与 {b['role']} 结论不一致",
                        "severity": severity,
                        "conclusions": {a["role"]: concl_a, b["role"]: concl_b},
                    })
    return conflicts


def run_debate_round(
    session_id: str,
    thread_id: str,
    agent_ids: List[str],
    conclusions: List[Dict[str, Any]],
    conflict: Dict[str, Any],
    max_statements_per_agent: int = 2,
) -> List[AgentMessage]:
    """
    执行一轮辩论：每个参与角色可发一条陈述 + 一条反驳/证据。
    通过总线发送 DEBATE_STATEMENT / DEBATE_REBUTTAL / EVIDENCE / QUESTION。
    返回本轮产生的消息列表。
    """
    bus = get_bus()
    messages: List[AgentMessage] = []
    roles = conflict.get("roles", [])
    for agent_id in agent_ids:
        if agent_id not in roles:
            continue
        c = next((x for x in conclusions if x.get("role") == agent_id), None)
        if not c:
            continue
        # 陈述
        st = bus.send(
            agent_id,
            [r for r in roles if r != agent_id],
            MessageType.DEBATE_STATEMENT.value,
            {
                "position": c.get("conclusion", "") or str(c.get("raw", ""))[:500],
                "confidence": c.get("confidence", 0),
                "evidence": c.get("evidence", [])[:5],
            },
            session_id=session_id,
            thread_id=thread_id,
        )
        messages.append(st)
    for agent_id in agent_ids:
        if agent_id not in roles:
            continue
        # 对另一方提出质疑或反驳
        other = next((r for r in roles if r != agent_id), None)
        if not other:
            continue
        q = bus.send(
            agent_id,
            [other],
            MessageType.QUESTION.value,
            {"question": f"请提供支持你结论的证据或补充说明。"},
            session_id=session_id,
            thread_id=thread_id,
        )
        messages.append(q)
    return messages


def run_debate(
    session_id: str,
    conclusions: List[Dict[str, Any]],
    agent_ids: List[str],
    max_rounds: int = 3,
) -> Dict[str, Any]:
    """
    多轮辩论流程：
    1. 检测冲突
    2. 对每个冲突发起 thread，进行多轮陈述与证据交换
    3. 返回辩论结果：各轮消息、是否达成共识（简化：以最后一轮陈述为准，不做强共识判断）
    """
    thread_id = f"debate_{uuid.uuid4().hex[:12]}"
    conflicts = detect_conflicts(conclusions)
    all_messages: List[AgentMessage] = []
    for conflict in conflicts:
        for r in range(max_rounds):
            round_msgs = run_debate_round(
                session_id, f"{thread_id}_{r}", agent_ids, conclusions, conflict,
            )
            all_messages.extend(round_msgs)
    return {
        "thread_id": thread_id,
        "conflicts": conflicts,
        "rounds": max_rounds,
        "messages_count": len(all_messages),
        "messages": [m.to_dict() for m in all_messages],
    }
