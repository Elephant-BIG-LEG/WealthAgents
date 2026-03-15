"""
四类角色 Agent：技术面、基本面、风险、反对者
每个角色有专属分析框架与提示，支持 A2A 通信：自主决定通信对象、收发消息、参与辩论与协商
"""
from typing import Dict, Any, List, Optional
import logging

from .messages import MessageType
from .bus import get_bus
from .communication import (
    decide_communication_targets,
    should_initiate_communication,
    send_message,
    receive_messages,
    broadcast_conclusion,
)

logger = logging.getLogger(__name__)


class BaseRoleAgent:
    """角色 Agent 基类，支持 A2A 消息收发与通信决策"""

    role_name: str = "base"
    system_prompt: str = "你是一位专业分析师。"

    def __init__(self, tools: Optional[Dict[str, Any]] = None, agent_id: Optional[str] = None):
        self.tools = tools or {}
        self.agent_id = agent_id or self.role_name

    def analyze(self, query: str, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        执行角色专属分析，返回统一结构：conclusion, confidence, evidence, role。
        """
        # 1. 调用工具获取数据
        tool_results = self._run_tools(query, context)
        
        # 2. 调用大模型生成分析结论
        try:
            from app.agentWorker.response import response_generator
            
            # 构建大模型输入
            analysis_prompt = f"{self.system_prompt}\n\n用户问题：{query}\n\n请基于以下数据进行分析，输出详细的分析结论、置信度（0-1之间）和关键证据：\n{tool_results}"
            
            # 调用大模型
            user_input = {
                "final_result": {
                    "tasks": [{"result": {"parsed_data": [{"title": f"{self.role_name}分析", "summary": analysis_prompt}]}}]
                },
                "user_request": analysis_prompt
            }
            
            response = response_generator.get_response(user_input)
            llm_response = response.get("response", "")
            
            # 3. 解析响应，提取结论、置信度和证据
            # 简单解析，实际可根据大模型输出格式优化
            conclusion = llm_response
            confidence = 0.8  # 可根据大模型输出或其他方式计算
            evidence = [str(tool_results)]
            
        except Exception as e:
            # 大模型调用失败时的降级处理
            conclusion = f"分析失败：{str(e)}"
            confidence = 0.3
            evidence = [str(tool_results)]
        
        return {
            "role": self.role_name,
            "conclusion": conclusion,
            "confidence": confidence,
            "evidence": evidence,
            "raw": tool_results
        }

    def get_inbox(self, session_id: Optional[str] = None, thread_id: Optional[str] = None) -> List[Any]:
        """拉取收件箱消息。"""
        return receive_messages(self.agent_id, session_id=session_id, thread_id=thread_id)

    def send_to(self, receivers: List[str], msg_type: str, payload: Dict[str, Any],
                session_id: str = "", thread_id: str = "", reply_to: Optional[str] = None) -> Any:
        """主动向指定 Agent 发送消息。"""
        return send_message(
            self.agent_id, receivers, msg_type, payload,
            session_id=session_id, thread_id=thread_id, reply_to=reply_to,
        )

    def broadcast_result(self, conclusion: Dict[str, Any], session_id: str = "", thread_id: str = "") -> Any:
        """广播己方结论（结果共享）。"""
        return broadcast_conclusion(self.agent_id, conclusion, session_id=session_id, thread_id=thread_id)

    def decide_who_to_talk_to(
        self,
        current_conclusions: List[Dict[str, Any]],
        query: str,
        message_history: Optional[List[Any]] = None,
    ) -> List[str]:
        """自主决定本轮回信对象。"""
        return decide_communication_targets(
            self.agent_id, current_conclusions, query, message_history or [],
        )

    def should_initiate(
        self,
        conclusions: List[Dict[str, Any]],
        message_history: List[Any],
        max_per_session: int = 2,
    ) -> bool:
        """是否主动发起通信（请求/邀请辩论/质疑）。"""
        return should_initiate_communication(
            self.agent_id, conclusions, message_history, max_initiative_per_session=max_per_session,
        )

    def process_allocated_tasks(self, session_id: str, thread_id: str, coordinator_id: str = "coordinator") -> List[Dict[str, Any]]:
        """
        处理收件箱中的 TASK_ALLOCATION，执行任务并向协调器回传 TASK_RESULT（协作任务分配）。
        """
        from .messages import MessageType
        inbox = self.get_inbox(session_id=session_id, thread_id=thread_id)
        results = []
        for msg in inbox:
            if getattr(msg, "msg_type", None) != MessageType.TASK_ALLOCATION.value:
                continue
            task = (getattr(msg, "payload", None) or {}).get("task", {})
            query = task.get("query", "")
            if not query:
                continue
            try:
                out = self.analyze(query, {"task": task})
                send_message(
                    self.agent_id,
                    [coordinator_id],
                    MessageType.TASK_RESULT.value,
                    {"task": task, "result": out},
                    session_id=session_id,
                    thread_id=thread_id,
                )
                results.append({"query": query, "result": out})
            except Exception as e:
                send_message(
                    self.agent_id,
                    [coordinator_id],
                    MessageType.TASK_RESULT.value,
                    {"task": task, "error": str(e)},
                    session_id=session_id,
                    thread_id=thread_id,
                )
        return results


class TechnicalAgent(BaseRoleAgent):
    """技术面 Agent：K 线、均线、MACD、量价等"""

    role_name = "technical"

    def __init__(self, tools: Optional[Dict[str, Any]] = None, agent_id: Optional[str] = None):
        super().__init__(tools=tools, agent_id=agent_id or self.role_name)
    system_prompt = (
        "你是技术面分析师。从 K 线、均线、MACD、KDJ、量价关系、支撑阻力等角度分析，"
        "给出短线/中线技术结论与置信度。输出需包含：结论、置信度(0-1)、关键指标摘要。"
    )

    # 直接使用基类的analyze方法，无需重写
    pass

    def _run_tools(self, query: str, context: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        if not self.tools:
            return {"message": "无可用工具，返回占位"}
        out = {}
        for name, fn in self.tools.items():
            if "data_analysis" in name or "visualization" in name:
                try:
                    out[name] = fn(query=query) if callable(fn) else {}
                except Exception as e:
                    out[name] = {"error": str(e)}
        return out


class FundamentalAgent(BaseRoleAgent):
    """基本面 Agent：财报、估值、ROE、现金流等"""

    role_name = "fundamental"

    def __init__(self, tools: Optional[Dict[str, Any]] = None, agent_id: Optional[str] = None):
        super().__init__(tools=tools, agent_id=agent_id or self.role_name)
    system_prompt = (
        "你是基本面分析师。从财报、估值(PE/PB)、ROE、毛利率、现金流、成长性等角度分析，"
        "给出中长期价值结论与置信度。输出需包含：结论、置信度(0-1)、关键财务指标。"
    )

    # 直接使用基类的analyze方法，无需重写
    pass

    def _run_tools(self, query: str, context: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        if not self.tools:
            return {"message": "无可用工具"}
        out = {}
        for name, fn in self.tools.items():
            if "financial" in name or "database" in name or "data_analysis" in name:
                try:
                    out[name] = fn(query=query) if callable(fn) else {}
                except Exception as e:
                    out[name] = {"error": str(e)}
        return out


class RiskAgent(BaseRoleAgent):
    """风险 Agent：波动率、回撤、VaR、风险等级"""

    role_name = "risk"

    def __init__(self, tools: Optional[Dict[str, Any]] = None, agent_id: Optional[str] = None):
        super().__init__(tools=tools, agent_id=agent_id or self.role_name)
    system_prompt = (
        "你是风险评估师。从波动率、最大回撤、VaR、流动性、杠杆等角度分析，"
        "给出风险等级与置信度。输出需包含：结论、置信度(0-1)、风险指标摘要。"
    )

    # 直接使用基类的analyze方法，无需重写
    pass

    def _run_tools(self, query: str, context: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        if not self.tools:
            return {"message": "无可用工具"}
        out = {}
        for name, fn in self.tools.items():
            if "risk" in name or "assessment" in name:
                try:
                    out[name] = fn(query=query) if callable(fn) else {}
                except Exception as e:
                    out[name] = {"error": str(e)}
        return out


class DevilAdvocateAgent(BaseRoleAgent):
    """反对者 Agent：质疑结论、指出盲区与反例"""

    role_name = "devil_advocate"

    def __init__(self, tools: Optional[Dict[str, Any]] = None, agent_id: Optional[str] = None):
        super().__init__(tools=tools, agent_id=agent_id or self.role_name)
    system_prompt = (
        "你是反对者/纠错角色。对已有分析结论提出质疑：列举反例、盲区、假设不成立的情形，"
        "给出反向观点与置信度。输出需包含：质疑点、反向结论、置信度(0-1)。"
    )

    def analyze(
        self,
        query: str,
        context: Optional[Dict[str, Any]] = None,
        other_conclusions: Optional[List[Dict[str, Any]]] = None,
    ) -> Dict[str, Any]:
        # 1. 调用工具获取数据
        tool_results = self._run_tools(query, context)
        
        # 2. 调用大模型生成分析结论
        try:
            from app.agentWorker.response import response_generator
            
            # 构建包含其他结论的分析提示
            other_conclusions_str = "\n\n其他角色分析结论：\n"
            for conclusion in other_conclusions or []:
                other_conclusions_str += f"{conclusion.get('role', '未知角色')}：{conclusion.get('conclusion', '')}\n"
            
            analysis_prompt = f"{self.system_prompt}\n\n用户问题：{query}\n\n{other_conclusions_str}\n\n请基于以下数据进行反对者分析，质疑其他结论，指出盲区与反例，输出详细的分析结论、置信度（0-1之间）和关键证据：\n{tool_results}"
            
            # 调用大模型
            user_input = {
                "final_result": {
                    "tasks": [{"result": {"parsed_data": [{"title": "反对者分析", "summary": analysis_prompt}]}}]
                },
                "user_request": analysis_prompt
            }
            
            response = response_generator.get_response(user_input)
            llm_response = response.get("response", "")
            
            # 3. 解析响应，提取结论、置信度和证据
            conclusion = llm_response
            confidence = 0.8
            evidence = [str(tool_results)]
            
        except Exception as e:
            # 大模型调用失败时的降级处理
            conclusion = f"分析失败：{str(e)}"
            confidence = 0.3
            evidence = [str(tool_results)]
        
        return {
            "role": self.role_name,
            "conclusion": conclusion,
            "confidence": confidence,
            "evidence": evidence,
            "counterpoints": other_conclusions or [],
            "raw": tool_results,
        }
