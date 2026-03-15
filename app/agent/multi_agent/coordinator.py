"""
多 Agent 协调器：A2A 通信、辩论、协商、任务分配与结果共享
支持多 Agent 并行执行以提高效率
"""
from typing import Dict, Any, List, Optional
from concurrent.futures import ThreadPoolExecutor, as_completed
import logging
import uuid

from .role_agents import TechnicalAgent, FundamentalAgent, RiskAgent, DevilAdvocateAgent
from .cross_validate import cross_validate_and_fuse
from .messages import MessageType
from .bus import get_bus
from .debate import detect_conflicts, run_debate
from .negotiation import run_negotiation

logger = logging.getLogger(__name__)


class MultiAgentCoordinator:
    """
    投研多 Agent 协调器，支持完整 A2A：
    - 统一消息总线：各 Agent 通过总线收发消息
    - Agent 自主通信：决定通信对象、主动发起
    - 辩论机制：冲突检测 → 多轮陈述与证据交换
    - 协商机制：投票/妥协达成共识
    - 任务分配与结果共享：TASK_ALLOCATION / TASK_RESULT / BROADCAST
    """

    def __init__(
        self,
        tools: Optional[Dict[str, Any]] = None,
        run_devil_after_others: bool = True,
        fuse_method: str = "weighted",
        enable_debate: bool = True,
        enable_negotiation: bool = True,
        negotiation_method: str = "compromise",
        max_debate_rounds: int = 2,
        parallel_agents: bool = True,
        max_worker_agents: int = 4,
    ):
        self.tools = tools or {}
        self.run_devil_after_others = run_devil_after_others
        self.fuse_method = fuse_method
        self.enable_debate = enable_debate
        self.enable_negotiation = enable_negotiation
        self.negotiation_method = negotiation_method
        self.max_debate_rounds = max_debate_rounds
        self.parallel_agents = parallel_agents
        self.max_worker_agents = max(1, min(max_worker_agents, 8))
        self.bus = get_bus()
        self.technical = TechnicalAgent(tools=self.tools)
        self.fundamental = FundamentalAgent(tools=self.tools)
        self.risk = RiskAgent(tools=self.tools)
        self.devil = DevilAdvocateAgent(tools=self.tools)
        self._agent_map = {
            "technical": self.technical,
            "fundamental": self.fundamental,
            "risk": self.risk,
            "devil_advocate": self.devil,
        }

    def run(
        self,
        query: str,
        context: Optional[Dict[str, Any]] = None,
        roles: Optional[List[str]] = None,
        session_id: Optional[str] = None,
        enable_a2a: bool = True,
    ) -> Dict[str, Any]:
        """
        执行多角色分析 + A2A 通信（可选）+ 辩论 + 协商 + 结果融合。
        """
        session_id = session_id or str(uuid.uuid4())[:12]
        roles = roles or ["technical", "fundamental", "risk", "devil_advocate"]
        agent_map = self._agent_map
        conclusions: List[Dict[str, Any]] = []

        # ---------- 1. 各角色分析（并行执行）并可选广播结论（结果共享）----------
        def _analyze_one(role: str) -> Dict[str, Any]:
            if role not in agent_map:
                return {"role": role, "conclusion": "", "confidence": 0, "error": "unknown role"}
            try:
                return agent_map[role].analyze(query, context)
            except Exception as e:
                logger.warning(f"角色 {role} 执行失败: {e}")
                return {"role": role, "conclusion": "", "confidence": 0, "evidence": [], "error": str(e)}

        if self.run_devil_after_others and "devil_advocate" in roles:
            other_roles = [r for r in roles if r != "devil_advocate" and r in agent_map]
            if self.parallel_agents and len(other_roles) > 1:
                results_by_role: Dict[str, Dict[str, Any]] = {}
                with ThreadPoolExecutor(max_workers=min(len(other_roles), self.max_worker_agents)) as executor:
                    future_to_role = {executor.submit(_analyze_one, r): r for r in other_roles}
                    for future in as_completed(future_to_role):
                        r = future_to_role[future]
                        try:
                            results_by_role[r] = future.result()
                        except Exception as e:
                            results_by_role[r] = {"role": r, "conclusion": "", "confidence": 0, "evidence": [], "error": str(e)}
                conclusions = [results_by_role[r] for r in other_roles]
            else:
                conclusions = [_analyze_one(r) for r in other_roles]
            for i, r in enumerate(other_roles):
                if enable_a2a and r in agent_map:
                    agent_map[r].broadcast_result(conclusions[i], session_id=session_id)
            other_conclusions = conclusions.copy()
            try:
                devil_out = self.devil.analyze(query, context, other_conclusions=other_conclusions)
                conclusions.append(devil_out)
                if enable_a2a:
                    self.devil.broadcast_result(devil_out, session_id=session_id)
            except Exception as e:
                logger.warning(f"反对者角色执行失败: {e}")
                conclusions.append({"role": "devil_advocate", "conclusion": "", "confidence": 0, "error": str(e)})
        else:
            roles_to_run = [r for r in roles if r in agent_map]
            if self.parallel_agents and len(roles_to_run) > 1:
                results_by_role = {}
                with ThreadPoolExecutor(max_workers=min(len(roles_to_run), self.max_worker_agents)) as executor:
                    future_to_role = {executor.submit(_analyze_one, r): r for r in roles_to_run}
                    for future in as_completed(future_to_role):
                        r = future_to_role[future]
                        try:
                            results_by_role[r] = future.result()
                        except Exception as e:
                            results_by_role[r] = {"role": r, "conclusion": "", "confidence": 0, "error": str(e)}
                conclusions = [results_by_role[r] for r in roles_to_run]
            else:
                conclusions = [_analyze_one(r) for r in roles_to_run]
            for i, r in enumerate(roles_to_run):
                if enable_a2a and r in agent_map:
                    agent_map[r].broadcast_result(conclusions[i], session_id=session_id)

        # ---------- 2. Agent 自主通信：拉取收件箱并决定是否主动发起 ----------
        a2a_log: List[Dict[str, Any]] = []
        if enable_a2a:
            for r in roles:
                if r not in agent_map:
                    continue
                agent = agent_map[r]
                inbox = agent.get_inbox(session_id=session_id)
                a2a_log.append({"agent": r, "inbox_count": len(inbox)})
                if agent.should_initiate(conclusions, inbox):
                    targets = agent.decide_who_to_talk_to(conclusions, query, inbox)
                    if targets:
                        my_conclusion = next((c for c in conclusions if c.get("role") == r), {})
                        agent.send_to(
                            targets,
                            MessageType.REQUEST.value,
                            {"query": query, "my_conclusion": my_conclusion},
                            session_id=session_id,
                        )
                        a2a_log.append({"agent": r, "initiative_to": targets})

        # ---------- 3. 辩论：检测冲突并多轮陈述/证据交换 ----------
        debate_result: Dict[str, Any] = {}
        if enable_a2a and self.enable_debate:
            conflicts = detect_conflicts(conclusions)
            if conflicts:
                debate_result = run_debate(
                    session_id, conclusions, list(agent_map.keys()), max_rounds=self.max_debate_rounds,
                )
                debate_result["conflicts_detected"] = len(conflicts)

        # ---------- 4. 协商：投票或妥协达成共识 ----------
        negotiation_result: Dict[str, Any] = {}
        if self.enable_negotiation:
            thread_id = debate_result.get("thread_id", f"neg_{uuid.uuid4().hex[:8]}")
            negotiation_result = run_negotiation(
                session_id, thread_id, conclusions, method=self.negotiation_method,
                debate_messages=debate_result.get("messages"),
            )

        # ---------- 5. 融合（沿用原有加权/保守）----------
        fused = cross_validate_and_fuse(conclusions, method=self.fuse_method)
        if negotiation_result.get("consensus"):
            fused["negotiation_consensus"] = negotiation_result["consensus"]
            fused["negotiation_confidence"] = negotiation_result.get("confidence")

        return {
            "conclusions": conclusions,
            "fused": fused,
            "query": query,
            "session_id": session_id,
            "a2a": {"log": a2a_log, "debate": debate_result, "negotiation": negotiation_result},
        }

    def allocate_tasks(
        self,
        session_id: str,
        task_specs: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """
        协作任务分配：通过总线向指定 Agent 发送 TASK_ALLOCATION，各 Agent 处理并回传 TASK_RESULT。
        task_specs: [{"agent_id": "technical", "task": {"query": "...", "type": "..."}}, ...]
        """
        thread_id = f"task_{uuid.uuid4().hex[:8]}"
        for spec in task_specs:
            agent_id = spec.get("agent_id")
            task = spec.get("task", {})
            if not agent_id or agent_id not in self._agent_map:
                continue
            self.bus.send(
                "coordinator",
                [agent_id],
                MessageType.TASK_ALLOCATION.value,
                {"task": task, "session_id": session_id, "thread_id": thread_id},
                session_id=session_id,
                thread_id=thread_id,
            )
        agents_to_run = [spec.get("agent_id") for spec in task_specs if spec.get("agent_id") in self._agent_map]
        if self.parallel_agents and len(agents_to_run) > 1:
            def _process(agent_id: str) -> None:
                self._agent_map[agent_id].process_allocated_tasks(session_id, thread_id, "coordinator")
            with ThreadPoolExecutor(max_workers=min(len(agents_to_run), self.max_worker_agents)) as executor:
                list(executor.map(_process, agents_to_run))
        else:
            for agent_id in agents_to_run:
                self._agent_map[agent_id].process_allocated_tasks(session_id, thread_id, "coordinator")
        results = []
        msgs = self.bus.receive("coordinator", limit=len(task_specs) * 2, session_id=session_id, thread_id=thread_id)
        for m in msgs:
            if getattr(m, "msg_type", None) == MessageType.TASK_RESULT.value:
                payload = getattr(m, "payload", {})
                results.append({"agent_id": getattr(m, "sender", ""), "payload": payload})
        return {"thread_id": thread_id, "allocated": len(task_specs), "results": results}
