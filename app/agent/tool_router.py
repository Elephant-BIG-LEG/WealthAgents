"""
工具路由：关键词触发 + 可选 LLM 工具选择
为 Planner 提供「关键词 → 工具」映射与基于描述的 LLM 工具推荐
"""
from typing import Dict, List, Any, Optional
import logging

logger = logging.getLogger(__name__)

# 关键词 → 工具名（可被 Planner 用于优先路由）
KEYWORD_TO_TOOL: Dict[str, List[str]] = {
    "行情": ["market_data_adapter", "web_scraping_tool"],
    "股价": ["market_data_adapter", "stock_data_tool"],
    "实时": ["market_data_adapter"],
    "涨跌": ["market_data_adapter", "data_analysis"],
    "财报": ["financial_report_adapter", "database_tool"],
    "年报": ["financial_report_adapter"],
    "季报": ["financial_report_adapter"],
    "财务": ["financial_report_adapter", "data_analysis"],
    "营收": ["financial_report_adapter"],
    "利润": ["financial_report_adapter"],
    "风险": ["risk_assessment_adapter", "risk_assessment"],
    "评估": ["risk_assessment", "data_analysis"],
    "波动": ["risk_assessment_adapter"],
    "回撤": ["risk_assessment_adapter"],
    "K线": ["data_analysis", "visualization_tool"],
    "均线": ["data_analysis"],
    "MACD": ["data_analysis"],
    "基本面": ["financial_report_adapter", "data_analysis"],
    "估值": ["financial_report_adapter", "data_analysis"],
    "pe": ["financial_report_adapter"],
    "pb": ["financial_report_adapter"],
    "收集": ["web_scraping_tool", "database_tool"],
    "采集": ["web_scraping_tool"],
    "新闻": ["web_scraping_tool", "news_analysis"],
    "资讯": ["web_scraping_tool", "news_analysis"],
    "热点": ["web_scraping_tool", "news_analysis"],
    "市场": ["market_data_adapter", "web_scraping_tool", "data_analysis"],
    "分析": ["data_analysis", "web_scraping_tool"],
    "趋势": ["data_analysis", "market_data_adapter"],
    "股票": ["market_data_adapter", "stock_data_tool", "data_analysis"],
    "查询": ["database_tool", "general_query"],
}


class ToolRouter:
    """
    智能工具选择器：优先使用 LLM 进行工具选择，关键词匹配作为辅助和后备方案。
    """

    def __init__(self, enable_llm_selection: bool = True):
        self.enable_llm_selection = enable_llm_selection
        self._keyword_to_tool = dict(KEYWORD_TO_TOOL)

    def route_by_keywords(self, query: str, available_tools: List[str]) -> List[str]:
        """
        根据查询中的关键词返回推荐工具列表（用于快速过滤和后备方案）。
        """
        q = (query or "").strip().lower()
        scored: Dict[str, int] = {}
        for keyword, tools in self._keyword_to_tool.items():
            if keyword in q:
                for t in tools:
                    if t in available_tools:
                        scored[t] = scored.get(t, 0) + 1
        ordered = sorted(scored.keys(), key=lambda x: -scored[x])
        return ordered if ordered else list(available_tools)[:5]

    def select_tools_with_llm(
        self,
        query: str,
        tool_definitions: List[Dict[str, Any]],
        top_k: int = 5,
    ) -> List[str]:
        """
        使用 LLM 根据用户查询与工具描述选择最匹配的工具。
        tool_definitions: [{"name": "...", "description": "..."}, ...]
        返回选中的工具 name 列表。
        """
        if not self.enable_llm_selection or not tool_definitions:
            return []
        try:
            import os
            api_key = os.getenv("DASHSCOPE_API_KEY") or os.getenv("OPENAI_API_KEY")
            if not api_key:
                logger.warning("未配置 LLM API Key，跳过 LLM 工具选择")
                return []
            # 简单 HTTP 调用 DashScope 或兼容 OpenAI 的 chat
            try:
                import openai
                client = openai.OpenAI(
                    api_key=os.getenv("OPENAI_API_KEY") or api_key,
                    base_url=os.getenv("DASHSCOPE_BASE_URL") or os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1"),
                )
                # 构建更详细的工具描述，帮助 LLM 做出更准确的选择
                tools_desc = "\n".join(
                    [f"工具名称：{d.get('name', '')}\n描述：{d.get('description', '')}\n" for d in tool_definitions]
                )
                prompt = f"""
你是一个智能工具选择助手，请根据用户的查询，从以下可用工具中选择最适合的工具。

用户查询：{query}

可用工具：
{tools_desc}

请严格按照以下要求输出：
1. 只返回工具名称列表，用英文逗号分隔
2. 最多选择{top_k}个最相关的工具
3. 按照相关性从高到低排序
4. 不要添加任何解释或说明
5. 不要使用任何标点符号，除了英文逗号
6. 确保返回的工具名称与提供的完全一致

例如：tool1,tool2,tool3
"""
                resp = client.chat.completions.create(
                    model=os.getenv("LLM_MODEL", "gpt-3.5-turbo"),
                    messages=[{"role": "user", "content": prompt}],
                    max_tokens=200,
                    temperature=0.1,  # 降低随机性，提高一致性
                )
                text = (resp.choices[0].message.content or "").strip()
                names = [n.strip() for n in text.replace("，", ",").split(",") if n.strip()]
                # 过滤出有效的工具名称
                valid_tool_names = {d.get("name") for d in tool_definitions}
                return [n for n in names if n in valid_tool_names][:top_k]
            except Exception as e:
                logger.warning(f"LLM 工具选择失败: {e}")
                return []
        except ImportError:
            logger.warning("openai 未安装，跳过 LLM 工具选择")
            return []

    def recommend_tools(
        self,
        query: str,
        available_tools: List[str],
        tool_definitions: Optional[List[Dict[str, Any]]] = None,
        use_llm: bool = True,
    ) -> List[str]:
        """
        智能推荐工具：
        1. 优先使用 LLM 进行精准工具选择
        2. 若 LLM 不可用或失败，使用关键词匹配作为后备方案
        3. 关键词匹配还用于过滤可用工具，减少 LLM 需要处理的工具数量
        """
        # 步骤1：使用关键词匹配快速过滤，减少 LLM 需要处理的工具数量
        keyword_filtered_tools = self.route_by_keywords(query, available_tools)
        
        # 步骤2：如果启用 LLM 且有工具定义，直接使用 LLM 选择工具
        if use_llm and tool_definitions:
            # 过滤工具定义，只保留可用的工具
            filtered_tool_defs = [
                d for d in tool_definitions 
                if d.get("name") in available_tools
            ]
            
            # 优先使用 LLM 进行工具选择
            llm_tools = self.select_tools_with_llm(query, filtered_tool_defs, top_k=5)
            if llm_tools:
                logger.info(f"LLM 工具选择结果: {llm_tools}")
                return llm_tools
            
        # 步骤3：若 LLM 不可用或失败，使用关键词匹配结果作为后备
        logger.info(f"使用关键词匹配结果作为后备: {keyword_filtered_tools}")
        return keyword_filtered_tools[:10]
