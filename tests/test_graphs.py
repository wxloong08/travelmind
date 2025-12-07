"""
LangGraph 状态和工作流测试
"""

import pytest
from datetime import datetime


class TestAgentState:
    """Agent 状态测试"""

    def test_create_initial_state(self):
        """测试创建初始状态"""
        from src.graphs.state import create_initial_state

        state = create_initial_state()

        assert state["messages"] == []
        assert state["session_id"] is not None
        assert state["task_type"] is None
        assert state["planning_phase"] == "init"
        assert state["should_end"] is False

    def test_create_initial_state_with_session_id(self):
        """测试带会话 ID 创建状态"""
        from src.graphs.state import create_initial_state

        session_id = "test_session_123"
        state = create_initial_state(session_id)

        assert state["session_id"] == session_id

    def test_initial_state_timestamps(self):
        """测试初始状态时间戳"""
        from src.graphs.state import create_initial_state

        state = create_initial_state()

        assert state["created_at"] is not None
        assert state["updated_at"] is not None
        # 时间戳应该是 ISO 格式
        datetime.fromisoformat(state["created_at"])
        datetime.fromisoformat(state["updated_at"])


class TestTaskType:
    """任务类型枚举测试"""

    def test_task_type_values(self):
        """测试任务类型值"""
        from src.graphs.state import TaskType

        assert TaskType.TRAVEL_PLANNING.value == "travel_planning"
        assert TaskType.HOTEL_SEARCH.value == "hotel_search"
        assert TaskType.ATTRACTION_INFO.value == "attraction_info"
        assert TaskType.RENTAL_SEARCH.value == "rental_search"
        assert TaskType.GENERAL_CHAT.value == "general_chat"


class TestPlanningPhase:
    """规划阶段枚举测试"""

    def test_planning_phase_values(self):
        """测试规划阶段值"""
        from src.graphs.state import PlanningPhase

        assert PlanningPhase.INIT.value == "init"
        assert PlanningPhase.UNDERSTAND.value == "understand"
        assert PlanningPhase.RESEARCH.value == "research"
        assert PlanningPhase.PLANNING.value == "planning"
        assert PlanningPhase.COMPLETE.value == "complete"


class TestTravelPreference:
    """旅游偏好数据类测试"""

    def test_default_values(self):
        """测试默认值"""
        from src.graphs.state import TravelPreference

        pref = TravelPreference()

        assert pref.destination is None
        assert pref.start_date is None
        assert pref.interests == []
        assert pref.party_size == 1

    def test_with_values(self):
        """测试带值创建"""
        from src.graphs.state import TravelPreference

        pref = TravelPreference(
            destination="杭州",
            start_date="2024-05-01",
            end_date="2024-05-03",
            budget="3000",
            interests=["自然风光", "美食"],
            party_size=2,
        )

        assert pref.destination == "杭州"
        assert pref.budget == "3000"
        assert len(pref.interests) == 2


class TestRentalPreference:
    """租房偏好数据类测试"""

    def test_default_values(self):
        """测试默认值"""
        from src.graphs.state import RentalPreference

        pref = RentalPreference()

        assert pref.city is None
        assert pref.near_subway is False
        assert pref.amenities == []

    def test_with_values(self):
        """测试带值创建"""
        from src.graphs.state import RentalPreference

        pref = RentalPreference(
            city="北京",
            district="朝阳区",
            budget_min=3000,
            budget_max=5000,
            room_type="整租",
            duration_months=12,
            near_subway=True,
        )

        assert pref.city == "北京"
        assert pref.budget_max == 5000
        assert pref.near_subway is True


class TestGraphCreation:
    """图创建测试"""

    def test_create_travel_graph(self):
        """测试创建旅游规划图"""
        from src.graphs.travel_graph import create_travel_graph

        graph = create_travel_graph()
        assert graph is not None

    def test_get_compiled_graph(self):
        """测试获取编译后的图"""
        from src.graphs.travel_graph import get_compiled_graph

        compiled = get_compiled_graph()
        assert compiled is not None
