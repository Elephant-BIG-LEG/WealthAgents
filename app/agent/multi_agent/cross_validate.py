"""
多 Agent 结论交叉验证与融合
"""
from typing import List, Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)


def cross_validate_and_fuse(
    conclusions: List[Dict[str, Any]],
    method: str = "weighted",
) -> Dict[str, Any]:
    """
    对多角色结论做交叉验证与融合。
    conclusions: 各角色 analyze() 返回的列表，每项含 role, conclusion, confidence, evidence。
    method: "weighted" 按置信度加权；"majority" 取多数一致；"conservative" 取最保守（风险优先）。
    """
    if not conclusions:
        return {"fused_conclusion": "", "confidence": 0.0, "roles_used": [], "conflicts": []}

    roles_used = [c.get("role", "") for c in conclusions if c.get("role")]
    conflicts: List[str] = []

    if method == "weighted":
        total_conf = sum(c.get("confidence", 0) for c in conclusions)
        if total_conf <= 0:
            total_conf = 1.0
        parts = []
        for c in conclusions:
            w = c.get("confidence", 0) / total_conf
            concl = c.get("conclusion", "") or str(c.get("raw", ""))[:200]
            if concl:
                parts.append(f"[{c.get('role', '')}] {concl}")
        fused = " | ".join(parts) if parts else "无有效结论"
        avg_conf = total_conf / len(conclusions) if conclusions else 0
        return {
            "fused_conclusion": fused,
            "confidence": avg_conf,
            "roles_used": roles_used,
            "conflicts": conflicts,
        }

    if method == "conservative":
        # 风险角色结论优先体现
        risk_c = next((c for c in conclusions if c.get("role") == "risk"), None)
        devil_c = next((c for c in conclusions if c.get("role") == "devil_advocate"), None)
        parts = []
        if risk_c and risk_c.get("conclusion"):
            parts.append(f"[风险] {risk_c['conclusion']}")
        if devil_c and devil_c.get("conclusion"):
            parts.append(f"[反对者] {devil_c['conclusion']}")
        for c in conclusions:
            if c.get("role") not in ("risk", "devil_advocate") and c.get("conclusion"):
                parts.append(f"[{c['role']}] {c['conclusion']}")
        fused = " | ".join(parts) if parts else "无有效结论"
        return {
            "fused_conclusion": fused,
            "confidence": min(c.get("confidence", 1) for c in conclusions) if conclusions else 0,
            "roles_used": roles_used,
            "conflicts": conflicts,
        }

    # default: weighted
    return cross_validate_and_fuse(conclusions, method="weighted")
