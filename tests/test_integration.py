import sys
sys.path.insert(0, str(__import__('pathlib').Path(__file__).resolve().parent.parent))

from tests import fake_db as tests_fake_db
tests_fake_db.patch_all()

from fastapi.testclient import TestClient
from backend.main import app

client = TestClient(app)
passed, failed = [], []


def check(name, cond, detail=""):
    if cond:
        passed.append(name)
        print(f"  OK   {name}")
    else:
        failed.append(name)
        print(f"  FAIL {name} {detail}")


print("\n=== Static frontend ===")
r = client.get("/")
check("GET / serves SPA shell", r.status_code == 200 and "Verdict" in r.text, r.status_code)

print("\n=== SPA client-side routing fallback ===")
r = client.get("/wishlist")
check("GET /wishlist (no such backend route) falls back to SPA shell", r.status_code == 200 and "Verdict" in r.text, r.status_code)
r = client.get("/docs")
check("GET /docs still serves FastAPI's own docs, not swallowed by the SPA fallback", r.status_code == 200 and "swagger" in r.text.lower(), r.status_code)

print("\n=== Health ===")
r = client.get("/health")
check("GET /health", r.status_code == 200 and r.json()["status"] == "healthy")

print("\n=== Auth: unauthenticated access is rejected ===")
r = client.post("/api/v1/products/search", json={"query": "shoes"})
check("search without token -> 401", r.status_code == 401, r.status_code)

r = client.get("/api/v1/user/wishlist/1")
check("wishlist without token -> 401", r.status_code == 401, r.status_code)

print("\n=== Auth: register ===")
r = client.post("/api/v1/auth/register", json={"name": "Test User", "email": "test@verdict.ai", "password": "hunter22"})
check("register -> 201", r.status_code == 201, (r.status_code, r.text))
token = r.json().get("access_token")
user_id = r.json().get("user", {}).get("id")
check("register returns access_token", bool(token))
check("register returns user id", isinstance(user_id, int))

r = client.post("/api/v1/auth/register", json={"name": "Dup", "email": "test@verdict.ai", "password": "hunter22"})
check("duplicate register -> 400", r.status_code == 400, r.status_code)

print("\n=== Auth: login ===")
r = client.post("/api/v1/auth/login", json={"email": "test@verdict.ai", "password": "wrongpass"})
check("wrong password -> 401", r.status_code == 401, r.status_code)

r = client.post("/api/v1/auth/login", json={"email": "test@verdict.ai", "password": "hunter22"})
check("correct login -> 200", r.status_code == 200, r.status_code)
token = r.json()["access_token"]
auth_headers = {"Authorization": f"Bearer {token}"}

r = client.get("/api/v1/auth/me", headers=auth_headers)
check("GET /auth/me with valid token -> 200", r.status_code == 200 and r.json()["email"] == "test@verdict.ai")

r = client.get("/api/v1/auth/me", headers={"Authorization": "Bearer garbage.token.here"})
check("GET /auth/me with bad token -> 401", r.status_code == 401, r.status_code)

print("\n=== Auth: validation errors (shape the frontend must parse) ===")
r = client.post("/api/v1/auth/register", json={"name": "X", "email": "not-an-email", "password": "hunter22"})
check("register with invalid email -> 422", r.status_code == 422, r.status_code)
detail = r.json().get("detail")
check("422 detail is a list of {loc, msg, type} (what formatApiError() must handle)",
      isinstance(detail, list) and all({"loc", "msg"} <= set(d.keys()) for d in detail), detail)

r = client.post("/api/v1/auth/register", json={"name": "X", "email": "shortpass@verdict.ai", "password": "abc"})
check("register with too-short password -> 422", r.status_code == 422, r.status_code)

print("\n=== Auth: expired token is rejected (not just malformed ones) ===")
import jwt as _pyjwt, datetime as _dt
from backend.utils.config import settings as _settings
expired = _pyjwt.encode(
    {"sub": str(user_id), "email": "test@verdict.ai", "exp": _dt.datetime.now(_dt.timezone.utc) - _dt.timedelta(minutes=1)},
    _settings.JWT_SECRET, algorithm=_settings.JWT_ALGORITHM,
)
r = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {expired}"})
check("expired token -> 401", r.status_code == 401, r.status_code)

print("\n=== Products ===")
r = client.post("/api/v1/products/search", json={"query": "running shoes", "max_price": 5000}, headers=auth_headers)
check("search with token -> 200", r.status_code == 200, (r.status_code, r.text[:300]))
products = r.json().get("products", [])
check("search returns products", len(products) > 0, len(products))
check("search respects max_price filter", all(p["price"] <= 5000 for p in products))

print("\n=== Insights ===")
r = client.post("/api/v1/insights/generate", json={"products": products, "query": "running shoes"}, headers=auth_headers)
check("insights -> 200", r.status_code == 200, (r.status_code, r.text[:300]))
check("insights has summary", bool(r.json().get("summary")))

print("\n=== Advisor compare (previously crashed on every call) ===")
r = client.post("/api/v1/advisor/compare", json={"products": products[:2]}, headers=auth_headers)
check("compare 2 products -> 200 (no ValueError crash)", r.status_code == 200, (r.status_code, r.text[:500]))
check("compare returns summary", bool(r.json().get("summary")) if r.status_code == 200 else False)

r = client.post("/api/v1/advisor/compare", json={"products": [products[0]]}, headers=auth_headers)
# Pydantic's `min_length=2` on ComparisonRequest.products rejects this at the
# schema level (422) before the handler's own `if len(...) < 2: raise 400`
# check ever runs — that manual check is unreachable dead code, not a bug.
check("compare with <2 products -> 422 (schema validation, not the handler's 400)", r.status_code == 422, r.status_code)

print("\n=== Advisor chat (Groq unreachable in sandbox -> exercises fallback path) ===")
r = client.post("/api/v1/advisor/chat", json={"message": "what's the cheapest one?", "history": [], "current_products": products[:3]}, headers=auth_headers)
check("chat -> 200 even without live Groq", r.status_code == 200, (r.status_code, r.text[:300]))
check("chat returns non-empty reply", bool(r.json().get("reply")))
check("chat returns updated history", len(r.json().get("history", [])) == 2)

print("\n=== Wishlist ===")
r = client.post("/api/v1/user/wishlist/add", json={"user_id": 99999, "product": products[0]}, headers=auth_headers)
check("add to wishlist (spoofed user_id in body is ignored) -> 200", r.status_code == 200, (r.status_code, r.text[:300]))
wishlist_id = r.json().get("wishlist_id")

r = client.get(f"/api/v1/user/wishlist/{user_id}", headers=auth_headers)
check("item actually landed under the authenticated user, not the spoofed 99999", r.status_code == 200 and r.json().get("count") == 1, r.json())

r = client.get("/api/v1/user/wishlist/99999", headers=auth_headers)
check("get someone else's wishlist -> 403", r.status_code == 403, r.status_code)

r = client.delete(f"/api/v1/user/wishlist/{user_id}/{wishlist_id}", headers=auth_headers)
check("remove wishlist item -> 200", r.status_code == 200, r.status_code)

client.post("/api/v1/user/wishlist/add", json={"user_id": user_id, "product": products[1]}, headers=auth_headers)
r = client.delete(f"/api/v1/user/wishlist/{user_id}/clear", headers=auth_headers)
check("clear wishlist -> 200", r.status_code == 200, r.status_code)
r = client.get(f"/api/v1/user/wishlist/{user_id}", headers=auth_headers)
check("wishlist empty after clear", r.json().get("count") == 0, r.json())

print("\n=== Search history ===")
r = client.get(f"/api/v1/user/history/{user_id}", headers=auth_headers)
check("get history -> 200", r.status_code == 200)
check("history has the earlier search logged", r.json().get("count", 0) >= 1, r.json())
hist_items = r.json().get("items", [])

if hist_items:
    hid = hist_items[0]["id"]
    r = client.delete(f"/api/v1/user/history/{user_id}/{hid}", headers=auth_headers)
    check("delete single history item -> 200", r.status_code == 200, r.status_code)

client.post("/api/v1/products/search", json={"query": "hoodie"}, headers=auth_headers)
r = client.delete(f"/api/v1/user/history/{user_id}/clear", headers=auth_headers)
check("clear history -> 200", r.status_code == 200, r.status_code)
r = client.get(f"/api/v1/user/history/{user_id}", headers=auth_headers)
check("history empty after clear", r.json().get("count") == 0, r.json())

print("\n=== Budget planner (Groq unreachable -> exercises rule-based fallback) ===")
r = client.post("/api/v1/user/budget/plan", json={"user_id": 1, "budget": 8000, "category": "Laptop & Tech setup"}, headers=auth_headers)
check("budget plan -> 200", r.status_code == 200, (r.status_code, r.text[:400]))
body = r.json()
check("budget plan has allocations with item/allocated/percentage/suggestion keys",
      all({"item", "allocated", "percentage", "suggestion"} <= set(a.keys()) for a in body.get("allocations", [])),
      body.get("allocations"))
check("budget total_allocated present", "total_allocated" in body)

r = client.get(f"/api/v1/user/budget/history/{user_id}", headers=auth_headers)
check("budget history -> 200", r.status_code == 200, r.status_code)
check("budget history has at least 1 plan", len(r.json().get("plans", [])) >= 1)

print(f"\n{'='*50}\n{len(passed)} passed, {len(failed)} failed\n{'='*50}")
if failed:
    print("FAILED:", failed)
    sys.exit(1)
