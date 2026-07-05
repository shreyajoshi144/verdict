from typing import Optional
from backend.models.models import UserRegister, UserLogin, UserPublic, TokenResponse
from backend.database.database import execute_query
from backend.utils.security import hash_password, verify_password, create_access_token
from backend.utils.logger import get_logger

logger = get_logger(__name__)


def register(request: UserRegister) -> TokenResponse:
    existing = execute_query("SELECT id FROM users WHERE email = %s", (request.email,))
    if existing:
        raise ValueError("An account with this email already exists.")

    password_hash = hash_password(request.password)
    user_id = execute_query(
        "INSERT INTO users (name, email, password_hash) VALUES (%s, %s, %s)",
        (request.name, request.email, password_hash),
        fetch=False,
    )
    logger.info(f"Registered new user: {request.email}")
    token = create_access_token(user_id, request.email)
    return TokenResponse(access_token=token, user=UserPublic(id=user_id, name=request.name, email=request.email))


def login(request: UserLogin) -> TokenResponse:
    rows = execute_query(
        "SELECT id, name, email, password_hash FROM users WHERE email = %s",
        (request.email,),
    )
    if not rows:
        raise ValueError("Invalid email or password.")

    user = rows[0]
    if not user.get("password_hash") or not verify_password(request.password, user["password_hash"]):
        raise ValueError("Invalid email or password.")

    logger.info(f"User logged in: {request.email}")
    token = create_access_token(user["id"], user["email"])
    return TokenResponse(
        access_token=token,
        user=UserPublic(id=user["id"], name=user["name"], email=user["email"]),
    )


def get_user_by_id(user_id: int) -> Optional[dict]:
    rows = execute_query("SELECT id, name, email FROM users WHERE id = %s", (user_id,))
    return rows[0] if rows else None
