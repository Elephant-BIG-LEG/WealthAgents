"""
A2A 消息队列 / 事件总线
Agent 通过总线发布、订阅、按接收者或会话拉取消息
"""
from typing import Dict, Any, List, Optional, Callable
from collections import deque
import threading
import logging
import time

from .messages import AgentMessage, MessageType

logger = logging.getLogger(__name__)


class AgentMessageBus:
    """
    进程内消息总线：按接收者维护收件箱，支持按 session/thread 查询。
    可扩展为 Redis/队列后端。
    """

    def __init__(self, max_inbox_size: int = 500):
        self._inbox: Dict[str, deque] = {}  # agent_id -> deque of AgentMessage
        self._broadcast_log: deque = deque(maxlen=200)  # 广播消息供订阅者消费
        self._max_inbox_size = max_inbox_size
        self._lock = threading.RLock()
        self._subscribers: Dict[str, List[Callable[[AgentMessage], None]]] = {}  # topic -> callbacks

    def _ensure_inbox(self, agent_id: str) -> deque:
        with self._lock:
            if agent_id not in self._inbox:
                self._inbox[agent_id] = deque(maxlen=self._max_inbox_size)
            return self._inbox[agent_id]

    def publish(self, message: AgentMessage) -> None:
        """发布消息：根据 receivers 投递到对应收件箱，无接收者则视为广播。"""
        if not isinstance(message, AgentMessage):
            message = AgentMessage.from_dict(message) if isinstance(message, dict) else message
        with self._lock:
            if message.is_broadcast():
                self._broadcast_log.append(message)
                for agent_id, inbox in self._inbox.items():
                    if agent_id != message.sender:
                        inbox.append(message)
                self._notify_topic("broadcast", message)
            else:
                for recv in message.receivers:
                    inbox = self._ensure_inbox(recv)
                    inbox.append(message)
                self._notify_topic(message.msg_type, message)
        logger.debug(f"A2A publish: {message.sender} -> {message.receivers} type={message.msg_type}")

    def send(self, sender: str, receivers: List[str], msg_type: str, payload: Dict[str, Any],
             session_id: str = "", thread_id: str = "", reply_to: Optional[str] = None) -> AgentMessage:
        """便捷发送：构造 AgentMessage 并 publish。"""
        msg = AgentMessage(
            msg_type=msg_type,
            sender=sender,
            receivers=receivers,
            session_id=session_id,
            thread_id=thread_id,
            payload=payload,
            reply_to=reply_to,
        )
        self.publish(msg)
        return msg

    def receive(self, agent_id: str, limit: int = 50, since_ts: Optional[float] = None,
                session_id: Optional[str] = None, thread_id: Optional[str] = None) -> List[AgentMessage]:
        """从 agent 收件箱拉取消息；可选按 session/thread 过滤、按时间过滤。"""
        inbox = self._ensure_inbox(agent_id)
        with self._lock:
            out: List[AgentMessage] = []
            for _ in range(min(limit, len(inbox))):
                if not inbox:
                    break
                m = inbox.popleft()
                if since_ts is not None and m.timestamp < since_ts:
                    inbox.appendleft(m)
                    break
                if session_id is not None and m.session_id != session_id:
                    inbox.appendleft(m)
                    continue
                if thread_id is not None and m.thread_id != thread_id:
                    inbox.appendleft(m)
                    continue
                out.append(m)
            return out

    def peek(self, agent_id: str, limit: int = 20) -> List[AgentMessage]:
        """查看收件箱但不移除。"""
        inbox = self._ensure_inbox(agent_id)
        with self._lock:
            return list(inbox)[:limit]

    def subscribe(self, topic: str, callback: Callable[[AgentMessage], None]) -> None:
        """订阅某类消息（按 msg_type 或 'broadcast'）。"""
        with self._lock:
            if topic not in self._subscribers:
                self._subscribers[topic] = []
            self._subscribers[topic].append(callback)

    def _notify_topic(self, topic: str, message: AgentMessage) -> None:
        for cb in self._subscribers.get(topic, []):
            try:
                cb(message)
            except Exception as e:
                logger.warning(f"Bus subscriber error: {e}")

    def get_broadcast_log(self, limit: int = 50) -> List[AgentMessage]:
        """获取最近广播消息（不按接收者）。"""
        with self._lock:
            return list(self._broadcast_log)[-limit:]

    def clear_inbox(self, agent_id: str) -> None:
        with self._lock:
            if agent_id in self._inbox:
                self._inbox[agent_id].clear()


# 单例总线，Coordinator 与各 Agent 共用
_global_bus: Optional[AgentMessageBus] = None


def get_bus() -> AgentMessageBus:
    global _global_bus
    if _global_bus is None:
        _global_bus = AgentMessageBus()
    return _global_bus


def set_bus(bus: AgentMessageBus) -> None:
    global _global_bus
    _global_bus = bus
