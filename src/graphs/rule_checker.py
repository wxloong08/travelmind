"""
规则检查器

硬约束检查模块，能用规则验证的不交给 LLM。
在 LLM 评分前执行，不通过直接打回反思节点。
"""

import asyncio
import re
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

import structlog

logger = structlog.get_logger()


# ============================================================
# 数据结构
# ============================================================


@dataclass
class RuleViolation:
    """规则违规"""
    
    rule_name: str           # "distance_check", "time_conflict", etc.
    severity: str            # "critical" | "high" | "medium"
    message: str             # "Day 1 故宫→长城距离 65km，超过阈值 50km"
    day: int | None = None
    activity_index: int | None = None
    suggestion: str = ""     # "建议将长城安排到独立一天"


@dataclass
class RuleCheckResult:
    """规则检查结果"""
    
    passed: bool
    violations: list[RuleViolation] = field(default_factory=list)
    checked_at: str = field(default_factory=lambda: datetime.now().isoformat())
    
    def to_dict(self) -> dict[str, Any]:
        """转换为字典"""
        return {
            "passed": self.passed,
            "violations": [
                {
                    "rule_name": v.rule_name,
                    "severity": v.severity,
                    "message": v.message,
                    "day": v.day,
                    "activity_index": v.activity_index,
                    "suggestion": v.suggestion,
                }
                for v in self.violations
            ],
            "checked_at": self.checked_at,
        }


# ============================================================
# 常量配置
# ============================================================

# 距离阈值（米）
MAX_SAME_DAY_DISTANCE = 50000  # 50km - 同天景点最大距离

# 高德 API 限流配置
AMAP_QPS_LIMIT = 3
AMAP_REQUEST_INTERVAL = 1.0 / AMAP_QPS_LIMIT + 0.05  # ~0.38s

# 已知景点开放时间（可扩展为数据库/API）
OPENING_HOURS: dict[str, tuple[int, int]] = {
    "故宫": (8, 17),
    "故宫博物院": (8, 17),
    "天安门广场": (5, 22),
    "颐和园": (6, 19),
    "长城": (7, 18),
    "八达岭长城": (7, 18),
    "慕田峪长城": (7, 18),
    "天坛": (6, 21),
    "圆明园": (7, 19),
    "北海公园": (6, 21),
    "环球影城": (10, 21),
    "北京环球影城": (10, 21),
    "迪士尼": (8, 22),
    "上海迪士尼": (8, 22),
    "外滩": (0, 24),  # 全天开放
    "东方明珠": (8, 22),
    "西湖": (0, 24),  # 全天开放
    "灵隐寺": (7, 18),
}


# ============================================================
# 规则检查器
# ============================================================


class RuleChecker:
    """
    规则检查器
    
    执行硬约束检查，能用规则验证的不交给 LLM。
    """
    
    def __init__(self):
        self._amap_client = None
    
    async def _get_amap_client(self):
        """延迟加载高德客户端"""
        if self._amap_client is None:
            try:
                from src.tools.amap import get_amap_client
                self._amap_client = get_amap_client()
            except Exception as e:
                logger.warning("Amap client not available", error=str(e))
        return self._amap_client
    
    async def check_all(
        self,
        itinerary: list[dict[str, Any]],
        travel_pref: dict[str, Any],
    ) -> RuleCheckResult:
        """
        执行所有规则检查
        
        Args:
            itinerary: 行程列表
            travel_pref: 用户旅行偏好
        
        Returns:
            RuleCheckResult: 检查结果
        """
        violations: list[RuleViolation] = []
        
        # 1. 时间冲突检查
        time_violations = self.check_time_conflicts(itinerary)
        violations.extend(time_violations)
        
        # 2. 必去景点覆盖检查
        must_visit = travel_pref.get("must_visit_places", [])
        if must_visit:
            coverage_violations = self.check_must_visit_coverage(itinerary, must_visit)
            violations.extend(coverage_violations)
        
        # 3. 预算匹配检查
        budget_level = travel_pref.get("budget_level", "moderate")
        budget_violations = self.check_budget_match(itinerary, budget_level)
        violations.extend(budget_violations)
        
        # 4. 开放时间检查
        opening_violations = self.check_opening_hours(itinerary)
        violations.extend(opening_violations)
        
        # 5. 距离检查（需要 API 调用，放最后）
        city = travel_pref.get("destination", "")
        if city:
            distance_violations = await self.check_distance(itinerary, city)
            violations.extend(distance_violations)
        
        # 判断是否通过：无 critical/high 严重性违规
        has_critical = any(v.severity in ("critical", "high") for v in violations)
        passed = not has_critical
        
        logger.info(
            "Rule check completed",
            total_violations=len(violations),
            critical_count=sum(1 for v in violations if v.severity in ("critical", "high")),
            passed=passed,
        )
        
        return RuleCheckResult(passed=passed, violations=violations)
    
    def check_time_conflicts(self, itinerary: list[dict[str, Any]]) -> list[RuleViolation]:
        """
        检查时间冲突
        
        - 同一时间重复安排
        - 活动结束时间晚于下一个活动开始时间
        """
        violations = []
        
        for day_idx, day in enumerate(itinerary):
            activities = day.get("activities", [])
            prev_end_time = None
            
            for act_idx, activity in enumerate(activities):
                time_str = activity.get("time", "")
                if not time_str:
                    continue
                
                # 解析时间
                current_time = self._parse_time(time_str)
                if current_time is None:
                    continue
                
                # 检查与前一个活动的时间冲突
                if prev_end_time is not None and current_time < prev_end_time:
                    violations.append(RuleViolation(
                        rule_name="time_conflict",
                        severity="high",
                        message=f"Day {day_idx}: {activity.get('title', '活动')} 开始时间 {time_str} 早于上一个活动结束时间",
                        day=day_idx,
                        activity_index=act_idx,
                        suggestion="调整活动顺序或修改时间安排",
                    ))
                
                # 估算当前活动结束时间（默认 2 小时）
                prev_end_time = current_time + 120  # 分钟
            
        return violations
    
    def check_must_visit_coverage(
        self,
        itinerary: list[dict[str, Any]],
        must_visit: list[str],
    ) -> list[RuleViolation]:
        """
        检查必去景点覆盖度
        """
        violations = []
        
        # 收集行程中所有活动标题
        all_titles = []
        for day in itinerary:
            for activity in day.get("activities", []):
                title = activity.get("title", "")
                if title:
                    all_titles.append(title.lower())
        
        all_titles_text = " ".join(all_titles)
        
        # 检查每个必去景点
        for place in must_visit:
            place_lower = place.lower()
            # 模糊匹配
            if place_lower not in all_titles_text:
                # 尝试简称匹配
                short_names = [place_lower[:2], place_lower[:3]]
                found = any(sn in all_titles_text for sn in short_names if len(sn) >= 2)
                
                if not found:
                    violations.append(RuleViolation(
                        rule_name="must_visit_missing",
                        severity="high",
                        message=f"必去景点「{place}」未出现在行程中",
                        suggestion=f"请将「{place}」添加到行程中",
                    ))
        
        return violations
    
    def check_budget_match(
        self,
        itinerary: list[dict[str, Any]],
        budget_level: str,
    ) -> list[RuleViolation]:
        """
        检查预算匹配度
        """
        violations = []
        
        # 预算等级对应的价格范围
        budget_ranges = {
            "economy": (0, 250),
            "moderate": (150, 500),
            "comfortable": (350, 1000),
            "luxury": (700, 5000),
        }
        
        min_price, max_price = budget_ranges.get(budget_level, (150, 500))
        
        for day_idx, day in enumerate(itinerary):
            accommodation = day.get("accommodation")
            if not accommodation:
                continue
            
            # 尝试解析价格
            price_str = accommodation.get("price", "")
            price_num = self._parse_price(price_str)
            
            if price_num and price_num > max_price * 1.2:  # 允许 20% 浮动
                violations.append(RuleViolation(
                    rule_name="budget_exceeded",
                    severity="high",
                    message=f"Day {day_idx} 住宿「{accommodation.get('name', '')}」价格 {price_str} 超出预算上限 ¥{max_price}",
                    day=day_idx,
                    suggestion=f"请选择价格在 ¥{min_price}-{max_price} 范围内的住宿",
                ))
        
        return violations
    
    def check_opening_hours(self, itinerary: list[dict[str, Any]]) -> list[RuleViolation]:
        """
        检查景点开放时间
        """
        violations = []
        
        for day_idx, day in enumerate(itinerary):
            for act_idx, activity in enumerate(activities := day.get("activities", [])):
                title = activity.get("title", "")
                time_str = activity.get("time", "")
                
                if not title or not time_str:
                    continue
                
                # 查找匹配的开放时间
                opening_hours = None
                for place_name, hours in OPENING_HOURS.items():
                    if place_name in title:
                        opening_hours = hours
                        break
                
                if opening_hours is None:
                    continue
                
                # 解析活动时间
                activity_hour = self._parse_hour(time_str)
                if activity_hour is None:
                    continue
                
                open_hour, close_hour = opening_hours
                
                if activity_hour < open_hour:
                    violations.append(RuleViolation(
                        rule_name="before_opening",
                        severity="medium",
                        message=f"Day {day_idx} {title} 安排在 {time_str}，但开放时间为 {open_hour}:00",
                        day=day_idx,
                        activity_index=act_idx,
                        suggestion=f"建议调整到 {open_hour}:00 后",
                    ))
                elif activity_hour >= close_hour:
                    violations.append(RuleViolation(
                        rule_name="after_closing",
                        severity="medium",
                        message=f"Day {day_idx} {title} 安排在 {time_str}，但 {close_hour}:00 关门",
                        day=day_idx,
                        activity_index=act_idx,
                        suggestion=f"建议调整到 {close_hour}:00 前",
                    ))
        
        return violations
    
    async def check_distance(
        self,
        itinerary: list[dict[str, Any]],
        city: str,
    ) -> list[RuleViolation]:
        """
        检查同天景点距离（调用高德 API）
        
        考虑 QPS=3 限制，使用限流
        """
        violations = []
        amap = await self._get_amap_client()
        
        if not amap:
            logger.warning("Amap client not available, skipping distance check")
            return violations
        
        for day_idx, day in enumerate(itinerary):
            activities = day.get("activities", [])
            if len(activities) < 2:
                continue
            
            # 收集有坐标的活动
            located_activities = []
            for act_idx, activity in enumerate(activities):
                location = activity.get("location")
                if location and location.get("lat") and location.get("lng"):
                    located_activities.append({
                        "index": act_idx,
                        "title": activity.get("title", ""),
                        "location": (location["lng"], location["lat"]),
                    })
            
            if len(located_activities) < 2:
                continue
            
            # 检查相邻活动间的距离
            for i in range(len(located_activities) - 1):
                act1 = located_activities[i]
                act2 = located_activities[i + 1]
                
                try:
                    # QPS 限流
                    await asyncio.sleep(AMAP_REQUEST_INTERVAL)
                    
                    # 调用路线规划获取真实距离
                    route_info = await amap.route_planning(
                        origin=act1["location"],
                        destination=act2["location"],
                        mode="driving",  # 驾车距离更准确
                    )
                    
                    if route_info and route_info.distance > MAX_SAME_DAY_DISTANCE:
                        distance_km = round(route_info.distance / 1000, 1)
                        violations.append(RuleViolation(
                            rule_name="distance_too_far",
                            severity="critical",
                            message=f"Day {day_idx} {act1['title']}→{act2['title']} 距离 {distance_km}km，超过阈值 {MAX_SAME_DAY_DISTANCE // 1000}km",
                            day=day_idx,
                            activity_index=act2["index"],
                            suggestion=f"建议将「{act2['title']}」调整到独立一天",
                        ))
                        
                except Exception as e:
                    logger.warning(
                        "Distance check failed",
                        day=day_idx,
                        from_=act1["title"],
                        to=act2["title"],
                        error=str(e),
                    )
        
        return violations
    
    # ============================================================
    # 辅助方法
    # ============================================================
    
    def _parse_time(self, time_str: str) -> int | None:
        """解析时间字符串为分钟数（从 00:00 起）"""
        if not time_str:
            return None
        
        # 尝试 HH:MM 格式
        match = re.search(r"(\d{1,2})[:\s：](\d{2})", time_str)
        if match:
            hour = int(match.group(1))
            minute = int(match.group(2))
            return hour * 60 + minute
        
        # 尝试 XX点 格式
        match = re.search(r"(\d{1,2})点", time_str)
        if match:
            return int(match.group(1)) * 60
        
        return None
    
    def _parse_hour(self, time_str: str) -> int | None:
        """解析时间字符串为小时"""
        if not time_str:
            return None
        
        match = re.search(r"(\d{1,2})[:\s：点]", time_str)
        if match:
            return int(match.group(1))
        
        return None
    
    def _parse_price(self, price_str: str) -> int | None:
        """解析价格字符串"""
        if not price_str:
            return None
        
        # 提取数字
        match = re.search(r"(\d+)", price_str)
        if match:
            return int(match.group(1))
        
        return None


# ============================================================
# 便捷函数
# ============================================================


def get_rule_checker() -> RuleChecker:
    """获取规则检查器实例"""
    return RuleChecker()
