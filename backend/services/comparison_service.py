from groq import Groq
from typing import List
from backend.models.models import Product, ComparisonResponse
from backend.utils.config import settings
from backend.utils.logger import get_logger

logger = get_logger(__name__)
client = Groq(api_key=settings.GROQ_API_KEY)


def compare_products(products: List[Product]) -> ComparisonResponse:
    logger.info(f"Comparing {len(products)} products")

    product_details = []
    for i, p in enumerate(products, 1):
        original_price = p.original_price if p.original_price else p.price
        product_details.append(
            f"Product {i}: {p.name}\n"
            f"  Website: {p.website}\n"
            f"  Price: ₹{p.price:.0f}\n"
            f"  Original Price: ₹{original_price:.0f}\n"
            f"  Discount: {p.discount:.0f}%\n"
            f"  Rating: {p.rating}★\n"
            f"  Brand: {p.brand or 'N/A'}"
        )

    prompt = f"""You are a shopping expert. Compare these {len(products)} products and provide a clear, actionable summary.

{chr(10).join(product_details)}

Write a 4-6 sentence comparison that:
1. Identifies which product offers the best price value
2. Identifies which has the highest rating
3. Identifies which offers the best discount
4. Gives a clear final recommendation

Be specific. Use actual prices, ratings, and percentages. Keep it practical for an Indian shopper."""

    try:
        response = client.chat.completions.create(
            model=settings.GROQ_MODEL,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.4,
            max_tokens=400,
        )
        summary = response.choices[0].message.content.strip()
    except Exception as e:
        logger.error(f"Groq comparison failed: {e}")
        cheapest = min(products, key=lambda p: p.price)
        best_rated = max(products, key=lambda p: p.rating)
        most_discount = max(products, key=lambda p: p.discount)
        summary = (
            f"{cheapest.name} offers the lowest price at ₹{cheapest.price:.0f} on {cheapest.website}. "
            f"{best_rated.name} has the best rating at {best_rated.rating}★. "
            f"{most_discount.name} offers the highest discount at {most_discount.discount:.0f}% off. "
            f"For best overall value, consider your priority: price, quality, or savings."
        )

    return ComparisonResponse(products=products, summary=summary)
