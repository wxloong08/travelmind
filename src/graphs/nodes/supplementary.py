"""
Fallback 补全搜索节点

当 Planning 节点发现缺少关键信息时，触发此节点进行一次性的补充搜索。
"""

from datetime import datetime
from typing import Any

import structlog

from src.graphs.state import AgentState
from src.tools.search import get_bocha_client

logger = structlog.get_logger()


async def supplementary_search_node(state: AgentState) -> dict[str, Any]:
    """
    补全搜索节点
    
    执行针对性的搜索查询，并将结果追加到 guide_context 中
    """
    logger.info("Node: supplementary_search")
    
    fallback_query = state.get("fallback_query")
    current_count = state.get("supplementary_search_count", 0)
    
    # 安全检查：虽然图结构应该保证不循环，但双重检查总是好的
    if not fallback_query or current_count >= 1:
        logger.warning(
            "Skipping supplementary search", 
            query=bool(fallback_query), 
            count=current_count
        )
        return {"next_action": "plan"}
    
    updates: dict[str, Any] = {
        "updated_at": datetime.now().isoformat(),
        "supplementary_search_count": current_count + 1,
        "next_action": "plan",  # 搜完后返回规划节点
    }
    
    try:
        client = get_bocha_client()
        logger.info("Executing supplementary search", query=fallback_query)
        
        # 执行搜索
        results, _ = await client.search(fallback_query, count=3, freshness=None)
        
        if not results:
            logger.warning("Supplementary search returned no results")
            return updates
            
        # 格式化结果
        new_context_parts = [f"\n\n### 🔍 补充搜索结果 (查询: {fallback_query})\n"]
        for r in results:
            title = r.title
            snippet = r.snippet
            source = r.source or "未知来源"
            new_context_parts.append(f"- 【{title}】({source}): {snippet}")
            
        new_context = "\n".join(new_context_parts)
        
        # 追加到 travel_preference.guide_context
        travel_pref = state.get("travel_preference") or {}
        current_guide_context = travel_pref.get("guide_context", "")
        
        # 避免重复添加 (简单检查)
        if fallback_query not in current_guide_context:
            updated_guide_context = current_guide_context + new_context
            travel_pref["guide_context"] = updated_guide_context
            updates["travel_preference"] = travel_pref
            logger.info("Supplementary info appended to context", length=len(new_context))
        else:
            logger.info("Duplicate context detected, skipping append")
            
    except Exception as e:
        logger.error("Supplementary search failed", error=str(e))
        # 即使失败也返回 plan，避免死循环
        
    return updates
