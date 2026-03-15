"""
A2A 协商机制：投票、妥协、动态调整观点、达成共识
"""
from typing import Dict, Any, List, Optional
import logging

from .messages import AgentMessage, MessageType
from .bus import get_bus

logger = logging.getLogger(__name__)


def negotiate_by_voting(
    conclusions: List[Dict[str, Any]],
    options: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """
    对离散选项投票；若无 options 则对「结论摘要」聚类后取多数。
    returns: { "winner": option, "votes": { option: count }, "tie": bool }
    """
    if options:
        votes = {o: 0 for o in options}
        for c in conclusions:
            concl = (c.get("conclusion") or "").strip() or str(c.get("raw", ""))[:100]
            for o in options:
                if o in concl or concl in o:
                    votes[o] = votes.get(o, 0) + 1
                    break
            else:
                if options:
                    votes[options[0]] = votes.get(options[0], 0) + 0
        total = sum(votes.values())
        if total == 0:
            return {"winner": options[0] if options else "", "votes": votes, "tie": True}
        best = max(votes, key=votes.get)
        tie = sum(1 for v in votes.values() if v == votes[best]) > 1
        return {"winner": best, "votes": votes, "tie": tie}
    # 无选项：按结论文本归类，计票
    labels: List[str] = []
    for c in conclusions:
        concl = (c.get("conclusion") or "").strip() or str(c.get("raw", ""))[:80]
        labels.append(concl or "弃权")
    from collections import Counter
    cnt = Counter(labels)
    if not cnt:
        return {"winner": "", "votes": {}, "tie": True}
    best_label, best_count = cnt.most_common(1)[0]
    tie = sum(1 for v in cnt.values() if v == best_count) > 1
    return {"winner": best_label, "votes": dict(cnt), "tie": tie}


def negotiate_by_compromise(
    conclusions: List[Dict[str, Any]],
    weights: Optional[Dict[str, float]] = None,
) -> Dict[str, Any]:
    """
    妥协/折中：按置信度或给定权重加权融合结论文本与置信度。
    """
    if not conclusions:
        return {"fused_conclusion": "", "fused_confidence": 0.0, "contributions": []}
    weights = weights or {}
    total_w = 0.0
    parts = []
    for c in conclusions:
        w = weights.get(c.get("role", ""), c.get("confidence", 0.5))
        total_w += w
        concl = c.get("conclusion", "") or str(c.get("raw", ""))[:200]
        if concl:
            parts.append((w, concl, c.get("role", "")))
    if total_w <= 0:
        total_w = 1.0
    fused_parts = [p[1] for p in sorted(parts, key=lambda x: -x[0])]
    fused_conclusion = " | ".join(fused_parts) if fused_parts else "无共识"
    fused_confidence = sum(c.get("confidence", 0) for c in conclusions) / len(conclusions) if conclusions else 0
    return {
        "fused_conclusion": fused_conclusion,
        "fused_confidence": fused_confidence,
        "contributions": [{"role": p[2], "weight": p[0] / total_w} for p in parts],
    }


def run_negotiation(
    session_id: str,
    thread_id: str,
    conclusions: List[Dict[str, Any]],
    method: str = "compromise",
    debate_messages: Optional[List[Dict[str, Any]]] = None,
) -> Dict[str, Any]:
    """
    执行协商：可选投票或妥协。
    debate_messages 可为辩论后的消息，用于在协商时考虑对方证据（当前实现仍仅用 conclusions）。
    """
    if method == "vote":
        result = negotiate_by_voting(conclusions)
        return {
            "method": "vote",
            "consensus": result.get("winner", ""),
            "tie": result.get("tie", False),
            "votes": result.get("votes", {}),
        }
    result = negotiate_by_compromise(conclusions)
    return {
        "method": "compromise",
        "consensus": result.get("fused_conclusion", ""),
        "confidence": result.get("fused_confidence", 0),
        "contributions": result.get("contributions", []),
    }
