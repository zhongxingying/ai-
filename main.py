from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from pydantic import BaseModel, Field
from typing import Literal
from fastapi import FastAPI, HTTPException
import uvicorn
import logging

# ---- 从 config 读取配置，不再硬编码 ----
from config import ONEAPI_API_BASE, ONEAPI_CHAT_API_KEY, ONEAPI_CHAT_MODEL

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI()

SYSTEM_PROMPT = """你是一个电信运营商的智能客服助手。
根据用户的问题，判断意图并给出回复。
意图只能从以下选项中选择：
- recommend_package（推荐套餐）
- ask_billing（账单查询）
- complaint（投诉建议）
- chitchat（寒暄、打招呼、问你是谁等闲聊）
- other（其他）"""


# 第一步：定义结构
class ChatResponse(BaseModel):
    intent: Literal["recommend_package", "ask_billing", "complaint", "chitchat", "other"] = Field(
        description="用户问题的业务类型"
    )
    answer: str = Field(description="面向用户展示的回复内容")
    confidence: float = Field(ge=0, le=1, description="置信度，0到1之间")
    need_human: bool = Field(description="是否需要转人工")


class ChatRequest(BaseModel):
    query: str
    user_id: str = "default_user"


# 第二步：绑定模型
model = ChatOpenAI(
    base_url=ONEAPI_API_BASE,
    api_key=ONEAPI_CHAT_API_KEY,
    model=ONEAPI_CHAT_MODEL,
    temperature=0.3,
    timeout=10,
    max_retries=2,
)
structured_model = model.with_structured_output(ChatResponse)

prompt = ChatPromptTemplate.from_messages([
    ("system", SYSTEM_PROMPT),
    ("human", "用户问题：{query}")
])
chain = prompt | structured_model


# 模拟外部业务函数
def query_billing_from_db(user_id: str) -> dict:
    return {"amount": 128.5, "detail": "套餐费 99 元 + 流量超额 29.5 元"}

def search_packages(need: str) -> list:
    return [
        {"name": "畅享 59 套餐", "data": "30GB", "price": 59},
        {"name": "畅享 99 套餐", "data": "80GB", "price": 99},
    ]

def create_ticket(user_id: str, content: str) -> str:
    return "TK20240914001"

def route_to_human(user_id: str, reason: str) -> str:
    return f"已为您转接人工客服（原因：{reason}），当前排队第 3 位。"


# 第三步 + 第四步：业务处理 + 异常兜底
@app.post("/v1/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    try:
        result = chain.invoke({"query": request.query})
    except Exception as e:
        logger.error(f"模型调用失败: {e}")
        return ChatResponse(
            intent="other",
            answer="抱歉，系统暂时无法处理您的问题，正在为您转接人工客服。",
            confidence=0.0,
            need_human=True,
        )

    try:
        if result.confidence < 0.6:
            result.need_human = True
            result.intent = "other"
            result.answer = route_to_human(request.user_id, "置信度过低")

        elif result.need_human:
            result.answer = route_to_human(request.user_id, "模型判断需人工")

        elif result.intent == "ask_billing":
            try:
                bill = query_billing_from_db(request.user_id)
                result.answer = f"您本月账单为 {bill['amount']} 元，明细：{bill['detail']}"
            except Exception as e:
                logger.error(f"查账单失败: {e}")
                result.answer = "账单系统暂时不可用，请稍后重试或转人工。"
                result.need_human = True

        elif result.intent == "recommend_package":
            try:
                packages = search_packages(request.query)
                lines = [
                    f"{p['name']}：{p['data']}流量，{p['price']}元/月"
                    for p in packages
                ]
                result.answer = "为您推荐以下套餐：\n" + "\n".join(lines)
            except Exception as e:
                logger.error(f"查套餐失败: {e}")
                result.answer = "套餐系统暂时不可用，请稍后重试或转人工。"
                result.need_human = True

        elif result.intent == "complaint":
            try:
                ticket_id = create_ticket(request.user_id, request.query)
                result.answer = f"已为您创建投诉工单，编号 {ticket_id}，我们会尽快处理。"
            except Exception as e:
                logger.error(f"建工单失败: {e}")
                result.answer = "工单系统暂时不可用，正在为您转接人工。"
                result.need_human = True

        elif result.intent == "chitchat":
            result.need_human = False

        else:
            result.need_human = True
            result.answer = route_to_human(request.user_id, "无法识别意图")

    except Exception as e:
        logger.error(f"业务处理异常: {e}")
        return ChatResponse(
            intent="other",
            answer="系统处理异常，正在为您转接人工客服。",
            confidence=0.0,
            need_human=True,
        )

    logger.info(
        f"user={request.user_id} intent={result.intent} "
        f"confidence={result.confidence} need_human={result.need_human}"
    )
    return result


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)