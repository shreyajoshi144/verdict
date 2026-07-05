from pydantic import BaseModel, Field, EmailStr
from typing import Optional, List, Any
from datetime import datetime

# ── Auth Models ──────────────────────────────────────────────────────────────

class UserRegister(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    email: EmailStr
    password: str = Field(..., min_length=6, max_length=128)

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class UserPublic(BaseModel):
    id: int
    name: str
    email: str

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserPublic

# ── Product Models ──────────────────────────────────────────────────────────

class Product(BaseModel):
    id: Optional[int] = None
    name: str
    website: str
    price: float
    original_price: Optional[float] = None
    discount: float = 0.0
    rating: float = 0.0
    rating_count: int = 0
    image_url: Optional[str] = None
    product_url: str
    brand: Optional[str] = None
    category: Optional[str] = None

class ProductSearchRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=500)
    min_price: Optional[float] = None
    max_price: Optional[float] = None
    min_rating: Optional[float] = None
    min_discount: Optional[float] = None
    sort_by: Optional[str] = "relevance"  # relevance | price_asc | price_desc | rating | discount
    category: Optional[str] = None
    brand: Optional[str] = None
    user_id: int = 1

class ProductSearchResponse(BaseModel):
    products: List[Product]
    total: int
    query: str

# ── Insight Models ───────────────────────────────────────────────────────────

class InsightRequest(BaseModel):
    products: List[Product]
    query: str

class InsightResponse(BaseModel):
    lowest_price: Optional[dict] = None
    highest_discount: Optional[dict] = None
    best_rated: Optional[dict] = None
    best_value: Optional[dict] = None
    summary: str

# ── Advisor Models ───────────────────────────────────────────────────────────

class AdvisorMessage(BaseModel):
    role: str  # "user" | "assistant"
    content: str

class AdvisorRequest(BaseModel):
    message: str = Field(..., min_length=1)
    history: List[AdvisorMessage] = []
    current_products: Optional[List[Product]] = []

class AdvisorResponse(BaseModel):
    reply: str
    history: List[AdvisorMessage]

# ── Comparison Models ────────────────────────────────────────────────────────

class ComparisonRequest(BaseModel):
    products: List[Product] = Field(..., min_length=2, max_length=3)

class ComparisonResponse(BaseModel):
    products: List[Product]
    summary: str

# ── Wishlist Models ──────────────────────────────────────────────────────────

class WishlistItem(BaseModel):
    id: Optional[int] = None
    user_id: int
    product_name: str
    website: str
    price: float
    discount: float = 0.0
    rating: float = 0.0
    image_url: Optional[str] = None
    product_url: str
    brand: Optional[str] = None
    saved_at: Optional[datetime] = None

class WishlistAddRequest(BaseModel):
    user_id: int = 1
    product: Product

class WishlistRemoveRequest(BaseModel):
    user_id: int = 1
    wishlist_id: int

# ── Search History Models ────────────────────────────────────────────────────

class SearchHistoryItem(BaseModel):
    id: Optional[int] = None
    user_id: int
    query: str
    filters: Optional[dict] = None
    result_count: int = 0
    created_at: Optional[datetime] = None

# ── Budget Models ────────────────────────────────────────────────────────────

class BudgetRequest(BaseModel):
    user_id: int = 1
    budget: float = Field(..., gt=0)
    category: Optional[str] = None
    description: Optional[str] = None

class BudgetAllocation(BaseModel):
    item: str
    allocated: float
    percentage: float
    suggestion: str

class BudgetResponse(BaseModel):
    budget: float
    category: Optional[str]
    allocations: List[BudgetAllocation]
    total_allocated: float
    advice: str
    saved_id: Optional[int] = None

# ── Generic Response ─────────────────────────────────────────────────────────

class APIResponse(BaseModel):
    success: bool
    message: str
    data: Optional[Any] = None
