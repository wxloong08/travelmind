"""
解析器函数

行程时长解析、时间解析等通用工具
"""

import re


def parse_trip_duration(user_input: str) -> dict:
    """
    解析用户输入的行程时长
    
    支持格式：
    - "4天3晚" → 4天游玩 + 1天抵达 = 5天行程，4晚住宿
    - "3天" → 3天游玩 + 1天抵达 = 4天行程，3晚住宿
    - "周末游" → 2天游玩，1晚住宿（当天出发）
    
    Returns:
        {
            "user_days": 4,         # 用户说的天数
            "user_nights": 3,       # 用户说的晚数
            "actual_days": 5,       # 实际行程天数（含抵达日）
            "actual_nights": 4,     # 实际住宿晚数
            "needs_arrival_day": True
        }
    """
    user_input = user_input.strip()
    
    # 匹配 "X天Y晚" 格式
    match = re.search(r'(\d+)\s*天\s*(\d+)\s*晚', user_input)
    if match:
        days = int(match.group(1))
        nights = int(match.group(2))
        return {
            "user_days": days,
            "user_nights": nights,
            "actual_days": days + 1,      # +1 抵达日
            "actual_nights": nights + 1,  # +1 抵达日住宿
            "needs_arrival_day": True,
        }
    
    # 匹配 "X天" 格式
    match = re.search(r'(\d+)\s*天', user_input)
    if match:
        days = int(match.group(1))
        nights = days - 1
        return {
            "user_days": days,
            "user_nights": nights,
            "actual_days": days + 1,
            "actual_nights": days,  # days - 1 + 1 = days
            "needs_arrival_day": True,
        }
    
    # 匹配 "周末" 格式
    if '周末' in user_input:
        return {
            "user_days": 2,
            "user_nights": 1,
            "actual_days": 2,         # 周末不加抵达日（当天早上出发）
            "actual_nights": 1,
            "needs_arrival_day": False,
        }
    
    # 默认 3 天 2 晚
    return {
        "user_days": 3,
        "user_nights": 2,
        "actual_days": 4,
        "actual_nights": 3,
        "needs_arrival_day": True,
    }


def parse_time(time_str: str) -> int | None:
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


def parse_hour(time_str: str) -> int | None:
    """解析时间字符串为小时"""
    if not time_str:
        return None
    
    match = re.search(r"(\d{1,2})[:\s：点]", time_str)
    if match:
        return int(match.group(1))
    
    return None


def parse_price(price_str: str) -> int | None:
    """解析价格字符串"""
    if not price_str:
        return None
    
    # 提取数字
    match = re.search(r"(\d+)", price_str)
    if match:
        return int(match.group(1))
    
    return None
