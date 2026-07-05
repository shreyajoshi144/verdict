import json
from groq import Groq
from typing import List
from backend.models.models import BudgetRequest, BudgetResponse, BudgetAllocation
from backend.database.database import execute_query
from backend.utils.config import settings
from backend.utils.logger import get_logger

logger = get_logger(__name__)
client = Groq(api_key=settings.GROQ_API_KEY)


def create_budget_plan(request: BudgetRequest) -> BudgetResponse:
    logger.info(f"Creating budget plan: ₹{request.budget} for '{request.category or 'general'}'")

    category_context = request.category or request.description or "general shopping"

    prompt = f"""You are a smart budget planning assistant for Indian shoppers.

A user wants to spend ₹{request.budget:.0f} on: {category_context}

Create a practical budget allocation plan. Respond ONLY with valid JSON in this exact format:
{{
  "allocations": [
    {{"item": "Item name", "allocated": 1500.0, "percentage": 30.0, "suggestion": "One specific buying tip"}},
    {{"item": "Item name", "allocated": 2000.0, "percentage": 40.0, "suggestion": "One specific buying tip"}},
    {{"item": "Item name", "allocated": 1500.0, "percentage": 30.0, "suggestion": "One specific buying tip"}}
  ],
  "advice": "2-3 sentence overall shopping strategy for this budget in India. Mention specific platforms like Amazon, Flipkart, Myntra where relevant."
}}

Rules:
- All amounts in ₹ (Indian Rupees)
- Total allocated must equal ₹{request.budget:.0f} exactly
- 3-5 allocation items
- Each suggestion should be actionable and India-specific
- Percentages must add up to 100"""

    try:
        response = client.chat.completions.create(
            model=settings.GROQ_MODEL,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.4,
            max_tokens=700,
        )

        content = response.choices[0].message.content.strip()
        start = content.find("{")
        end = content.rfind("}") + 1
        data = json.loads(content[start:end])

        allocations = [
            BudgetAllocation(
                item=a["item"],
                allocated=float(a["allocated"]),
                percentage=float(a["percentage"]),
                suggestion=a["suggestion"],
            )
            for a in data["allocations"]
        ]
        advice = data["advice"]

    except Exception as e:
        logger.error(f"Groq budget plan failed: {e}")
        # Rule-based fallback
        if "outfit" in category_context.lower() or "cloth" in category_context.lower():
            items = [
                ("Tops / Shirts", 0.35), ("Bottoms / Pants", 0.35),
                ("Footwear", 0.20), ("Accessories", 0.10)
            ]
        elif "laptop" in category_context.lower() or "tech" in category_context.lower():
            items = [
                ("Laptop / Device", 0.75), ("Carry Bag / Case", 0.10),
                ("Accessories", 0.10), ("Software / Subscription", 0.05)
            ]
        else:
            items = [
                ("Primary Item", 0.50), ("Secondary Item", 0.30), ("Extras", 0.20)
            ]

        allocations = [
            BudgetAllocation(
                item=name,
                allocated=round(request.budget * pct, 0),
                percentage=pct * 100,
                suggestion=f"Look for sales on Flipkart and Amazon for best deals.",
            )
            for name, pct in items
        ]
        advice = (
            f"With ₹{request.budget:.0f}, focus on getting the primary item first from Amazon or Flipkart. "
            "Use cashback offers and bank discounts to stretch your budget further. "
            "Compare prices across Myntra and Ajio for fashion items."
        )

    # Save to DB
    saved_id = None
    try:
        saved_id = execute_query(
            """INSERT INTO budget_plans (user_id, budget, category, description, ai_plan)
               VALUES (%s, %s, %s, %s, %s)""",
            (request.user_id, request.budget, request.category,
             request.description, json.dumps([a.dict() for a in allocations])),
            fetch=False
        )
    except Exception as e:
        logger.warning(f"Budget plan DB save failed: {e}")

    total = sum(a.allocated for a in allocations)
    return BudgetResponse(
        budget=request.budget,
        category=request.category,
        allocations=allocations,
        total_allocated=total,
        advice=advice,
        saved_id=saved_id,
    )


def get_budget_history(user_id: int) -> list:
    rows = execute_query(
        """SELECT id, budget, category, description, created_at
           FROM budget_plans WHERE user_id = %s ORDER BY created_at DESC LIMIT 10""",
        (user_id,)
    )
    return rows
