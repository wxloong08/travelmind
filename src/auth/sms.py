"""
腾讯云短信服务

发送验证码短信
"""

import random
import string
from datetime import datetime, timedelta

import structlog

from src.config import settings

logger = structlog.get_logger()

# 验证码缓存（简单内存实现，生产环境应使用 Redis）
_verification_codes: dict[str, tuple[str, datetime]] = {}


class SMSService:
    """
    腾讯云短信服务
    
    使用方式:
    ```python
    # 发送验证码
    code = await sms_service.send_verification_code("13800138000")
    
    # 验证
    is_valid = sms_service.verify_code("13800138000", "123456")
    ```
    """
    
    # 验证码有效期（分钟）
    CODE_EXPIRE_MINUTES = 5
    
    # 验证码长度
    CODE_LENGTH = 6
    
    # 发送频率限制（秒）
    SEND_INTERVAL_SECONDS = 60
    
    def __init__(self):
        self._client = None
        self._last_send_time: dict[str, datetime] = {}
    
    def _get_client(self):
        """获取腾讯云短信客户端"""
        if self._client is not None:
            return self._client
        
        # 检查配置
        if not all([
            settings.tencent_sms_secret_id,
            settings.tencent_sms_secret_key,
            settings.tencent_sms_app_id,
        ]):
            logger.warning("Tencent SMS not configured")
            return None
        
        try:
            from tencentcloud.common import credential
            from tencentcloud.sms.v20210111 import sms_client
            
            cred = credential.Credential(
                settings.tencent_sms_secret_id,
                settings.tencent_sms_secret_key,
            )
            self._client = sms_client.SmsClient(cred, "ap-guangzhou")
            return self._client
            
        except ImportError:
            logger.error("tencentcloud-sdk-python-sms not installed")
            return None
        except Exception as e:
            logger.error("Failed to create SMS client", error=str(e))
            return None
    
    def _generate_code(self) -> str:
        """生成验证码"""
        return ''.join(random.choices(string.digits, k=self.CODE_LENGTH))
    
    def _can_send(self, phone: str) -> tuple[bool, int]:
        """
        检查是否可以发送
        
        Returns:
            (can_send, wait_seconds): 是否可以发送，需要等待的秒数
        """
        last_send = self._last_send_time.get(phone)
        if not last_send:
            return True, 0
        
        elapsed = (datetime.now() - last_send).total_seconds()
        if elapsed < self.SEND_INTERVAL_SECONDS:
            wait = int(self.SEND_INTERVAL_SECONDS - elapsed)
            return False, wait
        
        return True, 0
    
    async def send_verification_code(self, phone: str) -> tuple[bool, str]:
        """
        发送验证码
        
        Args:
            phone: 手机号
        
        Returns:
            (success, message): 是否成功，消息/验证码
        """
        # 检查发送频率
        can_send, wait_seconds = self._can_send(phone)
        if not can_send:
            return False, f"请等待 {wait_seconds} 秒后再试"
        
        # 生成验证码
        code = self._generate_code()
        
        # 获取客户端
        client = self._get_client()
        
        # 开发/演示模式：使用固定验证码 123456
        if not client:
            code = "123456"  # 固定验证码，方便演示
            logger.info(
                "SMS service not configured, using demo mode",
                phone=phone[:3] + "****" + phone[-4:],
                code=code,
            )
        
        if client:
            # 发送短信
            try:
                from tencentcloud.sms.v20210111 import models
                
                req = models.SendSmsRequest()
                req.SmsSdkAppId = settings.tencent_sms_app_id
                req.SignName = settings.tencent_sms_sign_name
                req.TemplateId = settings.tencent_sms_template_id
                req.TemplateParamSet = [code, str(self.CODE_EXPIRE_MINUTES)]
                req.PhoneNumberSet = [f"+86{phone}"]
                
                resp = client.SendSms(req)
                
                # 检查发送结果
                if resp.SendStatusSet and resp.SendStatusSet[0].Code == "Ok":
                    logger.info("SMS sent successfully", phone=phone[:3] + "****" + phone[-4:])
                else:
                    error_msg = resp.SendStatusSet[0].Message if resp.SendStatusSet else "Unknown error"
                    logger.error("SMS send failed", error=error_msg)
                    return False, f"短信发送失败: {error_msg}", False
                    
            except Exception as e:
                logger.error("SMS send error", error=str(e))
                return False, f"短信发送失败: {str(e)}", False
        
        # 存储验证码
        expire_at = datetime.now() + timedelta(minutes=self.CODE_EXPIRE_MINUTES)
        _verification_codes[phone] = (code, expire_at)
        self._last_send_time[phone] = datetime.now()
        
        # 返回结果，包含是否为演示模式
        is_demo = not client
        if is_demo:
            return True, f"演示模式，验证码为 {code}", True
        return True, f"验证码已发送到 {phone[:3]}****{phone[-4:]}", False
    
    def verify_code(self, phone: str, code: str) -> tuple[bool, str]:
        """
        验证验证码
        
        Args:
            phone: 手机号
            code: 验证码
        
        Returns:
            (success, message): 是否成功，错误消息
        """
        cached = _verification_codes.get(phone)
        
        if not cached:
            return False, "请先获取验证码"
        
        stored_code, expire_at = cached
        
        # 检查过期
        if datetime.now() > expire_at:
            del _verification_codes[phone]
            return False, "验证码已过期，请重新获取"
        
        # 验证
        if code != stored_code:
            return False, "验证码错误"
        
        # 验证成功，删除验证码
        del _verification_codes[phone]
        
        return True, "验证成功"
    
    def get_remaining_seconds(self, phone: str) -> int:
        """获取下次可发送的剩余秒数"""
        _, wait = self._can_send(phone)
        return wait


# 全局实例
sms_service = SMSService()
