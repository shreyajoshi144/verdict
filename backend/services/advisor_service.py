from groq import Groq
from typing import List, Optional
from backend.models.models import AdvisorMessage, AdvisorRequest, AdvisorResponse, Product
from backend.utils.config import settings
from backend.utils.logger import get_logger

logger = get_logger(__name__)
client = Groq(api_key=settings.GROQ_API_KEY)

SYSTEM_PROMPT = """You are the Verdict Shopping Advisor — an expert, friendly AI assistant specializing in Indian e-commerce and fashion.

Your role:
- Give personalized shopping advice in Indian context (prices in ₹)
- Suggest products from popular Indian retailers: Amazon, Flipkart, Myntra, Ajio, Meesho
- Help users with outfit combinations, budget planning, and product comparisons
- Consider Indian fashion trends, seasons, and occasions
- Be concise and actionable (3-5 sentences per response unless asked for more)
- Format prices in ₹ (Indian Rupees)
- When relevant, mention specific product recommendations or categories

You are part of Verdict — a shopping intelligence platform that helps people decide, not just discover. Keep responses conversational and helpful."""


def _build_context_message(products: Optional[List[Product]]) -> str:
    if not products:
        return ""
    lines = [f"\nCurrent products on screen ({len(products)} items):"]
    for p in products[:5]:
        lines.append(f"- {p.name} ({p.website}) ₹{p.price:.0f} | {p.rating}★ | {p.discount:.0f}% off")
    return "\n".join(lines)


def chat(request: AdvisorRequest) -> AdvisorResponse:
    logger.info(f"Advisor chat: '{request.message[:60]}...'")

    messages = [{"role": "system", "content": SYSTEM_PROMPT}]

    context = _build_context_message(request.current_products)
    if context:
        messages.append({
            "role": "system",
            "content": f"Context:{context}"
        })

    for msg in request.history[-10:]:
        messages.append({"role": msg.role, "content": msg.content})

    messages.append({"role": "user", "content": request.message})

    try:
        response = client.chat.completions.create(
            model=settings.GROQ_MODEL,
            messages=messages,
            temperature=0.7,
            max_tokens=600,
        )
        reply = response.choices[0].message.content.strip()
    except Exception as e:
        logger.error(f"Groq advisor call failed: {e}")
        reply = (
            "I'm having trouble connecting right now. "
            "Please try again in a moment. In the meantime, you can browse products using the search bar above."
        )

    updated_history = list(request.history) + [
        AdvisorMessage(role="user", content=request.message),
        AdvisorMessage(role="assistant", content=reply),
    ]

    return AdvisorResponse(reply=reply, history=updated_history)
