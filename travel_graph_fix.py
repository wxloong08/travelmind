# ============================================================
# 修复 src/graphs/travel_graph.py 中的 stream_travel_agent 函数
# ============================================================
#
# 找到 stream_travel_agent 函数，将其替换为以下代码：
# 注意：只需要修改函数的前半部分，添加异常处理

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
    import traceback  # 添加这行导入
    
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

    # ... 后续 end_event 构建代码保持不变 ...
    # 从这里开始到函数结束，保持原有代码不变

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
        if travel_plan:
            # 优先使用结构化的 itinerary
            if travel_plan.get("structured") and travel_plan.get("itinerary"):
                end_event["itinerary"] = travel_plan["itinerary"]
            else:
                # 回退到文本解析
                plan_content = travel_plan.get("content", "")
                itinerary = _parse_itinerary_from_plan(plan_content, travel_pref.get("destination", ""))
                if itinerary:
                    end_event["itinerary"] = itinerary
            
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

    logger.info("Stream end event", 
                has_itinerary=bool(end_event.get("itinerary")),
                has_pois=bool(end_event.get("pois")))
    
    yield end_event