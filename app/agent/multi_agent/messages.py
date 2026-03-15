"""
A2A 统一消息格式
支持请求/响应、辩论、协商、任务分配、证据交换等类型
"""
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field
from enum import Enum
import time
import uuid


class MessageType(str, Enum):
    """消息类型"""
    REQUEST = "request"           # 请求信息/数据
    RESPONSE = "response"         # 响应/回复
    DEBATE_INVITE = "debate_invite"   # 邀请参与辩论
    DEBATE_STATEMENT = "debate_statement"  # 辩论陈述/立场
    DEBATE_REBUTTAL = "debate_rebuttal"    # 反驳
    EVIDENCE = "evidence"         # 证据交换
    QUESTION = "question"         # 质疑
    NEGOTIATION_PROPOSAL = "negotiation_proposal"  # 协商提议
    NEGOTIATION_VOTE = "negotiation_vote"  # 投票
    NEGOTIATION_COMPROMISE = "negotiation_compromise"  # 妥协/折中
    TASK_ALLOCATION = "task_allocation"   # 任务分配
    TASK_RESULT = "task_result"   # 任务结果共享
    BROADCAST = "broadcast"       # 广播给所有 Agent


@dataclass
class AgentMessage:
    """
    统一 A2A 消息格式
    """
    msg_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    msg_type: str = MessageType.REQUEST.value
    sender: str = ""
    receivers: List[str] = field(default_factory=list)  # 空列表表示广播
    session_id: str = ""
    thread_id: str = ""   # 辩论/协商线程，同 thread 的消息为一组
    payload: Dict[str, Any] = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)
    reply_to: Optional[str] = None  # 回复的 msg_id
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "msg_id": self.msg_id,
            "msg_type": self.msg_type,
            "sender": self.sender,
            "receivers": self.receivers,
            "session_id": self.session_id,
            "thread_id": self.thread_id,
            "payload": self.payload,
            "timestamp": self.timestamp,
            "reply_to": self.reply_to,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "AgentMessage":
        return cls(
            msg_id=data.get("msg_id", str(uuid.uuid4())[:8]),
            msg_type=data.get("msg_type", MessageType.REQUEST.value),
            sender=data.get("sender", ""),
            receivers=data.get("receivers", []),
            session_id=data.get("session_id", ""),
            thread_id=data.get("thread_id", ""),
            payload=data.get("payload", {}),
            timestamp=data.get("timestamp", time.time()),
            reply_to=data.get("reply_to"),
            metadata=data.get("metadata", {}),
        )

    def is_broadcast(self) -> bool:
        return not self.receivers

    def is_for_agent(self, agent_id: str) -> bool:
        return self.is_broadcast() or agent_id in self.receivers
