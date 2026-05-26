"""用户鉴权 — bcrypt 密码 + JWT 会话

设计:
  - 管理员账号只允许通过独立管理后台首次初始化创建,不在代码中内置默认账号密码
  - JWT HS256,有效期 30 天,无 refresh token(简单)
  - 普通 REST API 用 Header `Authorization: Bearer xxx`
  - WebSocket 用 query string ?token=xxx
"""
import os
import uuid
import time
import datetime as _dt
from typing import Optional

import jwt
from fastapi import HTTPException, Depends, Header, WebSocket, status
from passlib.context import CryptContext

from .store import _get_conn, get_character, save_character

# ─────────────────────────────────────────────────────────────────
# 密码 + JWT
# ─────────────────────────────────────────────────────────────────
_pwd = CryptContext(schemes=["bcrypt"], deprecated="auto")
_JWT_SECRET = os.getenv("JWT_SECRET", "lingshu-dev-secret-change-me-in-prod")
_JWT_ALG = "HS256"
_TOKEN_DAYS = int(os.getenv("JWT_DAYS", "30"))
ALLOW_REGISTER = os.getenv("ALLOW_REGISTER", "true").lower() in ("1", "true", "yes")


def hash_password(plain: str) -> str:
    return _pwd.hash(plain)


def verify_password(plain: str, hashed: str) -> bool:
    try:
        return _pwd.verify(plain, hashed)
    except Exception:
        return False


def create_access_token(user_id: str, username: str, is_admin: bool = False) -> str:
    payload = {
        "sub": user_id,
        "username": username,
        "is_admin": bool(is_admin),
        "iat": int(time.time()),
        "exp": int(time.time()) + _TOKEN_DAYS * 86400,
    }
    return jwt.encode(payload, _JWT_SECRET, algorithm=_JWT_ALG)


def decode_token(token: str) -> Optional[dict]:
    try:
        return jwt.decode(token, _JWT_SECRET, algorithms=[_JWT_ALG])
    except (jwt.ExpiredSignatureError, jwt.InvalidTokenError):
        return None


# ─────────────────────────────────────────────────────────────────
# 用户 CRUD
# ─────────────────────────────────────────────────────────────────
def get_user_by_id(user_id: str) -> Optional[dict]:
    conn = _get_conn()
    row = conn.execute(
        "SELECT id, username, password_hash, is_admin, created_at, last_login_at FROM users WHERE id=?",
        (user_id,)
    ).fetchone()
    if not row:
        return None
    return {
        "id": row[0], "username": row[1], "password_hash": row[2],
        "is_admin": bool(row[3]), "created_at": row[4], "last_login_at": row[5],
    }


def get_user_by_name(username: str) -> Optional[dict]:
    conn = _get_conn()
    row = conn.execute(
        "SELECT id, username, password_hash, is_admin, created_at, last_login_at FROM users WHERE username=?",
        (username,)
    ).fetchone()
    if not row:
        return None
    return {
        "id": row[0], "username": row[1], "password_hash": row[2],
        "is_admin": bool(row[3]), "created_at": row[4], "last_login_at": row[5],
    }


def count_users() -> int:
    conn = _get_conn()
    return conn.execute("SELECT COUNT(*) FROM users").fetchone()[0]


def count_admins() -> int:
    conn = _get_conn()
    return conn.execute("SELECT COUNT(*) FROM users WHERE is_admin = 1").fetchone()[0]


def create_user(username: str, password: str, is_admin: bool = False, user_id: Optional[str] = None) -> dict:
    """创建用户。返回 user dict(不含密码 hash)"""
    if get_user_by_name(username):
        raise HTTPException(status.HTTP_409_CONFLICT, f"用户名 '{username}' 已被占用")
    if len(username) < 2 or len(username) > 32:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "用户名长度需 2-32")
    if len(password) < 4:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "密码至少 4 位")

    uid = user_id or f"u_{uuid.uuid4().hex[:12]}"
    conn = _get_conn()
    conn.execute(
        "INSERT INTO users (id, username, password_hash, is_admin) VALUES (?, ?, ?, ?)",
        (uid, username, hash_password(password), 1 if is_admin else 0),
    )
    conn.commit()
    return {"id": uid, "username": username, "is_admin": is_admin}


def update_last_login(user_id: str):
    conn = _get_conn()
    conn.execute("UPDATE users SET last_login_at=datetime('now') WHERE id=?", (user_id,))
    conn.commit()


def set_admin(user_id: str, is_admin: bool):
    conn = _get_conn()
    conn.execute("UPDATE users SET is_admin=? WHERE id=?", (1 if is_admin else 0, user_id))
    conn.commit()


def list_users(limit: int = 100) -> list:
    conn = _get_conn()
    rows = conn.execute(
        "SELECT id, username, is_admin, created_at, last_login_at FROM users ORDER BY created_at DESC LIMIT ?",
        (limit,)
    ).fetchall()
    return [
        {"id": r[0], "username": r[1], "is_admin": bool(r[2]), "created_at": r[3], "last_login_at": r[4]}
        for r in rows
    ]


# ─────────────────────────────────────────────────────────────────
# 接管 demo_player 旧数据
# ─────────────────────────────────────────────────────────────────
def bootstrap_demo_user():
    """保留启动钩子,但不再创建任何默认账号。

    管理员必须从独立后台入口首次配置账号和密码,避免代码或日志中出现默认凭据。
    """
    if count_admins() == 0:
        print("[auth] 尚未配置管理员账号,请打开独立管理后台完成首次初始化")


# ─────────────────────────────────────────────────────────────────
# FastAPI 依赖项
# ─────────────────────────────────────────────────────────────────
def get_current_user(authorization: Optional[str] = Header(None)) -> dict:
    """从 Authorization: Bearer xxx 取 user,缺/无效 → 401"""
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "缺少认证")
    token = authorization[7:]
    payload = decode_token(token)
    if not payload:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "认证已过期或无效")
    user = get_user_by_id(payload["sub"])
    if not user:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "用户不存在")
    return user


def get_current_user_optional(authorization: Optional[str] = Header(None)) -> Optional[dict]:
    """同上但允许未登录(返回 None)。用于既支持登录又支持游客的端点"""
    if not authorization or not authorization.startswith("Bearer "):
        return None
    payload = decode_token(authorization[7:])
    if not payload:
        return None
    return get_user_by_id(payload["sub"])


def require_admin(user: dict = Depends(get_current_user)) -> dict:
    if not user.get("is_admin"):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "需要管理员权限")
    return user


async def get_ws_user(websocket: WebSocket) -> Optional[dict]:
    """WS 鉴权:从 ?token=xxx 取 user。失败返回 None,由调用方处理 close"""
    token = websocket.query_params.get("token")
    if not token:
        return None
    payload = decode_token(token)
    if not payload:
        return None
    return get_user_by_id(payload["sub"])
