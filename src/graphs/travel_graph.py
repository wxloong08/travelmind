"""
LangGraph 旅游规划工作流

定义完整的 Agent 工作流图
"""

from typing import Any

import structlog
from langchain_core.messages import HumanMessage
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, StateGraph

from src.config import settings
from src.graphs.nodes import (
    planning_node,
    research_node,
    respond_node,
    route_after_research,
    route_after_understand,
    understand_intent_node,
)
from src.graphs.state import AgentState, create_initial_state

logger = structlog.get_logger()


def create_travel_graph() -> StateGraph:
    """
    创建旅游规划工作流图

    工作流结构：
    START -> understand_intent -> [research | respond]
                                     |
                                     v
                                 planning
                                     |
                                     v
                                  respond -> END
    """
    # 创建状态图
    workflow = StateGraph(AgentState)

    # 添加节点
    workflow.add_node("understand_intent", understand_intent_node)
    workflow.add_node("research", research_node)
    workflow.add_node("planning", planning_node)
    workflow.add_node("respond", respond_node)

    # 设置入口点
    workflow.set_entry_point("understand_intent")

    # 添加条件边
    workflow.add_conditional_edges(
        "understand_intent",
        route_after_understand,
        {
            "research": "research",
            "respond": "respond",
        },
    )

    workflow.add_conditional_edges(
        "research",
        route_after_research,
        {
            "plan": "planning",
            "respond": "respond",
        },
    )

    # 规划完成后进入响应
    workflow.add_edge("planning", "respond")

    # 响应后结束
    workflow.add_edge("respond", END)

    return workflow


def _get_checkpointer():
    """
    获取检查点存储器

    优先使用 Redis（生产环境），回退到内存（开发环境）
    """
    # 尝试使用 Redis
    if settings.redis_url:
        try:
            from langgraph.checkpoint.redis import RedisSaver
            import redis

            # 测试 Redis 连接
            client = redis.from_url(settings.redis_url)
            client.ping()

            logger.info("Using Redis checkpointer for session persistence")
            return RedisSaver(conn=client)
        except ImportError:
            logger.warning("langgraph-checkpoint-redis not installed, falling back to memory")
        except Exception as e:
            logger.warning(f"Redis connection failed: {e}, falling back to memory")

    # 回退到内存存储
    logger.warning(
        "Using in-memory checkpointer - sessions will be lost on restart! "
        "Configure REDIS_URL for production use."
    )
    return MemorySaver()


# 创建带检查点的图
_checkpointer = _get_checkpointer()


def get_compiled_graph():
    """获取编译后的图"""
    workflow = create_travel_graph()
    return workflow.compile(checkpointer=_checkpointer)


# 全局图实例
travel_graph = get_compiled_graph()


async def run_travel_agent(
    user_input: str,
    session_id: str | None = None,
    initial_state: AgentState | None = None,
) -> dict[str, Any]:
    """
    运行旅游规划 Agent

    Args:
        user_input: 用户输入
        session_id: 会话 ID（用于多轮对话）
        initial_state: 初始状态（可选）

    Returns:
        包含响应和状态的字典
    """
    logger.info("Running travel agent", session_id=session_id, input_length=len(user_input))

    # 准备初始状态
    if initial_state is None:
        initial_state = create_initial_state(session_id)

    # 添加用户消息
    state_with_message: AgentState = {
        **initial_state,
        "messages": initial_state["messages"] + [HumanMessage(content=user_input)],
    }

    # 配置
    config = {
        "configurable": {
            "thread_id": session_id or initial_state["session_id"],
        },
    }

    # 执行图
    try:
        final_state = await travel_graph.ainvoke(state_with_message, config=config)

        # 提取最后的 AI 响应
        ai_response = ""
        for msg in reversed(final_state.get("messages", [])):
            if hasattr(msg, "content") and not isinstance(msg, HumanMessage):
                ai_response = msg.content
                break

        logger.info(
            "Agent completed",
            session_id=session_id,
            task_type=final_state.get("task_type"),
            phase=final_state.get("planning_phase"),
        )

        return {
            "response": ai_response,
            "session_id": final_state.get("session_id"),
            "task_type": final_state.get("task_type"),
            "planning_phase": final_state.get("planning_phase"),
            "has_plan": final_state.get("travel_plan") is not None,
            "collected_pois_count": len(final_state.get("collected_pois", [])),
        }

    except Exception as e:
        logger.error("Agent execution failed", error=str(e), session_id=session_id)
        raise


async def stream_travel_agent(
    user_input: str,
    session_id: str | None = None,
):
    """
    流式运行旅游规划 Agent

    返回前端期望的流式事件格式：
    - {type: "start", session_id: ...}
    - {type: "token", content: ...}
    - {type: "end", itinerary: [...], destination_detected: ..., ...}
    """
    import traceback
    
    logger.info("Streaming travel agent started", 
                session_id=session_id, 
                input_preview=user_input[:100])

    initial_state = create_initial_state(session_id)
    actual_session_id = session_id or initial_state["session_id"]
    
    state_with_message: AgentState = {
        **initial_state,
        "messages": [HumanMessage(content=user_input)],
    }

    config = {
        "configurable": {
            "thread_id": actual_session_id,
        },
    }

    # 发送开始事件
    yield {
        "type": "start",
        "session_id": actual_session_id,
    }

    final_state = None
    ai_response = ""

    try:
        # 关键修复：在工作流执行周围添加 try-except
        async for event in travel_graph.astream(state_with_message, config=config):
            for node_name, node_output in event.items():
                # 改为 info 级别，便于调试
                logger.info("Stream node executed", 
                           node=node_name, 
                           output_keys=list(node_output.keys()) if isinstance(node_output, dict) else "non-dict")
                
                # 保存最终状态
                if final_state is None:
                    final_state = node_output
                else:
                    final_state = {**final_state, **node_output}
                
                # 从 respond 节点提取 AI 响应
                if node_name == "respond" and node_output.get("messages"):
                    for msg in node_output["messages"]:
                        if hasattr(msg, "content"):
                            ai_response = msg.content
                            logger.info("AI response extracted", content_length=len(ai_response))
                            # 发送完整内容作为一个 token 事件
                            yield {
                                "type": "token",
                                "content": ai_response,
                            }
                            
    except Exception as e:
        # 关键修复：捕获并记录工作流执行中的异常
        logger.error(
            "Workflow execution failed",
            error=str(e),
            error_type=type(e).__name__,
            traceback=traceback.format_exc(),
            session_id=actual_session_id,
        )
        # 重新抛出异常，让上层 generate() 处理
        raise

    # 构建最终元数据
    end_event: dict[str, Any] = {
        "type": "end",
        "session_id": actual_session_id,
    }

    if final_state:
        # 目的地检测
        travel_pref = final_state.get("travel_preference") or {}
        if travel_pref.get("destination"):
            end_event["destination_detected"] = travel_pref["destination"]
        
        # 状态更新
        if final_state.get("travel_plan"):
            end_event["status_update"] = "Created"
        else:
            end_event["status_update"] = "Planning"
        
        # 天气信息
        weather_info = final_state.get("weather_info")
        if weather_info:
            end_event["weather_forecast"] = {
                "temp": f"{weather_info.get('temperature', '--')}°C",
                "condition": weather_info.get("weather", "未知"),
            }
        
        # 获取收集的 POI
        collected_pois = final_state.get("collected_pois", [])
        
        # 行程信息 - 优先使用结构化数据
        travel_plan = final_state.get("travel_plan")
        logger.info("Building end event",
                   has_travel_plan=bool(travel_plan),
                   structured=travel_plan.get("structured") if travel_plan else None,
                   itinerary_len=len(travel_plan.get("itinerary", [])) if travel_plan else 0)
        
        if travel_plan:
            # 优先使用结构化的 itinerary
            if travel_plan.get("structured") and travel_plan.get("itinerary"):
                end_event["itinerary"] = travel_plan["itinerary"]
                logger.info("Using structured itinerary", count=len(travel_plan["itinerary"]))
            else:
                # 回退到文本解析
                plan_content = travel_plan.get("content", "")
                itinerary = _parse_itinerary_from_plan(plan_content, travel_pref.get("destination", ""))
                if itinerary:
                    end_event["itinerary"] = itinerary
                    logger.info("Using parsed itinerary", count=len(itinerary))
            
            # 优先使用结构化的酒店推荐
            if travel_plan.get("recommended_hotels"):
                end_event["pois"] = [
                    {
                        "name": hotel.get("name", ""),
                        "price": hotel.get("price", "暂无报价"),
                        "rating": hotel.get("rating", 4.5),
                        "tags": hotel.get("tags", ["推荐"]),
                        "image": None,
                        "desc": hotel.get("desc", ""),
                    }
                    for hotel in travel_plan["recommended_hotels"][:10]
                ]
            elif collected_pois:
                # 回退到收集的 POI
                end_event["pois"] = [
                    {
                        "name": poi.get("name", ""),
                        "price": poi.get("price") or "暂无报价",
                        "rating": poi.get("rating") or "4.5",
                        "tags": poi.get("type", "").split(";") if poi.get("type") else ["推荐"],
                        "image": None,
                        "desc": poi.get("address", ""),
                    }
                    for poi in collected_pois[:10]
                ]
        elif collected_pois:
            # 如果没有旅游计划，使用收集的 POI
            end_event["pois"] = [
                {
                    "name": poi.get("name", ""),
                    "price": poi.get("price") or "暂无报价",
                    "rating": poi.get("rating") or "4.5",
                    "tags": poi.get("type", "").split(";") if poi.get("type") else ["推荐"],
                    "image": None,
                    "desc": poi.get("address", ""),
                }
                for poi in collected_pois[:10]
            ]

    yield end_event


def _parse_itinerary_from_plan(plan_content: str, destination: str) -> list[dict[str, Any]]:
    """
    从计划文本中解析行程结构
    
    返回格式：
    [
        {
            "day": "Day 1",
            "title": "抵达与探索",
            "activities": [
                {"time": "09:00", "title": "景点名", "desc": "描述", "type": "attraction"}
            ]
        }
    ]
    """
    import re
    
    itinerary = []
    
    # 尝试按日分割
    day_patterns = [
        r"(?:第\s*)?(\d+)\s*[天日]",
        r"Day\s*(\d+)",
        r"DAY\s*(\d+)",
    ]
    
    # 简单解析：按换行分割，查找天数标记
    lines = plan_content.split("\n")
    current_day = None
    current_activities = []
    day_count = 0
    
    for line in lines:
        line = line.strip()
        if not line:
            continue
        
        # 检查是否是新的一天
        is_new_day = False
        for pattern in day_patterns:
            match = re.search(pattern, line, re.IGNORECASE)
            if match:
                # 保存前一天的内容
                if current_day is not None and current_activities:
                    itinerary.append({
                        "day": current_day["day"],
                        "title": current_day["title"],
                        "activities": current_activities,
                    })
                
                day_count += 1
                current_day = {
                    "day": f"Day {day_count}",
                    "title": line.replace("#", "").strip()[:50],
                }
                current_activities = []
                is_new_day = True
                break
        
        if is_new_day:
            continue
        
        # 解析活动（简化版本）
        if current_day is not None:
            # 尝试匹配时间
            time_match = re.search(r"(\d{1,2}[:\s：]\d{2}|\d{1,2}点|\上午|\下午|\晚上|\早上)", line)
            
            if time_match or line.startswith("-") or line.startswith("*") or line.startswith("•"):
                activity_text = line.lstrip("-*•").strip()
                if activity_text and len(activity_text) > 2:
                    # 确定活动类型
                    activity_type = "attraction"
                    if any(k in activity_text for k in ["吃", "餐", "美食", "饭", "小吃"]):
                        activity_type = "food"
                    elif any(k in activity_text for k in ["酒店", "住宿", "入住", "休息"]):
                        activity_type = "hotel"
                    elif any(k in activity_text for k in ["交通", "地铁", "打车", "公交", "出发"]):
                        activity_type = "transport"
                    
                    current_activities.append({
                        "time": time_match.group(1) if time_match else "",
                        "title": activity_text[:30],
                        "desc": activity_text,
                        "type": activity_type,
                    })
    
    # 添加最后一天
    if current_day is not None and current_activities:
        itinerary.append({
            "day": current_day["day"],
            "title": current_day["title"],
            "activities": current_activities,
        })
    
    # 如果无法解析，返回一个简单的结构
    if not itinerary and plan_content:
        itinerary = [{
            "day": "Day 1",
            "title": f"{destination}之旅",
            "activities": [{
                "time": "",
                "title": "查看详细行程",
                "desc": "请查看左侧对话中的完整行程规划",
                "type": "attraction",
            }]
        }]
    
    return itinerary


# ============================================================
# 便捷函数
# ============================================================


async def quick_search_pois(
    keywords: str,
    city: str,
    poi_type: str | None = None,
) -> list[dict[str, Any]]:
    """
    快速搜索 POI（不经过完整工作流）
    """
    from src.tools import search_poi

    result = await search_poi.ainvoke({
        "keywords": keywords,
        "city": city,
        "poi_type": poi_type,
    })
    return result.get("results", [])


async def quick_get_weather(city: str) -> dict[str, Any]:
    """
    快速获取天气（不经过完整工作流）
    """
    from src.tools import get_weather

    return await get_weather.ainvoke({"city": city})
