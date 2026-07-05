from groq import Groq
from typing import List, Optional
from backend.models.models import Product, InsightResponse
from backend.utils.config import settings
from backend.utils.logger import get_logger

logger = get_logger(__name__)
client = Groq(api_key=settings.GROQ_API_KEY)


def _format_products_for_prompt(products: List[Product]) -> str:
    lines = []
    for i, p in enumerate(products[:15], 1):
        lines.append(
            f"{i}. {p.name} | {p.website} | ₹{p.price:.0f} | "
            f"{p.discount:.0f}% off | {p.rating}★ | Brand: {p.brand or 'N/A'}"
        )
    return "\n".join(lines)


def _find_lowest_price(products: List[Product]) -> Optional[dict]:
    if not products:
        return None
    p = min(products, key=lambda x: x.price)
    return {"name": p.name, "website": p.website, "price": p.price, "url": p.product_url}


def _find_highest_discount(products: List[Product]) -> Optional[dict]:
    if not products:
        return None
    p = max(products, key=lambda x: x.discount)
    return {"name": p.name, "website": p.website, "discount": p.discount, "price": p.price, "url": p.product_url}


def _find_best_rated(products: List[Product]) -> Optional[dict]:
    if not products:
        return None
    p = max(products, key=lambda x: x.rating)
    return {"name": p.name, "website": p.website, "rating": p.rating, "price": p.price, "url": p.product_url}


def generate_insights(products: List[Product], query: str) -> InsightResponse:
    if not products:
        return InsightResponse(summary="No products found to analyze.")

    lowest = _find_lowest_price(products)
    highest_discount = _find_highest_discount(products)
    best_rated = _find_best_rated(products)

    product_list = _format_products_for_prompt(products)

    prompt = f"""You are a smart shopping assistant. Analyze these products for the query "{query}" and provide a concise shopping recommendation.

Products:
{product_list}

Respond in this exact JSON structure:
{{
  "best_value_product": "Product name here",
  "best_value_reason": "2-sentence reason why it offers the best overall value (price + rating + discount)",
  "summary": "3-sentence overall shopping insight paragraph"
}}

Be specific. Mention actual prices, discounts, and ratings. Focus on helping the user make a smart decision."""

    try:
        response = client.chat.completions.create(
            model=settings.GROQ_MODEL,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,
            max_tokens=400,
        )

        import json
        content = response.choices[0].message.content.strip()
        # Extract JSON
        start = content.find("{")
        end = content.rfind("}") + 1
        if start >= 0 and end > start:
            data = json.loads(content[start:end])
            best_value = {
                "name": data.get("best_value_product", ""),
                "reason": data.get("best_value_reason", ""),
            }
            summary = data.get("summary", "")
        else:
            best_value = None
            summary = content

    except Exception as e:
        logger.error(f"Groq insight generation failed: {e}")
        # Fallback: rule-based insight
        best_value = None
        if lowest and best_rated:
            summary = (
                f"Found {len(products)} products for '{query}'. "
                f"Lowest price is ₹{lowest['price']:.0f} on {lowest['website']}. "
                f"Best rated option scores {best_rated['rating']}★ on {best_rated['website']}."
            )
        else:
            summary = f"Found {len(products)} products for your search."

    return InsightResponse(
        lowest_price=lowest,
        highest_discount=highest_discount,
        best_rated=best_rated,
        best_value=best_value,
        summary=summary,
    )
