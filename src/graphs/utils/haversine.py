"""
Haversine 距离计算

根据两点经纬度计算球面距离（km）
"""

import math


def haversine(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    """
    计算两点之间的 Haversine 球面距离
    
    Args:
        lat1, lng1: 第一个点的纬度和经度
        lat2, lng2: 第二个点的纬度和经度
    
    Returns:
        距离（公里）
    """
    # 地球半径（公里）
    R = 6371.0
    
    # 转换为弧度
    lat1_rad = math.radians(lat1)
    lat2_rad = math.radians(lat2)
    delta_lat = math.radians(lat2 - lat1)
    delta_lng = math.radians(lng2 - lng1)
    
    # Haversine 公式
    a = (
        math.sin(delta_lat / 2) ** 2
        + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(delta_lng / 2) ** 2
    )
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    
    return R * c


def is_within_distance(
    lat1: float, lng1: float,
    lat2: float, lng2: float,
    max_km: float,
) -> bool:
    """
    快速判断两点是否在指定距离内
    
    使用近似计算，速度更快
    """
    # 快速排除：经纬度差值过大
    # 1度纬度 ≈ 111km，1度经度 ≈ 111km * cos(lat)
    lat_diff = abs(lat2 - lat1)
    lng_diff = abs(lng2 - lng1)
    
    # 粗略估算（假设 1 度 ≈ 100km）
    rough_distance = math.sqrt(lat_diff ** 2 + lng_diff ** 2) * 100
    
    if rough_distance > max_km * 1.5:  # 留 50% 余量
        return False
    
    # 精确计算
    return haversine(lat1, lng1, lat2, lng2) <= max_km
