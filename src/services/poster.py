"""
海报生成服务 - 使用 Playwright 渲染 HTML 模板并截图

技术方案：
1. 使用 Jinja2 渲染 HTML 模板
2. 使用 Playwright 启动无头浏览器
3. 加载 HTML 并截图
4. 返回 PNG 图片字节
"""

import asyncio
import base64
from pathlib import Path
from typing import Optional

import httpx
import structlog
from jinja2 import Environment, FileSystemLoader

logger = structlog.get_logger()

# 模板目录
TEMPLATE_DIR = Path(__file__).parent.parent / "templates"


class PosterService:
    """海报生成服务"""
    
    def __init__(self):
        self._browser = None
        self._playwright = None
        self._lock = asyncio.Lock()
        
        # Jinja2 模板环境
        self.jinja_env = Environment(
            loader=FileSystemLoader(str(TEMPLATE_DIR)),
            autoescape=True
        )
    
    async def _get_browser(self):
        """获取或创建浏览器实例（单例模式）"""
        async with self._lock:
            if self._browser is None:
                try:
                    from playwright.async_api import async_playwright
                    self._playwright = await async_playwright().start()
                    self._browser = await self._playwright.chromium.launch(
                        headless=True,
                        args=['--no-sandbox', '--disable-setuid-sandbox']
                    )
                    logger.info("Playwright browser initialized")
                except Exception as e:
                    logger.error("Failed to initialize Playwright", error=str(e))
                    raise
            return self._browser
    
    async def _download_image_as_base64(self, url: str) -> Optional[str]:
        """下载图片并转换为 base64 data URL"""
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(url)
                if response.status_code == 200:
                    content_type = response.headers.get('content-type', 'image/jpeg')
                    b64 = base64.b64encode(response.content).decode('utf-8')
                    return f"data:{content_type};base64,{b64}"
        except Exception as e:
            logger.warning("Failed to download image", url=url, error=str(e))
        return None
    
    async def generate_poster(
        self,
        destination: str,
        days: int,
        nights: int,
        budget: str = "",
        highlights: list[str] = None,
        travel_style: str = "",
        background_url: str = "",
        image_source: str = ""
    ) -> bytes:
        """
        生成海报图片
        
        Args:
            destination: 目的地
            days: 天数
            nights: 晚数
            budget: 预算
            highlights: 行程亮点
            travel_style: 旅行风格
            background_url: 背景图片 URL
            image_source: 图片来源
        
        Returns:
            PNG 图片字节
        """
        logger.info(
            "Generating poster",
            destination=destination,
            days=days,
            nights=nights
        )
        
        # 下载背景图片并转换为 base64（避免跨域问题）
        bg_data_url = None
        if background_url:
            bg_data_url = await self._download_image_as_base64(background_url)
        
        # 渲染 HTML 模板
        template = self.jinja_env.get_template("poster.html")
        html_content = template.render(
            destination=destination,
            days=days,
            nights=nights,
            budget=budget,
            highlights=highlights or [],
            travel_style=travel_style,
            background_url=bg_data_url or "",
            image_source=image_source
        )
        
        # 使用 Playwright 截图（2x 分辨率提高清晰度）
        browser = await self._get_browser()
        page = await browser.new_page(
            viewport={'width': 1200, 'height': 1600},
            device_scale_factor=2
        )
        
        try:
            await page.set_content(html_content, wait_until='networkidle')
            
            # 等待图片加载
            await page.wait_for_timeout(500)
            
            # 截图
            screenshot = await page.screenshot(
                type='png',
                full_page=False
            )
            
            logger.info("Poster generated successfully", size=len(screenshot))
            return screenshot
            
        finally:
            await page.close()
    
    async def close(self):
        """关闭浏览器"""
        if self._browser:
            await self._browser.close()
            self._browser = None
        if self._playwright:
            await self._playwright.stop()
            self._playwright = None


# 全局服务实例
poster_service = PosterService()
