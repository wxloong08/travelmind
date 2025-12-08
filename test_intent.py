import asyncio
from src.llm import get_llm, Message

async def test():
    llm = get_llm()
    prompt = '''分析用户消息，判断任务类型并提取关键信息。

用户消息：帮我规划北京3天亲子游

请返回以下 JSON 格式：
{
    "task_type": "travel_planning",
    "confidence": 0.95,
    "extracted_info": {
        "destination": "北京",
        "dates": "3天",
        "travel_style": "亲子游"
    }
}

只返回 JSON，不要其他内容。'''
    
    response = await llm.chat([
        Message(role='system', content='你是一个意图分类助手，只返回JSON格式。'),
        Message(role='user', content=prompt),
    ])
    print('Response:', response.content)

asyncio.run(test())
