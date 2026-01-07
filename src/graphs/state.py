"""
LangGraph 状态定义

定义 Agent 工作流中的状态结构
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Annotated, Any

from langgraph.graph.message import add_messages
from typing_extensions import TypedDict


class TaskType(str, Enum):
    """任务类型枚举"""

    TRAVEL_PLANNING = "travel_planning"  # 旅游规划
    HOTEL_SEARCH = "hotel_search"  # 酒店搜索
    ATTRACTION_INFO = "attraction_info"  # 景点信息
    RENTAL_SEARCH = "rental_search"  # 租房搜索
    GENERAL_CHAT = "general_chat"  # 通用对话


class PlanningPhase(str, Enum):
    """规划阶段枚举"""

    INIT = "init"  # 初始化
    UNDERSTAND = "understand"  # 理解需求
    RESEARCH = "research"  # 信息收集
    PLANNING = "planning"  # 行程规划
    PLAN_GENERATED = "plan_generated"  # 行程已生成
    REFINE = "refine"  # 优化调整
    COMPLETE = "complete"  # 完成


@dataclass
class TravelPreference:
    """用户旅游偏好"""

    destination: str | None = None  # 目的地
    start_date: str | None = None  # 出发日期
    end_date: str | None = None  # 返回日期
    budget: str | None = None  # 预算范围
    travel_style: str | None = None  # 旅行风格（休闲/紧凑/探险）
    interests: list[str] = field(default_factory=list)  # 兴趣点
    accommodation_type: str | None = None  # 住宿类型偏好
    transportation: str | None = None  # 交通方式偏好
    party_size: int = 1  # 出行人数
    special_requirements: list[str] = field(default_factory=list)  # 特殊需求


@dataclass
class RentalPreference:
    """用户租房偏好"""

    city: str | None = None  # 城市
    district: str | None = None  # 区域
    budget_min: int | None = None  # 最低预算
    budget_max: int | None = None  # 最高预算
    room_type: str | None = None  # 房型（整租/合租）
    duration_months: int | None = None  # 租期（月）
    near_subway: bool = False  # 是否靠近地铁
    amenities: list[str] = field(default_factory=list)  # 设施要求


@dataclass
class POIInfo:
    """POI 信息"""

    name: str
    type: str
    address: str
    rating: float | None = None
    cost: float | None = None
    location: tuple[float, float] | None = None
    visit_duration: int | None = None  # 建议游览时长（分钟）
    tips: str | None = None  # 游玩建议


@dataclass
class DayPlan:
    """单日行程计划"""

    date: str
    theme: str  # 当日主题
    activities: list[dict[str, Any]] = field(default_factory=list)
    meals: list[dict[str, Any]] = field(default_factory=list)
    accommodation: dict[str, Any] | None = None
    notes: str | None = None


@dataclass
class TravelPlan:
    """完整旅游计划"""

    destination: str
    start_date: str
    end_date: str
    total_days: int
    summary: str
    daily_plans: list[DayPlan] = field(default_factory=list)
    estimated_budget: dict[str, Any] | None = None
    packing_list: list[str] = field(default_factory=list)
    tips: list[str] = field(default_factory=list)


class AgentState(TypedDict):
    """
    Agent 状态定义

    使用 TypedDict 以兼容 LangGraph 的状态管理
    """

    # 消息历史（使用 add_messages reducer 自动累积）
    messages: Annotated[list[Any], add_messages]

    # 会话元数据
    session_id: str
    created_at: str
    updated_at: str

    # 任务识别
    task_type: str | None
    planning_phase: str

    # 用户偏好
    travel_preference: dict[str, Any] | None
    rental_preference: dict[str, Any] | None

    # 收集的信息
    collected_pois: list[dict[str, Any]]
    weather_info: dict[str, Any] | None
    search_results: list[dict[str, Any]]

    # POI-Based 规划支持
    poi_pool: dict[str, dict[str, Any]] | None  # POI ID -> EnhancedPOI.to_dict()
    distance_matrix: dict[str, Any] | None  # 预计算的距离矩阵
    arrival_hub: dict[str, Any] | None  # 抵达点（机场/火车站）

    # 生成的计划
    travel_plan: dict[str, Any] | None

    # 工具调用追踪
    pending_tool_calls: list[dict[str, Any]]
    tool_results: list[dict[str, Any]]

    # 错误处理
    errors: list[str]

    # 控制流
    next_action: str | None
    should_end: bool

    # 重新生成支持
    regenerate: bool
    previous_itinerary: list[dict[str, Any]] | None

    # 评估闭环支持
    evaluation: dict[str, Any] | None  # LLM 评估结果
    evaluation_count: int  # 评估迭代次数
    reflection_count: int  # 反思迭代次数（防止无限循环）
    route_enriched: bool  # 路线是否已增强

    # 规则检查支持（混合架构）
    rule_check_result: dict[str, Any] | None  # 规则检查结果
    reflect_reason: str | None  # 反思来源: "rule_violation" | "llm_score"


def create_initial_state(session_id: str | None = None) -> AgentState:
    """创建初始状态"""
    import uuid

    now = datetime.now().isoformat()

    return AgentState(
        messages=[],
        session_id=session_id or str(uuid.uuid4()),
        created_at=now,
        updated_at=now,
        task_type=None,
        planning_phase=PlanningPhase.INIT.value,
        travel_preference=None,
        rental_preference=None,
        collected_pois=[],
        weather_info=None,
        search_results=[],
        poi_pool=None,
        distance_matrix=None,
        arrival_hub=None,
        travel_plan=None,
        pending_tool_calls=[],
        tool_results=[],
        errors=[],
        next_action=None,
        should_end=False,
        regenerate=False,
        previous_itinerary=None,
        evaluation=None,
        evaluation_count=0,
        reflection_count=0,
        route_enriched=False,
        rule_check_result=None,
        reflect_reason=None,
    )
