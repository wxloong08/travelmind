"""
AI 助手服务

为前端提供结构化的 AI 功能支持
"""

import json
from typing import Any

import structlog

from src.llm import get_llm, Message

logger = structlog.get_logger()


class AssistantService:
    """AI 助手服务类"""

    def __init__(self):
        self.llm = get_llm()

    async def _call_llm_json(self, prompt: str) -> dict[str, Any] | None:
        """调用 LLM 并解析 JSON 响应"""
        full_prompt = f"""{prompt}

**重要**：请直接返回纯 JSON 格式，不要包含 markdown 代码块标记（如 ```json）。"""

        try:
            messages = [
                Message(role="system", content="你是一个旅行助手，请根据用户要求返回结构化的 JSON 数据。"),
                Message(role="user", content=full_prompt),
            ]
            response = await self.llm.chat(messages)
            text = response.content.strip()

            # 清理可能的 markdown 标记
            if text.startswith("```json"):
                text = text[7:]
            if text.startswith("```"):
                text = text[3:]
            if text.endswith("```"):
                text = text[:-3]
            text = text.strip()

            return json.loads(text)
        except json.JSONDecodeError as e:
            logger.error("JSON parse failed", error=str(e), response=text[:200] if text else "empty")
            return None
        except Exception as e:
            logger.error("LLM call failed", error=str(e))
            return None

    async def _call_llm_text(self, prompt: str) -> str:
        """调用 LLM 获取文本响应"""
        try:
            messages = [
                Message(role="system", content="你是一个旅行助手，请用生动的语言回答用户问题。"),
                Message(role="user", content=prompt),
            ]
            response = await self.llm.chat(messages)
            return response.content.strip()
        except Exception as e:
            logger.error("LLM call failed", error=str(e))
            return ""

    # ================================================================
    # 预算估算
    # ================================================================

    async def estimate_budget(
        self,
        destination: str,
        context: str | None = None,
        days: int = 3,
    ) -> dict[str, Any]:
        """估算旅行预算"""
        prompt = f"""你是一位专业的旅行预算顾问。请为以下旅行估算预算：

目的地：{destination}
天数：{days} 天
行程概要：{context or "一般观光旅行"}

请返回 JSON 格式：
{{
    "total_range": "总预算范围，如 3000-5000 元",
    "categories": [
        {{"name": "住宿", "amount": "800-1500", "desc": "经济型酒店或民宿"}},
        {{"name": "餐饮", "amount": "600-1000", "desc": "当地特色美食"}},
        {{"name": "门票", "amount": "300-500", "desc": "主要景点门票"}},
        {{"name": "交通", "amount": "200-400", "desc": "市内交通"}},
        {{"name": "其他", "amount": "200-300", "desc": "购物、零食等"}}
    ],
    "saving_tip": "一条实用的省钱建议"
}}

请根据{destination}的实际物价水平给出合理估算。"""

        result = await self._call_llm_json(prompt)
        if result:
            return result
        return {
            "total_range": "暂无数据",
            "categories": [],
            "saving_tip": "请稍后重试",
        }

    # ================================================================
    # 行李清单
    # ================================================================

    async def generate_packing_list(
        self,
        destination: str,
        context: str | None = None,
        weather: str | None = None,
        days: int = 3,
    ) -> dict[str, Any]:
        """生成智能行李清单"""
        prompt = f"""你是一位旅行达人。请为以下旅行生成行李清单：

目的地：{destination}
天数：{days} 天
天气：{weather or "未知"}
行程概要：{context or "一般观光旅行"}

请返回 JSON 格式：
{{
    "special_tips": "针对{destination}的特别提醒（如防晒、防雨等）",
    "categories": [
        {{
            "name": "证件文件",
            "items": [
                {{"name": "身份证", "reason": "必备证件"}},
                {{"name": "手机充电器", "reason": "保持通讯"}}
            ]
        }},
        {{
            "name": "衣物鞋帽",
            "items": [...]
        }},
        {{
            "name": "洗漱用品",
            "items": [...]
        }},
        {{
            "name": "电子产品",
            "items": [...]
        }},
        {{
            "name": "其他",
            "items": [...]
        }}
    ]
}}

请根据目的地特点和天气给出实用建议。"""

        result = await self._call_llm_json(prompt)
        if result:
            return result
        return {"special_tips": "", "categories": []}

    # ================================================================
    # 氛围歌单
    # ================================================================

    async def generate_playlist(
        self,
        destination: str,
        context: str | None = None,
    ) -> dict[str, Any]:
        """生成旅行氛围歌单"""
        prompt = f"""你是一位音乐品味出众的旅行博主。请为{destination}之旅推荐一个氛围歌单：

行程概要：{context or "一般观光旅行"}

请返回 JSON 格式：
{{
    "vibe_title": "歌单的诗意标题，如：漫步西湖的午后",
    "vibe_desc": "一句话描述这个歌单的氛围",
    "songs": [
        {{"title": "歌曲名", "artist": "歌手", "reason": "为什么适合"}},
        ... (共5首歌)
    ]
}}

请推荐真实存在的歌曲，中英文皆可，风格与目的地氛围契合。"""

        result = await self._call_llm_json(prompt)
        if result:
            return result
        return {"vibe_title": "", "vibe_desc": "", "songs": []}

    # ================================================================
    # 紧急助手
    # ================================================================

    async def generate_emergency_info(
        self,
        destination: str,
    ) -> dict[str, Any]:
        """生成紧急求助信息"""
        prompt = f"""你是一位旅行安全专家。请为前往{destination}的游客提供紧急求助信息：

请返回 JSON 格式：
{{
    "local_numbers": {{
        "警方": "110",
        "急救": "120",
        "火警": "119",
        "旅游投诉": "12301"
    }},
    "sos_card": {{
        "text_local": "用当地语言说'请帮帮我'",
        "text_en": "Please help me",
        "pronunciation": "发音指南"
    }},
    "embassy_tip": "针对{destination}的安全提示和求助建议（中文，100字以内）"
}}

如果是国内城市，local_numbers 使用中国的紧急电话；如果是国外城市，使用当地的紧急电话。"""

        result = await self._call_llm_json(prompt)
        if result:
            return result
        return {
            "local_numbers": {"警方": "110", "急救": "120"},
            "sos_card": None,
            "embassy_tip": "请拨打当地紧急电话求助",
        }

    # ================================================================
    # 文化锦囊
    # ================================================================

    async def generate_culture_guide(
        self,
        destination: str,
    ) -> dict[str, Any]:
        """生成文化锦囊"""
        prompt = f"""你是一位{destination}本地文化专家。请为游客提供文化指南：

请返回 JSON 格式：
{{
    "taboos": [
        "不要做某事...",
        "避免某种行为..."
    ],
    "etiquette": "当地的礼仪建议，如小费、问候方式等",
    "phrases": [
        {{
            "local": "当地语言/方言的常用语",
            "pronunciation": "拼音或音标",
            "meaning": "含义"
        }},
        ... (3-5个实用短语)
    ]
}}

请提供实用、有趣的文化知识，帮助游客更好地融入当地。"""

        result = await self._call_llm_json(prompt)
        if result:
            return result
        return {"taboos": [], "etiquette": "", "phrases": []}

    # ================================================================
    # 伴手礼指南
    # ================================================================

    async def generate_souvenir_guide(
        self,
        destination: str,
    ) -> dict[str, Any]:
        """生成伴手礼推荐"""
        prompt = f"""你是一位{destination}购物达人。请推荐当地值得购买的伴手礼：

请返回 JSON 格式：
{{
    "must_buy": [
        {{"name": "特产名称", "desc": "为什么值得买，特点是什么"}},
        ... (3-5个推荐)
    ],
    "avoid": [
        "不推荐购买的东西1（如景区高价纪念品）",
        "不推荐购买的东西2"
    ]
}}

请推荐真正有当地特色、性价比高的伴手礼。"""

        result = await self._call_llm_json(prompt)
        if result:
            return result
        return {"must_buy": [], "avoid": []}

    # ================================================================
    # 摄影挑战
    # ================================================================

    async def generate_photo_challenges(
        self,
        destination: str,
    ) -> dict[str, Any]:
        """生成摄影挑战任务"""
        prompt = f"""你是一位旅行摄影师。请为{destination}之旅设计5个有趣的摄影挑战任务：

请返回 JSON 格式：
{{
    "challenges": [
        {{"title": "挑战标题（如：寻找红灯笼）", "desc": "任务描述和拍摄建议"}},
        ... (共5个挑战)
    ]
}}

挑战应该有趣、可完成，能帮助游客发现{destination}的独特之处。"""

        result = await self._call_llm_json(prompt)
        if result:
            return result
        return {"challenges": []}

    # ================================================================
    # 问路卡
    # ================================================================

    async def generate_direction_card(
        self,
        destination: str,
        place_name: str,
    ) -> dict[str, Any]:
        """生成问路卡"""
        prompt = f"""请帮助游客在{destination}找到"{place_name}"。

请返回 JSON 格式：
{{
    "local_text": "用当地语言说'请带我去{place_name}'",
    "pronunciation": "发音指南（拼音或音标）",
    "address": "{place_name}的大致位置描述"
}}

如果是中国城市，local_text 用普通话；如果是其他国家，用当地官方语言。"""

        result = await self._call_llm_json(prompt)
        if result:
            return result
        return {
            "local_text": f"请带我去{place_name}",
            "pronunciation": "",
            "address": "",
        }

    # ================================================================
    # 景点故事
    # ================================================================

    async def generate_story(
        self,
        destination: str,
        place_name: str,
    ) -> str:
        """生成景点故事/传说 - 丰富的文化底蕴内容"""
        prompt = f"""你是一位知识渊博的{destination}本地文化专家和导游。请讲述关于"{place_name}"的一个引人入胜的故事或典故。

## 内容要求
1. **历史背景**：简述该地点的历史渊源和文化意义
2. **核心故事**：讲述一个与此地相关的传说、典故或历史事件
3. **独特视角**：从一个独特的角度切入，让读者感觉仿佛亲历其境
4. **文化内涵**：自然融入当地文化特色和民俗元素

## 格式要求
- 语言：中文
- 长度：200-300字
- 风格：生动有趣、引人入胜、有文化深度
- 使用**粗体**标注关键概念或地名
- 可以使用一些生动的比喻和描写

## 示例风格参考
"**'龙门'与'红尘'的界线** 您站在雄伟的天安门广场，感受的是国之威严。但请往南看，那是正阳门与箭楼，俗称'前门'。古代北京有'内九外七'十六道城门，而正阳门是其中最高的'国门'……"

请直接输出故事内容，不需要任何额外标题或解释。"""

        return await self._call_llm_text(prompt)

    # ================================================================
    # 发圈文案
    # ================================================================

    async def generate_social_captions(
        self,
        destination: str,
        place_name: str,
    ) -> dict[str, Any]:
        """生成社交媒体发圈文案 - 3种不同风格"""
        prompt = f"""为"{place_name}"（{destination}）生成3种不同风格的朋友圈文案。

请返回 JSON 格式：
{{
    "styles": [
        {{
            "name": "文艺风",
            "text": "一段适合发朋友圈的文艺文案，要有诗意和情怀，可包含 #话题标签#"
        }},
        {{
            "name": "幽默风",
            "text": "一段轻松幽默的文案，适合分享旅行趣事"
        }},
        {{
            "name": "简约风",
            "text": "简短精炼的打卡文案，突出地点和感受"
        }}
    ]
}}

要求：
1. 每条文案 50-100 字
2. 风格要鲜明，符合各自特点
3. 可以包含 2-3 个相关话题标签（如 #北京旅行 #历史文化）
4. 文案要有吸引力，让人想点赞和评论
"""

        result = await self._call_llm_json(prompt)
        if result:
            return result
        return {"styles": []}

    # ================================================================
    # 每日攻略
    # ================================================================

    async def generate_day_tips(
        self,
        destination: str,
        day_title: str,
        activities: list[str],
    ) -> dict[str, Any]:
        """生成每日攻略"""
        activities_str = "、".join(activities) if activities else "一般游览"

        prompt = f"""你是一位{destination}本地向导。请为以下行程提供攻略：

主题：{day_title}
计划游览：{activities_str}

请返回 JSON 格式：
{{
    "photo_spots": [
        {{"name": "拍照点名称", "desc": "最佳拍摄时间和角度建议"}},
        ... (2-3个)
    ],
    "warnings": [
        "需要注意的事项1",
        "需要注意的事项2"
    ],
    "food": [
        "推荐美食1",
        "推荐美食2"
    ],
    "transport": "交通建议（如何前往、停车等）"
}}"""

        result = await self._call_llm_json(prompt)
        if result:
            return result
        return {
            "photo_spots": [],
            "warnings": [],
            "food": [],
            "transport": "",
        }

    # ================================================================
    # 旅行日记
    # ================================================================

    async def generate_diary(
        self,
        destination: str,
        day: int,
        day_title: str,
        activities: list[str],
    ) -> str:
        """生成旅行日记 - 情感丰富的第一人称叙述"""
        activities_str = "、".join(activities) if activities else "一般游览"

        prompt = f"""你是一位文笔优美的旅行作家。请以第一人称写一篇深刻动人的旅行日记：

## 背景信息
- 目的地：{destination}
- 第几天：Day {day}
- 主题：{day_title}
- 今日行程：{activities_str}

## 写作要求

### 格式要求
请使用 Markdown 格式，包含以下元素：
- 标题（包含日期和天气描述）
- 2-3 个小节标题（使用 ####）
- 段落清晰，有情感起伏

### 内容要求
1. **开篇场景**：描写早晨醒来的感受，或抵达某个地点的第一印象
2. **感官细节**：描述看到的色彩、听到的声音、闻到的气味、触摸到的质感、品尝到的味道
3. **情感变化**：从期待到震撼，从好奇到感悟，要有情绪的起伏
4. **历史文化**：自然融入一些历史典故或文化背景，让读者也能学到东西
5. **个人感悟**：结尾要有深刻的个人感悟，升华主题
6. **生动的比喻**：使用新颖的比喻和拟人手法，避免陈词滥调

### 语言风格
- 情感细腻，文字优美，有文学性
- 像真实的旅行日记，有私人的小秘密和独特感受
- 中文，500-800字
- 避免"我看到了xxx，我感到很xxx"这样简单的句式
- 多用动态描写，让读者身临其境

### 示例结构
```
## {destination}游记 · 第{day}日：{day_title}

**20XX年X月X日 晴转多云**

[开篇场景描写，1-2段]

#### [第一个小标题]
[详细的见闻和感受，2-3段]

#### [第二个小标题]
[另一个精彩时刻，2-3段]

[结尾感悟，1段]
```

请直接输出日记内容，不需要任何额外解释。"""

        return await self._call_llm_text(prompt)

    # ================================================================
    # Vlog 脚本生成
    # ================================================================

    async def generate_vlog_script(
        self,
        destination: str,
        day: int,
        day_title: str,
        activities: list[str],
    ) -> dict[str, Any]:
        """生成 Vlog 拍摄脚本"""
        activities_str = "、".join(activities) if activities else "一般游览"

        prompt = f"""你是一位专业的短视频编导。请为以下旅行日程生成一个完整的 Vlog 拍摄脚本：

## 背景信息
- 目的地：{destination}
- 第几天：Day {day}
- 主题：{day_title}
- 今日行程：{activities_str}

请返回 JSON 格式：
{{
    "title": "吸引眼球的 Vlog 标题，如【{destination}Vlog】Day{day} xxx",
    "shots": [
        {{
            "action": "具体拍摄内容描述",
            "angle": "拍摄角度，如广角、特写、跟拍",
            "duration": "建议时长，如 3s、5s",
            "audio": "配音文案或同期声描述"
        }}
    ],
    "bgm": "推荐背景音乐风格或具体歌曲"
}}

要求：
1. 生成 5-8 个镜头
2. 包含开场、主体内容和结尾
3. 镜头要有变化，避免单一
4. 配音文案要生动有趣"""

        result = await self._call_llm_json(prompt)
        if result:
            return result
        return {"title": f"{destination} Day{day}", "shots": [], "bgm": "轻快旅行音乐"}

    # ================================================================
    # 摄影指导
    # ================================================================

    async def generate_photo_guide(
        self,
        destination: str,
        place_name: str,
    ) -> dict[str, Any]:
        """生成景点摄影指导"""
        prompt = f"""你是一位专业的旅行摄影师。请为以下景点提供摄影建议：

景点：{place_name}
城市：{destination}

请返回 JSON 格式：
{{
    "best_time": "最佳拍摄时间段，如'日落时分 17:00-19:00'",
    "best_angle": "最佳拍摄角度和位置",
    "composition_tip": "构图技巧建议",
    "gear_tip": "器材建议（手机也可以）",
    "avoid": "拍摄时应避免的问题"
}}

请基于{place_name}的实际情况给出专业建议。"""

        result = await self._call_llm_json(prompt)
        if result:
            return result
        return {
            "best_time": "早晨或傍晚光线柔和时",
            "best_angle": "寻找独特视角",
            "composition_tip": "注意前景和背景的搭配",
            "gear_tip": "手机开启 HDR 模式",
            "avoid": "避免正午强光直射"
        }

    # ================================================================
    # 海报数据生成
    # ================================================================

    async def generate_poster_data(
        self,
        destination: str,
        days: int,
        activities: list[str] | None = None,
    ) -> dict[str, Any]:
        """生成分享海报所需数据"""
        activities_str = "、".join(activities[:10]) if activities else "探索当地"
        
        # 正确计算晚数
        nights = max(days - 1, 0)
        days_display = f"{days}天{nights}晚 深度游"

        prompt = f"""请为以下旅行生成分享海报所需的摘要信息：

目的地：{destination}
天数：{days} 天 {nights} 晚
行程亮点：{activities_str}

请返回 JSON 格式：
{{
    "destination": "{destination}",
    "days": "{days_display}",
    "highlights": ["亮点1", "亮点2", "亮点3"],
    "budget": "预估总预算，如 ¥3000"
}}

要求：
1. highlights 提取 3 个最吸引人的亮点（从行程中选取具体景点名称）
2. budget 根据行程和天数合理估算
3. days 字段必须保持为 "{days_display}"，不要修改"""

        result = await self._call_llm_json(prompt)
        if result:
            # 确保 days 字段使用正确计算的值，防止 LLM 修改
            result["days"] = days_display
            return result
        return {
            "destination": destination,
            "days": days_display,
            "highlights": ["探索未知", "品味美食", "留下回忆"],
            "budget": "¥3000起"
        }


# 创建全局实例
assistant_service = AssistantService()

