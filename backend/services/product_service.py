import random
import hashlib
from typing import List, Optional
from backend.models.models import Product, ProductSearchRequest
from backend.database.database import execute_query, execute_many
from backend.utils.logger import get_logger

logger = get_logger(__name__)

# Simulated retailer product data generator
# In production, replace this with real API calls (RapidAPI / retailer APIs)
RETAILER_CONFIGS = {
    "Amazon": {
        "url_template": "https://www.amazon.in/s?k={query}",
        "price_multiplier": 1.0,
        "discount_range": (5, 40),
        "rating_range": (3.5, 5.0),
    },
    "Flipkart": {
        "url_template": "https://www.flipkart.com/search?q={query}",
        "price_multiplier": 0.95,
        "discount_range": (10, 60),
        "rating_range": (3.2, 4.8),
    },
    "Myntra": {
        "url_template": "https://www.myntra.com/{query}",
        "price_multiplier": 1.05,
        "discount_range": (20, 70),
        "rating_range": (3.8, 4.9),
    },
    "Ajio": {
        "url_template": "https://www.ajio.com/s/{query}",
        "price_multiplier": 0.90,
        "discount_range": (30, 80),
        "rating_range": (3.5, 4.7),
    },
    "Meesho": {
        "url_template": "https://www.meesho.com/search?q={query}",
        "price_multiplier": 0.70,
        "discount_range": (15, 55),
        "rating_range": (3.0, 4.5),
    },
}

PRODUCT_TEMPLATES = {
    "pants": [
        {"name": "Slim Fit Formal Trousers", "brands": ["Peter England", "Van Heusen", "Allen Solly", "Arrow", "Louis Philippe"], "base_price": 1299},
        {"name": "Regular Fit Chinos", "brands": ["Levi's", "UCB", "Celio", "Marks & Spencer", "Pepe Jeans"], "base_price": 1599},
        {"name": "Stretch Formal Pants", "brands": ["Arrow", "Van Heusen", "Raymond", "Park Avenue", "ColorPlus"], "base_price": 1799},
        {"name": "Straight Fit Trousers", "brands": ["Peter England", "Monte Carlo", "Blackberrys", "Louis Philippe", "Allen Solly"], "base_price": 999},
        {"name": "Slim Tapered Chinos", "brands": ["Levi's", "Pepe Jeans", "Wrangler", "Lee", "UCB"], "base_price": 1399},
        {"name": "Business Formal Trousers", "brands": ["Raymond", "Blackberrys", "ColorPlus", "Park Avenue", "Louis Philippe"], "base_price": 2199},
    ],
    "shoes": [
        {"name": "Running Sneakers", "brands": ["Nike", "Adidas", "Puma", "Reebok", "ASICS"], "base_price": 3499},
        {"name": "Casual Lifestyle Shoes", "brands": ["Skechers", "Bata", "Red Tape", "Woodland", "Sparx"], "base_price": 1999},
        {"name": "Formal Oxford Shoes", "brands": ["Clarks", "Lee Cooper", "Red Tape", "Hush Puppies", "Bata"], "base_price": 2799},
        {"name": "Training Sports Shoes", "brands": ["Nike", "Adidas", "Under Armour", "New Balance", "Brooks"], "base_price": 4299},
        {"name": "Canvas Casual Sneakers", "brands": ["Converse", "Vans", "Puma", "Fila", "Keds"], "base_price": 1799},
        {"name": "Loafers Slip-On Shoes", "brands": ["Clarks", "Aldo", "Steve Madden", "Inc.5", "Metro"], "base_price": 2299},
    ],
    "laptop": [
        {"name": "Thin & Light Laptop", "brands": ["Lenovo", "HP", "Dell", "Asus", "Acer"], "base_price": 45999},
        {"name": "Gaming Laptop", "brands": ["Asus ROG", "MSI", "Lenovo Legion", "HP Omen", "Dell Alienware"], "base_price": 65999},
        {"name": "Business Ultrabook", "brands": ["Dell XPS", "HP Spectre", "Lenovo ThinkPad", "LG Gram", "Microsoft Surface"], "base_price": 75999},
        {"name": "Student Budget Laptop", "brands": ["Acer", "HP", "Lenovo", "Asus", "Dell Inspiron"], "base_price": 35999},
        {"name": "Creator's Laptop", "brands": ["Apple MacBook Air", "Apple MacBook Pro", "Dell XPS", "Asus ProArt", "HP Envy"], "base_price": 99999},
    ],
    "hoodie": [
        {"name": "Premium Cotton Hoodie", "brands": ["H&M", "Zara", "Roadster", "HRX", "Bewakoof"], "base_price": 799},
        {"name": "Fleece Pullover Hoodie", "brands": ["Columbia", "The North Face", "Puma", "Nike", "Adidas"], "base_price": 2499},
        {"name": "Oversized Drop-Shoulder Hoodie", "brands": ["Bewakoof", "The Souled Store", "Urbanic", "SNITCH", "Wrogn"], "base_price": 599},
        {"name": "Zip-Up Tech Fleece Hoodie", "brands": ["Nike", "Adidas", "Under Armour", "Puma", "Reebok"], "base_price": 3299},
    ],
    "default": [
        {"name": "Premium Product", "brands": ["Brand A", "Brand B", "Brand C", "Brand D", "Brand E"], "base_price": 1999},
        {"name": "Classic Style", "brands": ["Brand X", "Brand Y", "Brand Z", "TopBrand", "BestBrand"], "base_price": 2499},
        {"name": "Trending Choice", "brands": ["FashionBrand", "StyleCo", "TrendSet", "ModernWear", "UrbanStyle"], "base_price": 1499},
        {"name": "Value Pick", "brands": ["ValueBrand", "EcoChoice", "SmartPick", "BudgetPlus", "AffordStyle"], "base_price": 999},
        {"name": "Premium Edition", "brands": ["LuxBrand", "EliteCo", "ProStyle", "TopTier", "BestInClass"], "base_price": 3499},
    ],
}

PRODUCT_IMAGES = {
    "pants": [
        "https://images.unsplash.com/photo-1624378439575-d8705ad7ae80?w=400&q=80",
        "https://images.unsplash.com/photo-1594938298603-c8148c4b4345?w=400&q=80",
        "https://images.unsplash.com/photo-1506629082955-511b1aa562c8?w=400&q=80",
        "https://images.unsplash.com/photo-1473966968600-fa801b869a1a?w=400&q=80",
    ],
    "shoes": [
        "https://images.unsplash.com/photo-1542291026-7eec264c27ff?w=400&q=80",
        "https://images.unsplash.com/photo-1491553895911-0055eca6402d?w=400&q=80",
        "https://images.unsplash.com/photo-1600185365483-26d7a4cc7519?w=400&q=80",
        "https://images.unsplash.com/photo-1560769629-975ec94e6a86?w=400&q=80",
    ],
    "laptop": [
        "https://images.unsplash.com/photo-1496181133206-80ce9b88a853?w=400&q=80",
        "https://images.unsplash.com/photo-1517336714731-489689fd1ca8?w=400&q=80",
        "https://images.unsplash.com/photo-1593642632559-0c6d3fc62b89?w=400&q=80",
        "https://images.unsplash.com/photo-1525547719571-a2d4ac8945e2?w=400&q=80",
    ],
    "hoodie": [
        "https://images.unsplash.com/photo-1556821840-3a63f15732ce?w=400&q=80",
        "https://images.unsplash.com/photo-1509942774463-acf339cf87d5?w=400&q=80",
        "https://images.unsplash.com/photo-1620799140408-edc6dcb6d633?w=400&q=80",
    ],
    "default": [
        "https://images.unsplash.com/photo-1523275335684-37898b6baf30?w=400&q=80",
        "https://images.unsplash.com/photo-1567401893414-76b7b1e5a7a5?w=400&q=80",
        "https://images.unsplash.com/photo-1572635196237-14b3f281503f?w=400&q=80",
        "https://images.unsplash.com/photo-1485955900006-10f4d324d411?w=400&q=80",
    ],
}


def _get_category_key(query: str) -> str:
    query_lower = query.lower()
    if any(k in query_lower for k in ["pant", "trouser", "chino", "jeans", "denim"]):
        return "pants"
    if any(k in query_lower for k in ["shoe", "sneaker", "boot", "loafer", "footwear", "sandal"]):
        return "shoes"
    if any(k in query_lower for k in ["laptop", "notebook", "macbook", "chromebook"]):
        return "laptop"
    if any(k in query_lower for k in ["hoodie", "sweatshirt", "pullover"]):
        return "hoodie"
    return "default"


def _extract_price_limit(query: str) -> Optional[float]:
    import re
    match = re.search(r"under\s*[₹rs]?\s*(\d+)", query.lower())
    if match:
        return float(match.group(1))
    return None


def _generate_products(query: str, user_max_price: Optional[float] = None) -> List[Product]:
    cat_key = _get_category_key(query)
    templates = PRODUCT_TEMPLATES.get(cat_key, PRODUCT_TEMPLATES["default"])
    images = PRODUCT_IMAGES.get(cat_key, PRODUCT_IMAGES["default"])
    query_price_limit = _extract_price_limit(query)
    effective_max = user_max_price or query_price_limit

    seed = int(hashlib.md5(query.encode()).hexdigest(), 16) % 100000
    rng = random.Random(seed)

    products = []
    for retailer_name, retailer_cfg in RETAILER_CONFIGS.items():
        # Pick 2-3 templates per retailer
        num_items = rng.randint(2, 3)
        selected_templates = rng.sample(templates, min(num_items, len(templates)))
        for tmpl in selected_templates:
            brand = rng.choice(tmpl["brands"])
            base = tmpl["base_price"] * retailer_cfg["price_multiplier"]
            variation = rng.uniform(0.85, 1.20)
            price = round(base * variation, -1)  # round to nearest 10

            discount = round(rng.uniform(*retailer_cfg["discount_range"]), 0)
            original_price = round(price / (1 - discount / 100), -1)
            rating = round(rng.uniform(*retailer_cfg["rating_range"]), 1)
            rating_count = rng.randint(120, 18500)
            image_url = rng.choice(images)
            query_slug = query.lower().replace(" ", "-")

            if effective_max and price > effective_max:
                continue

            products.append(Product(
                name=f"{brand} {tmpl['name']}",
                website=retailer_name,
                price=price,
                original_price=original_price,
                discount=discount,
                rating=rating,
                rating_count=rating_count,
                image_url=image_url,
                product_url=retailer_cfg["url_template"].format(query=query_slug),
                brand=brand,
                category=cat_key,
            ))

    return products


def _apply_filters(products: List[Product], request: ProductSearchRequest) -> List[Product]:
    filtered = products

    if request.min_price is not None:
        filtered = [p for p in filtered if p.price >= request.min_price]
    if request.max_price is not None:
        filtered = [p for p in filtered if p.price <= request.max_price]
    if request.min_rating is not None:
        filtered = [p for p in filtered if p.rating >= request.min_rating]
    if request.min_discount is not None:
        filtered = [p for p in filtered if p.discount >= request.min_discount]
    if request.brand:
        filtered = [p for p in filtered if request.brand.lower() in (p.brand or "").lower()]
    if request.category:
        filtered = [p for p in filtered if request.category.lower() in (p.category or "").lower()]

    sort_map = {
        "price_asc": lambda p: p.price,
        "price_desc": lambda p: -p.price,
        "rating": lambda p: -p.rating,
        "discount": lambda p: -p.discount,
    }
    if request.sort_by in sort_map:
        filtered.sort(key=sort_map[request.sort_by])

    return filtered


def _cache_products(products: List[Product], query: str):
    try:
        execute_query(
            "DELETE FROM products WHERE search_query = %s",
            (query,), fetch=False
        )
        if products:
            rows = [
                (p.name, p.website, p.price, p.original_price, p.discount,
                 p.rating, p.rating_count, p.image_url, p.product_url,
                 p.brand, p.category, query)
                for p in products
            ]
            execute_many(
                """INSERT INTO products
                   (name, website, price, original_price, discount, rating, rating_count,
                    image_url, product_url, brand, category, search_query)
                   VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
                rows
            )
    except Exception as e:
        logger.warning(f"Product cache write failed: {e}")


def _save_search_history(user_id: int, query: str, filters: dict, result_count: int):
    import json
    try:
        execute_query(
            """INSERT INTO search_history (user_id, query, filters, result_count)
               VALUES (%s, %s, %s, %s)""",
            (user_id, query, json.dumps(filters), result_count),
            fetch=False
        )
    except Exception as e:
        logger.warning(f"Search history save failed: {e}")


def search_products(request: ProductSearchRequest) -> List[Product]:
    logger.info(f"Searching products: '{request.query}'")

    all_products = _generate_products(request.query, request.max_price)
    filtered = _apply_filters(all_products, request)

    _cache_products(filtered, request.query)

    filters_dict = {
        "min_price": request.min_price,
        "max_price": request.max_price,
        "min_rating": request.min_rating,
        "min_discount": request.min_discount,
        "sort_by": request.sort_by,
    }
    _save_search_history(request.user_id, request.query, filters_dict, len(filtered))

    logger.info(f"Found {len(filtered)} products for '{request.query}'")
    return filtered
