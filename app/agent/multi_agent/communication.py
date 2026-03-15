"""
A2A 通信决策逻辑与主动发起
Agent 自主决定通信对象、是否发起通信、以及收发接口
"""
from typing import Dict, Any, List, Optional
import logging

from .messages import AgentMessage, MessageType
from .bus import get_bus

logger = logging.getLogger(__name__)

# 角色与可通信对象建议（谁更常与谁交换）
ROLE_PEERS: Dict[str, List[str]] = {
    "technical": ["fundamental", "risk", "devil_advocate"],
    "fundamental": ["technical", "risk", "devil_advocate"],
    "risk": ["technical", "fundamental", "devil_advocate"],
    "devil_advocate": ["technical", "fundamental", "risk"],
}


def decide_communication_targets(
    agent_id: str,
    current_conclusions: List[Dict[str, Any]],
    query: str,
    message_history: Optional[List[AgentMessage]] = None,
) -> List[str]:
    """
    Agent 自主决定本轮要通信的对象。
    - 若存在与己方结论冲突的角色，优先选择其为通信对象；
    - 否则按 ROLE_PEERS 选 1～2 个 peer。
    """
    all_roles = {c.get("role") for c in current_conclusions if c.get("role")}
    peers = ROLE_PEERS.get(agent_id, list(all_roles - {agent_id}))
    targets = []
    my_conclusion = next((c for c in current_conclusions if c.get("role") == agent_id), None)
    my_conf = (my_conclusion or {}).get("confidence", 0)
    # 优先选结论与自己差异大或置信度高的对方
    for c in current_conclusions:
        role = c.get("role")
        if role == agent_id or not role:
            continue
        if role in peers:
            other_conf = c.get("confidence", 0)
            if other_conf > 0.5 or my_conf < 0.5:
                targets.append(role)
    if not targets:
        targets = list(peers)[:2]
    return targets[:3]


def should_initiate_communication(
    agent_id: str,
    conclusions: List[Dict[str, Any]],
    message_history: List[AgentMessage],
    max_initiative_per_session: int = 2,
) -> bool:
    """
    Agent 是否主动发起通信（发请求或邀请辩论）。
    条件：己方有结论且置信度中等以上，且本轮尚未超过主动发起次数。
    """
    my = next((c for c in conclusions if c.get("role") == agent_id), None)
    if not my or my.get("confidence", 0) < 0.4:
        return False
    sent_by_me = sum(1 for m in message_history if m.sender == agent_id and m.msg_type in (
        MessageType.REQUEST.value, MessageType.DEBATE_INVITE.value, MessageType.QUESTION.value,
    ))
    return sent_by_me < max_initiative_per_session


def send_message(
    sender: str,
    receivers: List[str],
    msg_type: str,
    payload: Dict[str, Any],
    session_id: str = "",
    thread_id: str = "",
    reply_to: Optional[str] = None,
) -> AgentMessage:
    """发送消息到总线。"""
    bus = get_bus()
    return bus.send(sender, receivers, msg_type, payload, session_id, thread_id, reply_to)


def receive_messages(
    agent_id: str,
    limit: int = 50,
    session_id: Optional[str] = None,
    thread_id: Optional[str] = None,
) -> List[AgentMessage]:
    """从总线拉取发给该 Agent 的消息。"""
    return get_bus().receive(agent_id, limit=limit, session_id=session_id, thread_id=thread_id)


def broadcast_conclusion(
    sender: str,
    conclusion: Dict[str, Any],
    session_id: str = "",
    thread_id: str = "",
) -> AgentMessage:
    """向所有 Agent 广播己方结论（用于结果共享）。"""
    return send_message(
        sender, [],
        MessageType.BROADCAST.value,
        {"conclusion": conclusion, "type": "conclusion"},
        session_id=session_id,
        thread_id=thread_id,
    )
