import httpx
from fastapi import Header, HTTPException
from app.config import settings

async def get_current_user(authorization: str | None = Header(default=None)) -> str:
    """Supabase validates token; no unsigned JWT decoding or client-supplied user ID."""
    cfg = settings()
    if not cfg.supabase_url or not cfg.supabase_publishable_key:
        raise HTTPException(503, "Authentication backend is not configured")
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(401, "Bearer token required")
    token = authorization.removeprefix("Bearer ").strip()
    if not token:
        raise HTTPException(401, "Bearer token required")
    try:
        async with httpx.AsyncClient(timeout=12) as client:
            res = await client.get(
                f"{cfg.supabase_url.rstrip('/')}/auth/v1/user",
                headers={"Authorization": f"Bearer {token}", "apikey": cfg.supabase_publishable_key},
            )
    except httpx.RequestError:
        raise HTTPException(503, "Authentication service unavailable")
    if res.status_code != 200:
        raise HTTPException(401, "Invalid or expired access token")
    user_id = res.json().get("id")
    if not user_id:
        raise HTTPException(401, "Invalid user response")
    return str(user_id)
