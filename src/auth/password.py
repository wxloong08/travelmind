"""
密码工具函数

使用 passlib 进行密码哈希和验证
bcrypt 是行业标准的密码哈希算法，具有自适应性和内置盐值
"""

import re
from passlib.context import CryptContext

# 创建密码上下文，使用 bcrypt
# bcrypt 是 OWASP 推荐的密码哈希算法
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    """
    对密码进行哈希处理
    
    Args:
        password: 明文密码
        
    Returns:
        哈希后的密码字符串
    """
    return pwd_context.hash(password)


def verify_password(password: str, hashed: str) -> bool:
    """
    验证密码是否正确
    
    Args:
        password: 明文密码
        hashed: 存储的密码哈希
        
    Returns:
        验证结果
    """
    try:
        return pwd_context.verify(password, hashed)
    except Exception:
        return False


class PasswordValidationError(Exception):
    """密码验证错误"""
    pass


def validate_password(password: str) -> None:
    """
    验证密码是否符合规则
    
    规则：
    - 最少8位
    - 必须包含字母
    - 必须包含数字
    - 必须包含特殊字符
    
    Args:
        password: 明文密码
        
    Raises:
        PasswordValidationError: 如果密码不符合规则
    """
    if len(password) < 8:
        raise PasswordValidationError("密码长度至少8位")
    
    # bcrypt 有 72 字节限制
    if len(password.encode('utf-8')) > 72:
        raise PasswordValidationError("密码长度不能超过72字节")
    
    if not re.search(r'[a-zA-Z]', password):
        raise PasswordValidationError("密码必须包含字母")
    
    if not re.search(r'\d', password):
        raise PasswordValidationError("密码必须包含数字")
    
    # 特殊字符必须
    if not re.search(r'[!@#$%^&*(),.?":{}|<>_\-+=\[\]\\;\'`~]', password):
        raise PasswordValidationError("密码必须包含特殊字符（如 !@#$%^&*）")
