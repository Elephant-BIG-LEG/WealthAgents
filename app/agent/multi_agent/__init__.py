"""
多 Agent 投研机制：技术面、基本面、风险、反对者四角色 + A2A 通信、辩论、协商、任务分配
"""
from .coordinator import MultiAgentCoordinator
from .role_agents import (
    TechnicalAgent,
    FundamentalAgent,
    RiskAgent,
    DevilAdvocateAgent,
)
from .messages import AgentMessage, MessageType
from .bus import get_bus, AgentMessageBus

__all__ = [
    "MultiAgentCoordinator",
    "TechnicalAgent",
    "FundamentalAgent",
    "RiskAgent",
    "DevilAdvocateAgent",
    "AgentMessage",
    "MessageType",
    "get_bus",
    "AgentMessageBus",
]
