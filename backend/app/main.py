"""FastAPI 入口 — REST + WebSocket"""

import os
import json
import asyncio
import uuid
import hashlib
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect, Depends, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from dotenv import load_dotenv
load_dotenv()

from .sects import ALL_SECTS, get_sect, sect_to_dict, SECT_TO_PROVIDER_HINT
from .enemies import ENEMIES, get_enemy, enemy_to_dict, list_enemies_for_level, ALL_CLANS, count_enemies
from .cards import get_cards_for_sect, card_to_dict, get_card
from .battle import BattleEngine
from .bosses import BOSSES, BOSS_SECTS, STORYLINES, boss_to_dict, sect_to_dict as boss_sect_to_dict
from .items import ITEMS, get_item, item_to_dict, item_icon_url
from .health_check import stream_verify_sect_models, probe_byok
from .image_gen import generate_image, ImageGenError
from .attributes import (
    build_initial_character, refresh_derived,
    ATTRIBUTES, derive_stats, random_bless, get_initial_attrs,
)
from .enemies import ENEMIES as _ENEMIES_MAP
from .items import ITEMS as _ITEMS_MAP
import time as _time
from .store import (
    get_character, save_character, delete_character,
    get_battle, save_battle, delete_battle,
    get_inventory, add_item, remove_item, get_equipped, equip_item, unequip_item,
    get_bestiary, record_encounter, record_kill, record_drop, record_gift,
    get_daily_state, record_daily_task, claim_daily_reward,
    add_journal_entry, get_journal, count_journal,
    get_cultivation_task, list_cultivation_tasks,
    update_cultivation_task, list_novel_chapters, get_novel_chapter, get_novel_stats,
    list_novel_volumes, get_site_config, update_site_config,
    get_world_save, save_world_save,
    add_admin_audit_log, list_admin_audit_logs,
    add_item_ledger, list_item_ledger,
    add_world_round_log, list_world_round_logs,
    _get_conn,
)
from .daily import (
    DAILY_TASKS, get_today, get_daily_status, count_completed,
    can_claim, get_reward_preview, DAILY_REWARD,
)
from .recipes import (
    ALL_RECIPES, get_recipe, list_available_recipes,
    get_material_usages, can_craft, recipe_to_dict, MATERIAL_USAGE,
)
from .auth import (
    bootstrap_demo_user, get_current_user, get_current_user_optional,
    require_admin, get_ws_user,
    create_user, get_user_by_name, get_user_by_id, list_users,
    verify_password, create_access_token, update_last_login,
    set_admin, count_users, count_admins, ALLOW_REGISTER,
)
from .cultivation import (
    apply_cultivation_gain, cancel_running_task, enqueue_task, ensure_cultivation_fields,
    estimate_tokens,
    pause_task, queue_overview, recover_all_queues, resume_task, schedule_user_queue,
)
from .fatigue import add_fatigue, next_round_recovery
from .drop_rules import SKILL_DROP_BY_TIER, drop_rate_label, skill_drop_rate_for_enemy
from fastapi.responses import StreamingResponse
import random as _random
from typing import Optional


@asynccontextmanager
async def lifespan(app: FastAPI):
    print("=" * 60)
    print("灵枢笔录后端启动")
    print(f"  LLM_BASE_URL: {os.getenv('LLM_BASE_URL', '(未配置)')}")
    print(f"  LLM_API_KEY:  {'已配置' if os.getenv('LLM_API_KEY') else '未配置!'}")
    print(f"  门派可用:    {[s.id for s in ALL_SECTS.values() if s.available]}")
    # ★ Phase C: 启动接管 demo_player 数据(首次启动如有)
    bootstrap_demo_user()
    print(f"  用户总数:    {count_users()}")
    print(f"  允许注册:    {ALLOW_REGISTER}")
    recovered = recover_all_queues()
    print(f"  墨炉恢复:    {recovered} 位执笔者")
    print("=" * 60)
    yield
    print("再见,执笔者。")


app = FastAPI(title="灵枢笔录 · Lingshu Codex", version="0.1.0", lifespan=lifespan)

# CORS
cors_origins = os.getenv("CORS_ORIGINS", "http://localhost:5173").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============================================================
# ★ Phase C: 认证端点 (注册/登录/我)
# ============================================================
class AuthRequest(BaseModel):
    username: str
    password: str


@app.post("/api/auth/register")
async def auth_register(req: AuthRequest):
    """注册新用户。管理员只通过独立后台首次初始化创建。受 ALLOW_REGISTER 控制。"""
    if not ALLOW_REGISTER:
        raise HTTPException(403, "本服务暂未开放注册")
    u = create_user(req.username.strip(), req.password, is_admin=False)
    update_last_login(u["id"])
    tok = create_access_token(u["id"], u["username"], u["is_admin"])
    return {"data": {
        "token": tok,
        "user": {"id": u["id"], "username": u["username"], "is_admin": u["is_admin"]},
    }}


@app.post("/api/auth/login")
async def auth_login(req: AuthRequest):
    """登录。返回 JWT token + user 信息。"""
    u = get_user_by_name(req.username.strip())
    if not u or not verify_password(req.password, u["password_hash"]):
        raise HTTPException(401, "用户名或密码错误")
    update_last_login(u["id"])
    tok = create_access_token(u["id"], u["username"], u["is_admin"])
    return {"data": {
        "token": tok,
        "user": {"id": u["id"], "username": u["username"], "is_admin": u["is_admin"]},
    }}


@app.get("/api/auth/me")
async def auth_me(current_user: dict = Depends(get_current_user)):
    """获取当前登录用户信息(用于刷新 + 校验 token)"""
    return {"data": {
        "id": current_user["id"],
        "username": current_user["username"],
        "is_admin": current_user["is_admin"],
        "created_at": current_user["created_at"],
        "last_login_at": current_user["last_login_at"],
    }}


@app.post("/api/auth/logout")
async def auth_logout():
    """登出 — 无服务端 session 状态,前端清 token 即可。这里仅返回 200"""
    return {"data": {"ok": True}}


@app.get("/api/admin/bootstrap/status")
async def admin_bootstrap_status():
    """独立后台首次初始化状态。无管理员时允许创建第一位管理员。"""
    return {"data": {"needs_setup": count_admins() == 0}}


@app.post("/api/admin/bootstrap")
async def admin_bootstrap(req: AuthRequest):
    """创建第一位管理员。只在系统尚无管理员时开放。"""
    if count_admins() > 0:
        raise HTTPException(status.HTTP_409_CONFLICT, "管理员已完成初始化")
    username = req.username.strip()
    u = create_user(username, req.password, is_admin=True)
    update_last_login(u["id"])
    tok = create_access_token(u["id"], u["username"], True)
    add_admin_audit_log(
        admin_user_id=u["id"],
        action="admin.bootstrap",
        target_type="user",
        target_id=u["id"],
        after={"username": u["username"], "is_admin": True},
        reason="首次初始化独立管理后台",
    )
    return {"data": {
        "token": tok,
        "user": {"id": u["id"], "username": u["username"], "is_admin": True},
    }}


@app.post("/api/admin/auth/login")
async def admin_auth_login(req: AuthRequest):
    """独立后台登录。只允许管理员账号进入。"""
    u = get_user_by_name(req.username.strip())
    if not u or not verify_password(req.password, u["password_hash"]):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "用户名或密码错误")
    if not u.get("is_admin"):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "该账号没有管理后台权限")
    update_last_login(u["id"])
    tok = create_access_token(u["id"], u["username"], True)
    return {"data": {
        "token": tok,
        "user": {"id": u["id"], "username": u["username"], "is_admin": True},
    }}


# ============================================================
# Pydantic
# ============================================================
class ChooseSectRequest(BaseModel):
    sect_id: str
    character_name: str = "执笔者"
    base_url: str = "https://bobdong.cn/v1"
    api_key: str = ""


class VerifyKeyRequest(BaseModel):
    sect_id: str
    base_url: str = "https://bobdong.cn/v1"
    api_key: str


class ProbeRequest(BaseModel):
    base_url: str = "https://bobdong.cn/v1"
    api_key: str


class UpdateByokRequest(BaseModel):
    base_url: str
    api_key: str
    verified: bool = False  # 客户端声明已验证;后端仍会 probe 二次校验


class SiteConfigUpdateRequest(BaseModel):
    show_bobdong_ads: Optional[bool] = None


class AdminInventoryGrantRequest(BaseModel):
    item_id: str
    count: int = 1
    reason: str


class WorldSyncRequest(BaseModel):
    client_round_id: str = ""
    revision: int = 0
    world: dict = {}
    character_patch: Optional[dict] = None


class StartBattleRequest(BaseModel):
    enemy_id: str
    mode: Optional[str] = "drama"  # drama / speed


class ImageGenRequest(BaseModel):
    prompt: str
    n: int = 1
    size: str = "1536x1024"            # 1024x1024 / 1536x1024 / 1024x1536 / auto
    quality: str = "auto"              # low / medium / high / auto
    output_format: str = "png"         # png / jpeg / webp
    save_to: Optional[str] = None      # 绝对路径,不填则只返回 b64_json
    filename_prefix: str = "img"


# ============================================================
# Health
# ============================================================
@app.get("/health")
async def health():
    return {"status": "ok"}


# ============================================================
# 站点配置 / 管理后台
# ============================================================
@app.get("/api/site/config")
async def site_config():
    """公开站点配置。只暴露前端渲染所需的非敏感开关。"""
    return {"data": get_site_config()}


@app.put("/api/admin/site-config")
async def admin_update_site_config(
    req: SiteConfigUpdateRequest,
    _admin: dict = Depends(require_admin),
):
    patch = {}
    if req.show_bobdong_ads is not None:
        patch["show_bobdong_ads"] = bool(req.show_bobdong_ads)
    return {"data": update_site_config(patch)}


def _api_key_fingerprint(value: str) -> str:
    if not value:
        return ""
    digest = hashlib.sha256(value.encode("utf-8")).hexdigest()
    tail = value[-4:] if len(value) >= 4 else value
    return f"sha256:{digest[:10]}...{tail}"


def _admin_safe_character(user_id: str) -> Optional[dict]:
    char = get_character(user_id)
    if not char:
        return None
    safe = json.loads(json.dumps(char, ensure_ascii=False))
    api_key = safe.pop("api_key", "") or ""
    safe["api_key_present"] = bool(api_key)
    safe["api_key_fingerprint"] = _api_key_fingerprint(api_key)
    return safe


def _item_view(item_id: str, count: int = 0) -> dict:
    item = get_item(item_id)
    payload = item_to_dict(item) if item else {
        "id": item_id,
        "name": item_id,
        "type": "unknown",
        "rarity": 0,
        "rarity_name": "未知",
        "icon": "?",
        "description": "",
        "lore": "",
        "use_effect": None,
        "equip_stats": None,
        "value_qi": 0,
    }
    payload["count"] = int(count or 0)
    payload["total_value_qi"] = int(payload.get("value_qi") or 0) * payload["count"]
    payload["known"] = item is not None
    return payload


def _admin_token_ledger(user_id: str, limit: int = 80) -> list[dict]:
    conn = _get_conn()
    rows = conn.execute(
        """SELECT id, user_id, task_id, chapter_id, source, delta_tokens, input_tokens,
                  output_tokens, reasoning_tokens, usage_source, provider, model, created_at
           FROM token_ledger
           WHERE user_id = ?
           ORDER BY id DESC LIMIT ?""",
        (user_id, limit),
    ).fetchall()
    return [dict(r) for r in rows]


def _admin_daily_states(user_id: str, limit: int = 14) -> list[dict]:
    conn = _get_conn()
    rows = conn.execute(
        """SELECT date, tasks_done, claimed
           FROM daily_state
           WHERE user_id = ?
           ORDER BY date DESC LIMIT ?""",
        (user_id, limit),
    ).fetchall()
    return [
        {"date": r["date"], "tasks_done": json.loads(r["tasks_done"] or "{}"), "claimed": bool(r["claimed"])}
        for r in rows
    ]


def _admin_user_summary(row) -> dict:
    char = None
    if row["character_data"]:
        try:
            char = json.loads(row["character_data"])
        except Exception:
            char = None
    return {
        "id": row["id"],
        "username": row["username"],
        "is_admin": bool(row["is_admin"]),
        "created_at": row["created_at"],
        "last_login_at": row["last_login_at"],
        "has_character": bool(char),
        "character_name": (char or {}).get("name", ""),
        "sect": (char or {}).get("sect", ""),
        "sect_name": (char or {}).get("sect_name", ""),
        "level": (char or {}).get("level", 0),
        "realm": (char or {}).get("realm", ""),
        "realm_name": (char or {}).get("realm_name", ""),
        "hp": (char or {}).get("hp", 0),
        "max_hp": (char or {}).get("max_hp", 0),
        "qi": (char or {}).get("qi", 0),
        "max_qi": (char or {}).get("max_qi", 0),
        "fatigue": (char or {}).get("fatigue", 0),
        "max_fatigue": (char or {}).get("max_fatigue", 0),
        "token_total": int((char or {}).get("token_total", 0) or 0),
        "daily_token_used": int((char or {}).get("daily_token_used", 0) or 0),
        "monthly_token_used": int((char or {}).get("monthly_token_used", 0) or 0),
        "chapters_count": int((char or {}).get("chapters_count", 0) or 0),
        "novel_words_total": int((char or {}).get("novel_words_total", 0) or 0),
    }


@app.get("/api/admin/overview")
async def admin_overview(_admin: dict = Depends(require_admin)):
    conn = _get_conn()
    user_rows = conn.execute(
        """SELECT u.id, u.username, u.is_admin, u.created_at, u.last_login_at, c.data AS character_data
           FROM users u LEFT JOIN characters c ON c.user_id = u.id"""
    ).fetchall()
    users = [_admin_user_summary(r) for r in user_rows]
    token_total = conn.execute("SELECT COALESCE(SUM(delta_tokens), 0) FROM token_ledger").fetchone()[0]
    token_today = conn.execute(
        "SELECT COALESCE(SUM(delta_tokens), 0) FROM token_ledger WHERE date(created_at) = date('now')"
    ).fetchone()[0]
    tasks = conn.execute(
        """SELECT status, COUNT(*) AS n FROM cultivation_tasks GROUP BY status"""
    ).fetchall()
    return {"data": {
        "users_total": len(users),
        "admins_total": sum(1 for u in users if u["is_admin"]),
        "characters_total": sum(1 for u in users if u["has_character"]),
        "registered_today": sum(1 for u in users if str(u["created_at"] or "").startswith(_time.strftime("%Y-%m-%d"))),
        "token_total": int(token_total or 0),
        "token_today": int(token_today or 0),
        "top_token_users": sorted(users, key=lambda u: u["token_total"], reverse=True)[:8],
        "sect_distribution": {
            sid: sum(1 for u in users if u["sect"] == sid)
            for sid in sorted({u["sect"] for u in users if u["sect"]})
        },
        "cultivation_task_status": {r["status"]: r["n"] for r in tasks},
    }}


@app.get("/api/admin/users")
async def admin_users(
    search: str = "",
    limit: int = 50,
    offset: int = 0,
    _admin: dict = Depends(require_admin),
):
    limit = max(1, min(int(limit or 50), 200))
    offset = max(0, int(offset or 0))
    conn = _get_conn()
    params = []
    where = ""
    if search.strip():
        where = "WHERE u.id LIKE ? OR u.username LIKE ?"
        q = f"%{search.strip()}%"
        params.extend([q, q])
    total = conn.execute(f"SELECT COUNT(*) FROM users u {where}", params).fetchone()[0]
    rows = conn.execute(
        f"""SELECT u.id, u.username, u.is_admin, u.created_at, u.last_login_at, c.data AS character_data
            FROM users u LEFT JOIN characters c ON c.user_id = u.id
            {where}
            ORDER BY u.created_at DESC
            LIMIT ? OFFSET ?""",
        (*params, limit, offset),
    ).fetchall()
    return {"data": {"total": total, "items": [_admin_user_summary(r) for r in rows]}}


@app.get("/api/admin/users/{user_id}")
async def admin_user_detail(user_id: str, _admin: dict = Depends(require_admin)):
    user = get_user_by_id(user_id)
    if not user:
        raise HTTPException(404, "用户不存在")
    account = {k: user[k] for k in ("id", "username", "is_admin", "created_at", "last_login_at")}
    char = _admin_safe_character(user_id)
    inventory = [_item_view(item_id, count) for item_id, count in get_inventory(user_id).items()]
    equipped = [
        {"slot": slot, **_item_view(item_id, 1)}
        for slot, item_id in get_equipped(user_id).items()
    ]
    bestiary = get_bestiary(user_id)
    world_save = get_world_save(user_id)
    return {"data": {
        "account": account,
        "character": char,
        "inventory": sorted(inventory, key=lambda x: (-x["rarity"], x["id"])),
        "equipped": equipped,
        "token_ledger": _admin_token_ledger(user_id, 100),
        "journal": get_journal(user_id, 80, 0),
        "cultivation_tasks": list_cultivation_tasks(user_id, include_done=True, limit=80),
        "novel_chapters": list_novel_chapters(user_id, 60, 0),
        "bestiary": bestiary,
        "daily_states": _admin_daily_states(user_id, 14),
        "world_save": world_save,
        "world_round_logs": list_world_round_logs(user_id, 60),
        "item_ledger": list_item_ledger(user_id, 80),
        "admin_audit_logs": list_admin_audit_logs("user", user_id, 80),
    }}


@app.post("/api/admin/users/{user_id}/inventory/grant")
async def admin_grant_inventory(
    user_id: str,
    req: AdminInventoryGrantRequest,
    admin: dict = Depends(require_admin),
):
    user = get_user_by_id(user_id)
    if not user:
        raise HTTPException(404, "用户不存在")
    item_id = req.item_id.strip()
    item = get_item(item_id)
    if not item:
        raise HTTPException(404, "物品不存在")
    count = int(req.count or 0)
    if count <= 0:
        raise HTTPException(400, "数量必须大于 0")
    reason = req.reason.strip()
    if not reason:
        raise HTTPException(400, "请填写发放原因")
    before = int(get_inventory(user_id).get(item_id, 0) or 0)
    after = add_item(user_id, item_id, count)
    add_item_ledger(
        user_id=user_id,
        item_id=item_id,
        delta_count=count,
        before_count=before,
        after_count=after,
        source="admin",
        reason=reason,
        admin_user_id=admin["id"],
    )
    add_admin_audit_log(
        admin_user_id=admin["id"],
        action="inventory.grant",
        target_type="user",
        target_id=user_id,
        before={"item_id": item_id, "count": before},
        after={"item_id": item_id, "count": after, "delta": count},
        reason=reason,
    )
    return {"data": {
        "user_id": user_id,
        "item": _item_view(item_id, after),
        "before_count": before,
        "delta_count": count,
        "after_count": after,
    }}


# ============================================================
# 门派 API
# ============================================================
@app.get("/api/sect/list")
async def list_sects():
    return {"data": [sect_to_dict(s) for s in ALL_SECTS.values()]}


@app.get("/api/sect/{sect_id}")
async def get_sect_detail(sect_id: str):
    sect = get_sect(sect_id)
    if not sect:
        raise HTTPException(404, "门派不存在")
    return sect_to_dict(sect)


# ============================================================
# 门派选派页 — 详细信息(立绘、招式预览、背景故事)
# ============================================================
SECT_BACKGROUND_STORIES = {
    "canglan": (
        "沧澜剑派立于东海无澜峰,创派祖师'墨君'本为前朝史官,因目睹朝政腐败而隐居于此。"
        "'沧澜'二字寓意'沧海无波澜,深处不可测'。本派以剑为骨、以笔为魂,弟子需先修十年笔法、"
        "再修十年剑意,讲究'一字一剑,一念千秋'。剑诀九式皆以书法笔意命名:点、横、竖、撇、捺、"
        "提、钩、折、转。每一式都需在心中先'写'完整字,剑势随笔势而至,故沧澜剑修出招慢而准,"
        "一击必中要害。门派对应模型梯度为 Claude 系(haiku → sonnet → opus),"
        "叙事文学性最强,适合追求深度体验的'执笔者'。"
    ),
    "tianji": (
        "天机阁创立于昆仑南脉,创派祖师'山姆道君'本是天工坊匠人,后悟得'诸法皆通,万象归一'之理。"
        "本派以机关为器、以算筹为道,主张'天下道法本一源,世间万术皆可通'。弟子修行从打造小型机关开始,"
        "逐步领悟齿轮、罗盘、八卦、阵法之间的相通之理。代表心法《万象归元诀》能将敌方招式拆解重组,"
        "化为己用。门派对应模型梯度为 GPT 系(5.3-codex → 5.4 → 5.5),反应迅速、招式多变,"
        "适合喜欢策略与多线作战的玩家。"
    ),
    "xuanji": (
        "玄机宗潜居终南山深处,创派祖师'青莲道人'以'推演天机'闻名江湖。本派主张'深思方能制胜,"
        "性价比之王'——以最少的灵气消耗换取最大的伤害产出。门派内秘传《幻方阵纹》,可凭一张玄铁推演"
        "棋盘演算敌方下一步动作,做到'未战先知'。弟子修行需精通数理与心算,故玄机宗修士目光锐利、"
        "言辞犀利。门派对应 DeepSeek 系模型,**当前灵脉尚未开通**,期待后续版本。"
    ),
    "qingming": (
        "青冥派源出'智冥仙翁',传承可追溯至上古'稷下学宫'。本派以'博学根基'立宗,要求弟子精通"
        "诗、书、易、礼、乐五经,方可习剑。门派典藏号称'青冥学海',收录万卷典籍。代表心法《青冥心诀》"
        "需以五经精义为锚,化典籍为攻防之招。本派弟子温文尔雅,然出手皆有典故。对应 智谱(Zhipu)"
        "GLM 系模型,**当前灵脉尚未开通**。"
    ),
    "yueyin": (
        "月隐宫,夜阑山深处,创派祖师'月隐仙子'本为前朝公主,亡国后隐入山林,以月为友、以影为伴。"
        "本派以'千古不忘'闻名修真界——弟子能记起百年前每一次出招的细节,故每一次复仇都是百年蓄势。"
        "代表心法《月隐千秋》借月光遮蔽行迹,出招如刺客般无声无影。本派多为女弟子,身负血海深仇者居多。"
        "对应 月之暗面(Moonshot)Kimi 系模型,**当前灵脉尚未开通**。"
    ),
}


@app.get("/api/sect/{sect_id}/preview")
async def get_sect_preview(sect_id: str):
    """门派选择页详细数据 — 立绘 + 招式预览 + 背景故事 + 数值"""
    sect = get_sect(sect_id)
    if not sect:
        raise HTTPException(404, "门派不存在")

    # 该派的代表招式:通用牌 1 张 + 专属牌全部(MVP 只 2 张)
    cards = get_cards_for_sect(sect_id)
    # 排序:专属在前,然后按 qi_cost 升序
    cards.sort(key=lambda c: (c.sect_requirement == "any", c.qi_cost))
    cards_preview = [card_to_dict(c) for c in cards[:5]]

    # 境界梯度(模型 + 等级范围,去重模型)
    seen_models = []
    tier_summary = []
    for t in sect.tiers:
        if t.model not in [tm["model"] for tm in tier_summary]:
            covers = [tt.name for tt in sect.tiers if tt.model == t.model]
            tier_summary.append({
                "model": t.model,
                "covers": covers,
                "label": f"{covers[0]}—{covers[-1]}" if len(covers) > 1 else covers[0],
                "level_range": f"Lv.{t.level_min}-{[tt for tt in sect.tiers if tt.model == t.model][-1].level_max}",
            })

    return {
        "data": {
            "id": sect.id,
            "name": sect.name,
            "provider_display": sect.provider_display,
            "description": sect.description,
            "tagline": sect.tagline,
            "available": sect.available,
            "cost_tier": sect.cost_tier,
            "initial_difficulty": sect.initial_difficulty,
            "endgame_difficulty": sect.endgame_difficulty,
            "buffs": sect.buffs,
            "narration_style": sect.narration_style or "",
            "color_primary": sect.color_primary,
            "color_accent": sect.color_accent,

            # ★ 新增:立绘 URL(前端拼)
            "portrait_url": f"/images/sect-portraits/{sect.id}.png",

            # ★ 新增:招式预览
            "cards_preview": cards_preview,

            # ★ 新增:宗派背景故事
            "background_story": SECT_BACKGROUND_STORIES.get(sect.id, ""),

            # ★ 新增:模型梯度摘要
            "tier_summary": tier_summary,

            # 初始数值
            "initial_stats": {
                "hp": sect.initial_stats.get("hp"),
                "atk": sect.initial_stats.get("atk"),
                "def": sect.initial_stats.get("def_"),
                "spd": sect.initial_stats.get("spd"),
                "crit_rate": sect.initial_stats.get("crit_rate"),
                "qi": sect.initial_stats.get("qi"),
            },
        }
    }


@app.post("/api/byok/probe")
async def byok_probe(req: ProbeRequest):
    """探测 key 可用模型,返回各派可选性。

    与 verify-key 区别:probe 只调 /v1/models 列表,不实际发推理请求(快、便宜);
    verify-key 是逐个模型真打 chat/completions(慢、贵,但更严谨)。
    """
    if not req.api_key.strip():
        raise HTTPException(400, "API Key 不能为空")
    if not req.base_url.strip():
        raise HTTPException(400, "API 地址不能为空")

    result = await probe_byok(req.base_url.strip(), req.api_key.strip())
    # 即便 ok=False 也 200 返回,让前端正常渲染失败态(不抛 HTTPException)
    return {"data": result}


@app.post("/api/sect/verify-key")
async def verify_sect_key(req: VerifyKeyRequest):
    """SSE 流式验证 BYOK key 能否调用该派所有模型。

    前端用 fetch + ReadableStream 或 EventSource 读取。
    """
    sect = get_sect(req.sect_id)
    if not sect:
        raise HTTPException(404, "门派不存在")
    if not sect.available:
        raise HTTPException(400, f"门派 {sect.name} 暂未开放")
    if not req.api_key.strip():
        raise HTTPException(400, "API Key 不能为空")

    async def event_stream():
        try:
            async for event in stream_verify_sect_models(
                sect_id=req.sect_id,
                base_url=req.base_url,
                api_key=req.api_key,
            ):
                yield f"data: {json.dumps(event, ensure_ascii=False)}\n\n"
        except Exception as e:
            yield f"data: {json.dumps({'event':'error','message':str(e)})}\n\n"

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
            "Connection": "keep-alive",
        },
    )


@app.post("/api/sect/verify-current")
async def verify_current_sect_key(current_user: dict = Depends(get_current_user)):
    """★ 用当前角色已存的 base_url + api_key 验证(无需重新输入)"""
    user_id = current_user["id"]
    char = get_character(user_id)
    if not char:
        raise HTTPException(404, "未创建角色,无现有灵脉可用")
    base_url = char.get("base_url", "")
    api_key = char.get("api_key", "")
    sect_id = char.get("sect", "")
    if not (base_url and api_key and sect_id):
        raise HTTPException(400, "当前角色灵脉信息不完整")

    async def event_stream():
        try:
            async for event in stream_verify_sect_models(
                sect_id=sect_id,
                base_url=base_url,
                api_key=api_key,
            ):
                yield f"data: {json.dumps(event, ensure_ascii=False)}\n\n"
        except Exception as e:
            yield f"data: {json.dumps({'event':'error','message':str(e)})}\n\n"

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
            "Connection": "keep-alive",
        },
    )


# ============================================================
# 角色 API
# ============================================================
@app.post("/api/character/choose-sect")
async def choose_sect(req: ChooseSectRequest, current_user: dict = Depends(get_current_user)):
    """创建角色 - 需要先通过 verify-key,这里只做最终存档。"""
    sect = get_sect(req.sect_id)
    if not sect:
        raise HTTPException(404, "门派不存在")
    if not sect.available:
        raise HTTPException(400, f"【{sect.name}】尚未开放。当前可选:沧澜剑派、天机阁")
    if not req.api_key.strip():
        raise HTTPException(400, "请先填写 API Key(并通过灵脉验证)")

    # ★ Phase C: 从 token 拿真实 user_id (替代硬编码)
    user_id = current_user["id"]

    # ★ 用新的 8 属性系统构建角色
    character = build_initial_character(
        user_id=user_id, sect_id=sect.id,
        name=req.character_name,
        base_url=req.base_url, api_key=req.api_key,
    )
    save_character(user_id, character)

    # 返回时隐藏 api_key
    safe = {k: v for k, v in character.items() if k != "api_key"}
    safe["api_key_masked"] = "****" + req.api_key.strip()[-4:]
    return {"data": safe}


@app.get("/api/character/me")
async def get_me(current_user: dict = Depends(get_current_user)):
    user_id = current_user["id"]
    char = get_character(user_id)
    if not char:
        raise HTTPException(404, "未创建角色")
    # 兼容老存档:若没有 attrs 字段,补一份默认值(防 404 之后立即接旧用户)
    if "attrs" not in char and char.get("sect"):
        char["attrs"] = get_initial_attrs(char["sect"])
        refresh_derived(char)
        char.setdefault("fatigue", 0)
        char.setdefault("factions", {})
        char.setdefault("battle_history", [])
        char.setdefault("fortune_log", [])
        save_character(user_id, char)
    # 独立战斗模型已废弃:战斗/本命书统一使用门派 + 等级阶段模型。
    char.pop("battle_model", None)
    char.pop("battle_api_key", None)
    char.pop("battle_base_url", None)
    ensure_cultivation_fields(char)
    save_character(user_id, char)
    # 不返回 api_key 给前端
    safe = {k: v for k, v in char.items() if k != "api_key"}
    # 附�� attributes 元数据(让��端不用 hardcode)
    safe["_attributes_meta"] = ATTRIBUTES
    if char.get("api_key"):
        safe["api_key_masked"] = "****" + char["api_key"][-4:]
    return {"data": safe}


@app.delete("/api/character/me")
async def reset_character(current_user: dict = Depends(get_current_user)):
    user_id = current_user["id"]
    """重置角色(测试用)"""
    delete_character(user_id)
    return {"status": "deleted"}


# ============================================================
# 玩家专属五宗世界云同步
# ============================================================
@app.get("/api/world/save")
async def get_world_cloud_save(current_user: dict = Depends(get_current_user)):
    saved = get_world_save(current_user["id"])
    return {"data": saved}


@app.post("/api/world/sync")
async def sync_world_cloud_save(req: WorldSyncRequest, current_user: dict = Depends(get_current_user)):
    # 服务端只做轻量云备份,不参与 500 事件结算。
    # 下一轮只允许同步状态恢复,绝不接受前端修为/等级写入。
    before_saved = get_world_save(current_user["id"])
    before_world = (before_saved or {}).get("data") or {}
    saved_character_status = None
    saved_character = None
    if isinstance(req.character_patch, dict) and req.character_patch:
        char = get_character(current_user["id"])
        if char:
            patch = req.character_patch
            recovery = None
            if patch.get("next_round_recovery"):
                recovery = next_round_recovery(char)
            elif "hp" in patch:
                char["hp"] = max(1, min(int(char.get("max_hp", 100)), int(patch.get("hp") or 1)))
            if not recovery and "qi" in patch:
                char["qi"] = max(0, min(int(char.get("max_qi", 600)), int(patch.get("qi") or 0)))
            if not recovery and "fatigue" in patch:
                char["fatigue"] = max(0, min(int(char.get("max_fatigue", 80)), int(patch.get("fatigue") or 0)))
            save_character(current_user["id"], char)
            saved_character_status = {
                "hp": char.get("hp"),
                "qi": char.get("qi"),
                "fatigue": char.get("fatigue"),
                "recovery": recovery,
            }
            saved_character = char

    world = req.world or {}
    compact = {
        "id": str(world.get("id") or ""),
        "version": int(world.get("version") or 1),
        "round": int(world.get("round") or req.revision or 0),
        "day": int(world.get("day") or 1),
        "seed": int(world.get("seed") or 0),
        "player": world.get("player") or {},
        "familiar_ids": list(world.get("familiar_ids") or [])[:12],
        "last_summary": world.get("last_summary") or {},
        "event_log": list(world.get("event_log") or [])[:80],
        "pending_sync": [],
    }
    saved = save_world_save(current_user["id"], req.revision, compact)
    try:
        add_world_round_log(
            user_id=current_user["id"],
            client_round_id=req.client_round_id,
            from_revision=int((before_saved or {}).get("revision") or before_world.get("round") or 0),
            to_revision=int(saved.get("revision") or compact.get("round") or 0),
            from_day=int(before_world.get("day") or 0),
            to_day=int(compact.get("day") or 0),
            character_patch=saved_character_status or req.character_patch or {},
            summary=compact.get("last_summary") or {},
            event_count=len(compact.get("event_log") or []),
            payload_size=len(json.dumps(compact, ensure_ascii=False)),
            status="saved",
        )
    except Exception as exc:
        print(f"[world sync] failed to log round: {exc}")
    if saved_character is None:
        saved_character = get_character(current_user["id"])
    if saved_character_status:
        saved["character_status"] = saved_character_status
    saved["world"] = saved.get("data") or compact
    saved["character"] = saved_character
    saved["server_revision"] = saved.get("revision")
    return {"data": saved}


# ============================================================
# ★ 墨炉 / 本命书 API
# ============================================================
class CreateCultivationTaskRequest(BaseModel):
    task_type: str
    theme: str = ""
    expected_tokens: int = 0


class BudgetRequest(BaseModel):
    budget_chapter: Optional[int] = None
    budget_daily: Optional[int] = None
    budget_monthly: Optional[int] = None
    budget_confirm_required: Optional[bool] = None


@app.get("/api/cultivation/queue")
async def get_cultivation_queue(current_user: dict = Depends(get_current_user)):
    user_id = current_user["id"]
    schedule_user_queue(user_id)
    return {"data": queue_overview(user_id)}


@app.post("/api/cultivation/tasks")
async def create_cultivation_task_api(req: CreateCultivationTaskRequest, current_user: dict = Depends(get_current_user)):
    user_id = current_user["id"]
    char = get_character(user_id)
    if not char:
        raise HTTPException(404, "未创建角色")
    ensure_cultivation_fields(char)
    save_character(user_id, char)

    allowed = {"meditate_inner", "retreat_long"}
    if req.task_type not in allowed:
        raise HTTPException(400, "此任务类型不能由前端直接创建")

    fatigue_delta = add_fatigue(char, req.task_type)
    save_character(user_id, char)

    title = "闭关章 · 墨炉长明" if req.task_type == "retreat_long" else "内景章 · 灵台生墨"
    task = enqueue_task(
        user_id=user_id,
        task_type=req.task_type,
        title=title,
        prompt_payload={
            "theme": req.theme or ("墨炉长明,灵台观照" if req.task_type == "retreat_long" else "灵台生墨,入定成章"),
            "expected_tokens": req.expected_tokens,
        },
        source_type="meditation",
        source_id=req.task_type,
        priority=4 if req.task_type == "retreat_long" else 2,
        model="",
    )
    return {"data": {"task": task, "fatigue": fatigue_delta}}


@app.get("/api/cultivation/tasks/{task_id}")
async def get_cultivation_task_api(task_id: str, current_user: dict = Depends(get_current_user)):
    task = get_cultivation_task(task_id)
    if not task or task["user_id"] != current_user["id"]:
        raise HTTPException(404, "燃灵任务不存在")
    return {"data": {"task": task}}


@app.post("/api/cultivation/tasks/{task_id}/pause")
async def pause_cultivation_task_api(task_id: str, current_user: dict = Depends(get_current_user)):
    try:
        return {"data": {"task": pause_task(task_id, current_user["id"])}}
    except ValueError as e:
        raise HTTPException(404, str(e))


@app.post("/api/cultivation/tasks/{task_id}/resume")
async def resume_cultivation_task_api(task_id: str, current_user: dict = Depends(get_current_user)):
    try:
        return {"data": {"task": resume_task(task_id, current_user["id"])}}
    except ValueError as e:
        raise HTTPException(404, str(e))


@app.post("/api/cultivation/tasks/{task_id}/cancel")
async def cancel_cultivation_task_api(task_id: str, current_user: dict = Depends(get_current_user)):
    try:
        return {"data": {"task": cancel_running_task(task_id, current_user["id"])}}
    except ValueError as e:
        raise HTTPException(404, str(e))


@app.get("/api/cultivation/budget")
async def get_cultivation_budget(current_user: dict = Depends(get_current_user)):
    user_id = current_user["id"]
    char = get_character(user_id)
    if not char:
        raise HTTPException(404, "未创建角色")
    ensure_cultivation_fields(char)
    save_character(user_id, char)
    return {"data": {
        "budget_chapter": 0,
        "budget_daily": 0,
        "budget_monthly": 0,
        "budget_confirm_required": False,
        "daily_token_used": char["daily_token_used"],
        "monthly_token_used": char["monthly_token_used"],
    }}


@app.put("/api/cultivation/budget")
async def update_cultivation_budget(req: BudgetRequest, current_user: dict = Depends(get_current_user)):
    user_id = current_user["id"]
    char = get_character(user_id)
    if not char:
        raise HTTPException(404, "未创建角色")
    ensure_cultivation_fields(char)
    char["budget_chapter"] = 0
    char["budget_daily"] = 0
    char["budget_monthly"] = 0
    char["budget_confirm_required"] = False
    save_character(user_id, char)
    return {"data": {
        "budget_chapter": 0,
        "budget_daily": 0,
        "budget_monthly": 0,
        "budget_confirm_required": False,
    }}


@app.get("/api/novel/stats")
async def novel_stats(current_user: dict = Depends(get_current_user)):
    user_id = current_user["id"]
    char = get_character(user_id)
    if not char:
        raise HTTPException(404, "未创建角色")
    ensure_cultivation_fields(char)
    save_character(user_id, char)
    stats = get_novel_stats(user_id)
    stats.update({
        "cultivation_total": char.get("cultivation_total", 0),
        "token_total": char.get("token_total", 0),
        "novel_words_total": char.get("novel_words_total", 0),
        "chapters_count_character": char.get("chapters_count", 0),
    })
    return {"data": stats}


@app.get("/api/novel/chapters")
async def novel_chapters(limit: int = 30, offset: int = 0, current_user: dict = Depends(get_current_user)):
    user_id = current_user["id"]
    return {"data": {"chapters": list_novel_chapters(user_id, limit, offset)}}


@app.get("/api/novel/volumes")
async def novel_volumes(current_user: dict = Depends(get_current_user)):
    return {"data": {"volumes": list_novel_volumes(current_user["id"])}}


@app.get("/api/novel/chapters/{chapter_id}")
async def novel_chapter_detail(chapter_id: int, current_user: dict = Depends(get_current_user)):
    chapter = get_novel_chapter(current_user["id"], chapter_id)
    if not chapter:
        raise HTTPException(404, "章节不存在")
    return {"data": {"chapter": chapter}}


# ============================================================
# ★ 打坐 — 无冷却 · 连击加成 · 恢复气血灵气但增加疲劳
# ============================================================
@app.post("/api/character/meditate")
async def meditate(current_user: dict = Depends(get_current_user)):
    user_id = current_user["id"]
    char = get_character(user_id)
    if not char:
        raise HTTPException(404, "未创建角色")

    now = _time.time()
    last = char.get("last_meditation_at", 0)
    streak = char.get("meditate_streak", 0)
    total_count = char.get("meditate_total", 0)

    # ★ 连击判定:3s 内连续点击 → streak+1,否则重置
    STREAK_WINDOW = 3.0
    if last > 0 and (now - last) <= STREAK_WINDOW:
        streak += 1
    else:
        streak = 1

    # ★ 连击倍率:streak 1=1x, 5=1.5x, 10=2x, 20=3x, 50=5x
    if streak >= 50:
        mult = 5.0
    elif streak >= 20:
        mult = 3.0 + (streak - 20) / 15  # 20→3x, 50→5x
    elif streak >= 10:
        mult = 2.0 + (streak - 10) / 10  # 10→2x, 20→3x
    elif streak >= 5:
        mult = 1.5 + (streak - 5) / 10   # 5→1.5x, 10→2x
    else:
        mult = 1.0 + (streak - 1) * 0.125  # 1→1x, 5→1.5x

    mult = round(mult, 2)

    # ★ 基础恢复:1% max_hp / max_qi;疲劳只增不减,下一轮统一清零。
    max_hp = char.get("max_hp", 100)
    max_qi = char.get("max_qi", 600)
    base_heal = max(1, int(max_hp * 0.01))
    base_qi_gain = max(1, int(max_qi * 0.01))

    # 应用倍率
    heal = int(base_heal * mult)
    qi_gain = int(base_qi_gain * mult)

    # 更新角色
    old_hp = char.get("hp", 0)
    old_qi = char.get("qi", 0)
    char["hp"] = min(max_hp, old_hp + heal)
    char["qi"] = min(max_qi, old_qi + qi_gain)
    fatigue_delta = add_fatigue(char, "meditate")

    char["last_meditation_at"] = now
    char["meditate_streak"] = streak
    char["meditate_total"] = total_count + 1

    # ★ 里程碑检测
    milestone = None
    MILESTONES = [5, 10, 20, 50, 100, 200, 500, 1000]
    if streak in MILESTONES:
        milestone = streak
        # 写修行录:打坐里程碑
        _journal_safe(user_id, "meditate",
                      f"打坐入定 · {milestone} 连",
                      f"连击 {milestone} 次,气血调息 {mult}x",
                      {"tags": [f"{milestone}连", "打坐"]})

    save_character(user_id, char)

    # ★ 今日修行令:打坐(只记第一次)
    today = get_today()
    record_daily_task(user_id, today, "meditate")
    return {"data": {
        "heal": heal,
        "qi_gain": qi_gain,
        "fatigue_relief": 0,
        "fatigue_gain": fatigue_delta["gain"],
        "fatigue_full": fatigue_delta["is_full"],
        "exp_gain": 0,
        "streak": streak,
        "mult": mult,
        "milestone": milestone,
        "hp": char["hp"],
        "max_hp": char["max_hp"],  # 升级后会变大
        "qi": char["qi"],
        "max_qi": char["max_qi"],
        "fatigue": char["fatigue"],
        "exp": char["exp"],
        "level": char["level"],
        "realm_name": char.get("realm_name", ""),
        "realm": char.get("realm", "qi"),
        "level_up": None,
        "total_count": char["meditate_total"],
        "can_enter_trance": True,
        "message": "调息完成,灵台已静,可入定成章。疲劳会在下一轮清零。",
    }}


def _journal_safe(uid, etype, title, detail="", meta=None):
    """写修行录的兜底 wrapper(失败不抛错,免得影响主流程)"""
    try:
        from .store import add_journal_entry
        add_journal_entry(uid, etype, title, detail, meta or {})
    except Exception as _e:
        print(f"[journal] {etype} err: {_e}")


# ============================================================
# ★ 战斗中赠礼 — 加权判断接受概率
# ============================================================
class GiveGiftRequest(BaseModel):
    battle_id: str
    item_id: str
    gift_count_so_far: int = 0  # 本场已送几次


@app.post("/api/battle/give-gift")
async def give_gift(req: GiveGiftRequest, current_user: dict = Depends(get_current_user)):
    user_id = current_user["id"]
    """赠礼给战斗中的怪物。
    - 接受率 = 友好度系数 + 物品稀有度 + 缘分(INS) - 已送次数衰减
    - 接受 → 怪物消失 + 章节入墨炉 + 友好度+5
    - 拒绝 → 友好度-1,继续战斗

    ★ Phase 3: 服务端管理 gift_count(不再信任前端的 gift_count_so_far)
    """
    char = get_character(user_id)
    if not char:
        raise HTTPException(404, "未创建角色")

    engine = get_battle(req.battle_id)
    if not engine:
        raise HTTPException(404, "战斗不存在")

    # ★ Phase 3: 服务端检查赠礼次数 + 战斗是否结束
    allowed, reason = engine.can_gift()
    if not allowed:
        raise HTTPException(400, reason)

    item = _ITEMS_MAP.get(req.item_id)
    if not item:
        raise HTTPException(404, "物品不存在")

    # 检查背包 — 用 list 形式
    inv = get_inventory(user_id)
    cur_count = next((it["count"] for it in inv if it["id"] == req.item_id), 0) if isinstance(inv, list) else inv.get(req.item_id, 0)
    if cur_count < 1:
        raise HTTPException(400, "物品不足")

    # 找怪物对应的派(用 enemy.clan 反查)
    enemy_id = engine.state.get("enemy_id")
    enemy = _ENEMIES_MAP.get(enemy_id)
    enemy_clan = engine.state.get("enemy_clan", "")
    # 怪物族群不直接 = 修真门派,先用一个简单映射
    factions = char.get("factions", {})
    avg_faction = sum(factions.values()) / max(1, len(factions))

    # ★ Phase 3: 用服务端 gift_count 计算 penalty
    server_gift_count = engine.gift_count
    rarity_bonus = (item.rarity - 1) * 0.12
    faction_bonus = avg_faction / 200
    ins_bonus = char.get("attrs", {}).get("ins", 5) * 0.02
    penalty = server_gift_count * 0.18
    accept_prob = 0.40 + rarity_bonus + faction_bonus + ins_bonus - penalty
    accept_prob = max(0.05, min(0.95, accept_prob))

    accepted = _random.random() < accept_prob

    # 记一次赠礼尝试(扣物品 + 次数++)
    engine.record_gift_attempt()
    remove_item(user_id, req.item_id, 1)

    if accepted:
        # 怪物消失 — 友好度 +5,章节入墨炉;不再直接给修为
        legacy_exp_reward = int(engine.state.get("enemy_rewards_exp", 0) * 0.5)
        exp_reward = 0

        # 怪物族群→门派映射(友好度,只这里改 char)
        CLAN_TO_SECT = {
            "灵狐": "canglan", "蛟龙": "canglan", "鬼修": "canglan",
            "蛮兽": "tianji", "机关": "tianji", "傀儡": "tianji",
            "妖植": "xuanji", "虫族": "xuanji",
            "石魔": "qingming", "海妖": "qingming",
            "飞禽": "yueyin", "幽灵": "yueyin",
        }
        target_sect = CLAN_TO_SECT.get(enemy_clan, char.get("sect", "canglan"))
        factions[target_sect] = min(100, factions.get(target_sect, 0) + 5)
        char["factions"] = factions
        # 注:此时只改 factions,不save_character。战斗历史与入炉任务由 engine.end_with_gift commit。
        # 但 factions 必须在 commit 前写回:
        save_character(user_id, char)

        # ★ 记录今日修行令: 赠礼
        record_daily_task(user_id, get_today(), "gift")
        if enemy_id:
            record_gift(user_id, enemy_id)

        # ★ Phase 3: 统一走 engine.end_with_gift(走 commit + 推 result=victory + finish_reason=gift)
        await engine.end_with_gift(exp_reward)
        # 额外推一个 gift_message 让 UI 显示
        await engine._push({"type": "gift_result", "data": {
            "accepted": True,
            "gift_message": f"{enemy.name if enemy else '妖兽'}满意地收下了 {item.name},悄然离去。",
        }})
        return {"data": {
            "accepted": True,
            "exp_reward": exp_reward,
            "legacy_exp_reward": legacy_exp_reward,
            "accept_prob": round(accept_prob, 2),
            "gift_count": engine.gift_count,
        }}
    else:
        # 拒绝:怪物对应派友好度 -1
        CLAN_TO_SECT = {
            "灵狐": "canglan", "蛟龙": "canglan", "鬼修": "canglan",
            "蛮兽": "tianji", "机关": "tianji", "傀儡": "tianji",
            "妖植": "xuanji", "虫族": "xuanji",
            "石魔": "qingming", "海妖": "qingming",
            "飞禽": "yueyin", "幽灵": "yueyin",
        }
        target_sect = CLAN_TO_SECT.get(enemy_clan, char.get("sect", "canglan"))
        factions[target_sect] = max(-100, factions.get(target_sect, 0) - 1)
        char["factions"] = factions
        fatigue_delta = add_fatigue(char, "battle_pacified", amount=1)
        save_character(user_id, char)
        return {"data": {
            "accepted": False,
            "message": f"{enemy.name if enemy else '妖兽'}嗤之以鼻,将 {item.name} 拍落在地。",
            "accept_prob": round(accept_prob, 2),
            "fatigue": fatigue_delta,
        }}


# ============================================================
# ★ 奇遇 — LLM 即时生成 + 应用效果
# ============================================================
class FortuneTriggerRequest(BaseModel):
    visible_enemies: list = []   # 当前地图上的怪物 [{id, name, clan, level}]


@app.post("/api/fortune/trigger")
async def trigger_fortune(req: FortuneTriggerRequest, current_user: dict = Depends(get_current_user)):
    user_id = current_user["id"]
    """触发奇遇 — 用 LLM 根据当前场景生成,效果立即应用"""
    char = get_character(user_id)
    if not char:
        raise HTTPException(404, "未创建角色")

    # 频率限制 — 至少 60s 一次
    last = char.get("last_fortune_at", 0)
    now = _time.time()
    if now - last < 55:
        return {"data": {"skipped": True, "reason": "cooldown", "remain": int(55 - (now - last))}}

    # ★ v2:用 events.py 事件引擎(12 类分类 + 加权选择 + 类型化 prompt)
    import json
    from .events import pick_and_build, EVENT_TYPES
    enemy_ids = list(_ENEMIES_MAP.keys())
    item_ids = list(_ITEMS_MAP.keys())
    visible = req.visible_enemies[:8]
    recent_battles = char.get("battle_history", [])[-3:]

    event_type, type_meta, prompt = pick_and_build(
        visible_enemies=visible,
        character=char,
        recent_battles=recent_battles,
        enemy_ids=enemy_ids,
        item_ids=item_ids,
    )
    print(f"[Fortune] 触发类型: {event_type} ({type_meta['label']})")

    # 调 Haiku 快速生成
    try:
        from .llm_client import stream_battle_narration
        chunks = []
        usage_holder = {"usage": None, "fallback": False}

        async def _on_usage(usage: dict):
            usage_holder["usage"] = usage

        async def _on_fallback():
            usage_holder["fallback"] = True

        async for c in stream_battle_narration(
            sect_narration_style="精炼仙侠,严格输出 JSON",
            model="claude-haiku-4-5-20251001",
            max_tokens=400,
            user_prompt=prompt,
            api_key=char.get("api_key"),
            base_url=char.get("base_url"),
            on_usage=_on_usage,
            on_fallback=_on_fallback,
            suppress_fallback=True,
        ):
            chunks.append(c)
        raw = "".join(chunks).strip()
        if not raw or usage_holder["fallback"]:
            raise ValueError("灵脉未能生成奇遇")
        if usage_holder["usage"] and usage_holder["usage"].get("total_tokens"):
            apply_cultivation_gain(
                user_id,
                int(usage_holder["usage"].get("total_tokens") or 0),
                "",
                "fortune_json",
                model="claude-haiku-4-5-20251001",
                input_tokens=int(usage_holder["usage"].get("input_tokens") or 0),
                output_tokens=int(usage_holder["usage"].get("output_tokens") or 0),
                reasoning_tokens=int(usage_holder["usage"].get("reasoning_tokens") or 0),
                usage_source="provider",
            )
        else:
            apply_cultivation_gain(
                user_id,
                estimate_tokens(prompt) + estimate_tokens(raw),
                "",
                "fortune_json",
                model="claude-haiku-4-5-20251001",
                usage_source="estimated",
            )
        # 抠出 JSON(防 LLM 多说几句)
        if "```" in raw:
            raw = raw.split("```")[1]
            if raw.startswith("json"): raw = raw[4:]
        # 找第一个 { 到最后一个 }
        s = raw.find("{"); e = raw.rfind("}")
        if s == -1 or e == -1:
            raise ValueError("LLM 未返回 JSON: " + raw[:100])
        fortune = json.loads(raw[s:e+1])
    except Exception as e:
        return {"data": {"error": f"奇遇生成失败: {e}", "skipped": True}}

    # ★ 应用效果(安全 clamp)
    eff = fortune.get("effects", {})
    applied = {}

    hp_d = max(-30, min(50, int(eff.get("hp_delta") or 0)))
    char["hp"] = max(1, min(char.get("max_hp", 100), char.get("hp", 0) + hp_d))
    applied["hp_delta"] = hp_d

    qi_d = max(-200, min(200, int(eff.get("qi_delta") or 0)))
    char["qi"] = max(0, min(char.get("max_qi", 600), char.get("qi", 0) + qi_d))
    applied["qi_delta"] = qi_d

    # 奇遇不再直接给修为;原 LLM 的 exp_delta 只作为外传章命题强度参考。
    exp_d = max(-10, min(50, int(eff.get("exp_delta") or 0)))
    applied["exp_delta"] = 0
    if exp_d:
        applied["inspiration_delta"] = exp_d

    event_fatigue = max(0, min(15, int(eff.get("fatigue_delta") or 0)))
    fatigue_delta = add_fatigue(char, "fortune", amount=3 + event_fatigue)
    applied["fatigue_delta"] = fatigue_delta["gain"]
    applied["fatigue_full"] = fatigue_delta["is_full"]

    fac_d = eff.get("faction_delta") or {}
    factions = char.get("factions", {})
    fd_applied = {}
    if isinstance(fac_d, dict):
        for k, v in fac_d.items():
            if k in factions:
                d = max(-10, min(10, int(v)))
                factions[k] = max(-100, min(100, factions[k] + d))
                fd_applied[k] = d
    char["factions"] = factions
    applied["faction_delta"] = fd_applied

    # 掉落 — 返回中文名 + icon,避免前端显示英文 id
    drop_id = eff.get("drop_item_id")
    if drop_id and drop_id in _ITEMS_MAP:
        add_item(user_id, drop_id, 1)
        _it = _ITEMS_MAP[drop_id]
        applied["drop"] = drop_id  # 保留兼容
        applied["drop_name"] = getattr(_it, "name", drop_id)
        applied["drop_icon"] = getattr(_it, "icon", "🎁")
        applied["drop_icon_url"] = item_icon_url(drop_id)
        applied["drop_rarity"] = getattr(_it, "rarity", 1)

    # 触发战斗(若 force_battle)
    spawn_id = eff.get("spawn_enemy_id")
    force = bool(eff.get("force_battle"))
    battle_url = None
    if force and spawn_id and spawn_id in _ENEMIES_MAP:
        try:
            engine = BattleEngine(character=char, enemy_id=spawn_id, user_id=user_id)
            save_battle(engine.battle_id, engine)
            battle_url = f"/battle/{engine.battle_id}"
            applied["forced_battle"] = battle_url
        except Exception:
            pass

    # 写历史(含 type)
    log = char.get("fortune_log", [])
    log.append({
        "ts": int(now),
        "type": event_type,
        "type_label": type_meta["label"],
        "type_icon": type_meta["icon"],
        "name": fortune.get("name", "奇遇"),
        "narrative": fortune.get("narrative", ""),
        "applied": applied,
    })
    char["fortune_log"] = log[-20:]
    char["last_fortune_at"] = now

    cultivation_task = None
    try:
        cultivation_task = enqueue_task(
            user_id=user_id,
            task_type="fortune",
            title=f"外传章 · {fortune.get('name', '奇遇')}",
            prompt_payload={
                "name": fortune.get("name", "奇遇"),
                "narrative": fortune.get("narrative", ""),
                "applied": applied,
                "type": event_type,
                "type_label": type_meta["label"],
            },
            source_type="fortune",
            source_id=event_type,
            priority=1,
            model="",
        )
        applied["cultivation_task_id"] = cultivation_task.get("id")
    except Exception as exc:
        print(f"[cultivation] enqueue fortune failed: {exc}")

    save_character(user_id, char)

    # ★ 记录今日修行令: 奇遇
    record_daily_task(user_id, get_today(), "fortune")

    # ★ 写修行录:奇遇
    _detail_parts = []
    if applied.get("hp_delta"): _detail_parts.append(f"HP{'+' if applied['hp_delta']>0 else ''}{applied['hp_delta']}")
    if applied.get("qi_delta"): _detail_parts.append(f"灵气{'+' if applied['qi_delta']>0 else ''}{applied['qi_delta']}")
    if applied.get("drop_name"): _detail_parts.append(f"获得 {applied['drop_name']}")
    if applied.get("cultivation_task_id"): _detail_parts.append("外传章已入墨炉")
    _journal_safe(user_id, "fortune",
                  f"{event.get('type_label','奇遇')} · {event.get('name','奇遇')}",
                  " · ".join(_detail_parts) or "奇遇降临",
                  {"tags": [event.get("type_label", "奇遇")], "event_type": event.get("type"),
                   "cultivation_task_id": applied.get("cultivation_task_id")})

    return {"data": {
        "fortune": {**fortune, "type": event_type, "type_label": type_meta["label"], "type_icon": type_meta["icon"]},
        "applied": applied,
        "cultivation_task": cultivation_task,
        "battle_url": battle_url,
        "character": {k: v for k, v in char.items() if k != "api_key"},
    }}


# ============================================================
# ★ 怪物章节按需 LLM 生成 + 缓存
# ============================================================
_CHAPTER_CACHE: dict = {}  # { "enemy_id:章名": "章节文本" }


@app.get("/api/enemy/{enemy_id}/chapters")
async def get_enemy_chapters(enemy_id: str):
    """返回该怪物已生成的章节列表(标题+前 80 字预览)"""
    enemy = _ENEMIES_MAP.get(enemy_id)
    if not enemy:
        raise HTTPException(404, "怪物不存在")
    chapters = [
        {"key": k.split(":", 1)[1], "preview": v[:80] + ("..." if len(v) > 80 else "")}
        for k, v in _CHAPTER_CACHE.items() if k.startswith(f"{enemy_id}:")
    ]
    return {"data": {
        "enemy": {"id": enemy.id, "name": enemy.name, "clan": enemy.clan},
        "chapters": chapters,
        "chapter_templates": ["出生", "觉醒", "族群", "失踪", "复仇", "陨落", "再生", "羁绊", "宿敌", "传说"],
    }}


@app.post("/api/enemy/{enemy_id}/chapter")
async def generate_enemy_chapter(enemy_id: str, key: str = "出生", current_user: dict = Depends(get_current_user)):
    user_id = current_user["id"]
    """LLM 生成怪物指定章节(若已 cache 则直接返回)"""
    enemy = _ENEMIES_MAP.get(enemy_id)
    if not enemy:
        raise HTTPException(404, "怪物不存在")

    cache_key = f"{enemy_id}:{key}"
    if cache_key in _CHAPTER_CACHE:
        return {"data": {"key": key, "text": _CHAPTER_CACHE[cache_key], "cached": True}}

    char = get_character(user_id)
    if not char:
        raise HTTPException(404, "未创建角色")
    fatigue_delta = add_fatigue(char, "monster_chapter")
    save_character(user_id, char)
    api_key = char.get("api_key")
    base_url = char.get("base_url")

    chapter_hint = {
        "出生": "描写它的出生 / 起源 / 早年",
        "觉醒": "描写它觉醒灵智 / 首次施展能力的关键时刻",
        "族群": "描写它在族群中的地位 / 与同类的关系",
        "失踪": "描写一次重要的失踪 / 流亡 / 隐匿事件",
        "复仇": "描写它的仇恨与复仇之念",
        "陨落": "描写它(可能的)死亡 / 重伤 / 衰败",
        "再生": "描写它从一次重创中重新崛起",
        "羁绊": "描写它与某个修真者 / 同族的深厚羁绊",
        "宿敌": "描写它与某个具体宿敌的恩怨",
        "传说": "描写流传于江湖的它的传说,半真半假",
    }.get(key, "为它写一段独立的小故事")

    prompt = f"""为《灵枢笔录》游戏中的怪物【{enemy.name}】写一段 200-300 字的章节短篇:

【主题】{chapter_hint}
【背景】{enemy.name} 属 {enemy.clan} 族,Lv.{enemy.level}
【描述】{enemy.description}
【典故】{enemy.lore}

要求:
- 仙侠武侠笔法,有起承转合
- 字数控制 200-300 字
- 至少 3 处 ** 标记重点(关键词、地点、招式、人名)
- 风格阴森 / 悲壮 / 神秘 / 凄美,与怪物气质相符
- 直接输出正文,不要前缀
"""

    try:
        from .llm_client import stream_battle_narration
        chunks = []
        async for c in stream_battle_narration(
            sect_narration_style="独立短篇,文笔仙侠",
            model="claude-sonnet-4-6",
            max_tokens=500,
            user_prompt=prompt,
            api_key=api_key, base_url=base_url,
        ):
            chunks.append(c)
        text = "".join(chunks).strip()
    except Exception as e:
        raise HTTPException(500, f"章节生成失败: {e}")

    _CHAPTER_CACHE[cache_key] = text
    return {"data": {"key": key, "text": text, "cached": False, "enemy_name": enemy.name, "fatigue": fatigue_delta}}


@app.post("/api/character/me/byok")
async def update_my_byok(req: UpdateByokRequest, current_user: dict = Depends(get_current_user)):
    user_id = current_user["id"]
    """在游戏中随时更换 base_url + api_key。

    强制流程:
    1. 客户端 verified=True 表示已在前端跑过 verify-key 全过
    2. 后端再次 probe 防绕过(快验证,只调 /v1/models)
    3. 检查 character.sect 是否在新 key 的可用门派内
    4. 全部 OK → 保存,否则报错
    """
    if not req.verified:
        raise HTTPException(400, {
            "code": "NOT_VERIFIED",
            "message": "请先在前端完成模型验证再保存",
        })
    if not req.api_key.strip():
        raise HTTPException(400, "API Key 不能为空")
    if not req.base_url.strip():
        raise HTTPException(400, "API 地址不能为空")

    char = get_character(user_id)
    if not char:
        raise HTTPException(404, "未创建角色")

    # 二次校验:后端独立 probe 一次防客户端造假
    probe = await probe_byok(req.base_url.strip(), req.api_key.strip())
    if not probe["ok"]:
        raise HTTPException(400, {
            "code": "BYOK_PROBE_FAILED",
            "message": "服务端验证失败: " + (probe.get("error") or "未知错误"),
        })
    if char["sect"] not in probe["available_sect_ids"]:
        raise HTTPException(400, {
            "code": "SECT_NOT_AVAILABLE",
            "message": f"新 Key 无法支持当前门派【{char.get('sect_name','?')}】",
            "available_sects": probe["available_sect_ids"],
            "current_sect": char["sect"],
        })

    # 保存
    old_masked = "****" + char.get("api_key", "")[-4:] if char.get("api_key") else "(空)"
    char["base_url"] = req.base_url.strip().rstrip("/")
    char["api_key"] = req.api_key.strip()
    save_character(user_id, char)

    new_masked = "****" + req.api_key.strip()[-4:]
    return {"data": {
        "updated": True,
        "old_api_key_masked": old_masked,
        "new_api_key_masked": new_masked,
        "new_base_url": char["base_url"],
        "verified_models_for_sect": [
            t.model for t in [t for s_id, s in ALL_SECTS.items()
                              if s_id == char["sect"] for t in s.tiers]
        ][:5],  # 仅返回前 5 个,作为提示
    }}


# ============================================================
# 图片生成 API (gpt-image-2 via bobdong.cn 网关)
# ============================================================
@app.post("/api/image/generate")
async def api_image_generate(req: ImageGenRequest):
    """统一图片生成端点 — 后端转发到 /v1/images/generations,自动重试 3 次。

    Body:
      { prompt: "...", n: 1, size: "1536x1024", quality: "auto",
        save_to: "/abs/path", filename_prefix: "sect-bg" }

    Response:
      { data: [ { b64_json, url, revised_prompt, local_path? }, ... ], count: N }

    Errors:
      400 — 配置 / prompt 问题(不会重试)
      500 — 上游 5xx,重试 3 次仍失败
    """
    if not req.prompt.strip():
        raise HTTPException(400, "prompt 不能为空")

    try:
        results = await generate_image(
            prompt=req.prompt,
            n=req.n,
            size=req.size,
            quality=req.quality,
            output_format=req.output_format,
            save_to=req.save_to,
            filename_prefix=req.filename_prefix,
        )
        return {"data": results, "count": len(results)}
    except ImageGenError as e:
        # 配置 / 审查问题 → 400;上游错误 → 500
        status = 400 if e.http_status in (400, 401, 403, 422) else 500
        raise HTTPException(status, {
            "code": "IMAGE_GEN_FAILED",
            "message": str(e),
            "http_status": e.http_status,
        })


# ============================================================
# 战斗 API
# ============================================================
@app.get("/api/battle/enemies")
async def list_battle_enemies(current_user: dict = Depends(get_current_user)):
    user_id = current_user["id"]
    """根据当前角色等级返回可挑战的敌人"""
    char = get_character(user_id)
    level = char.get("level", 1) if char else 1
    enemies = list_enemies_for_level(level, span=15)
    return {"data": [enemy_to_dict(e, char) for e in enemies]}


# ============================================================
# 修行地图 / 探索 API
# ============================================================
@app.get("/api/explore/spawn")
async def spawn_explore_enemies(count: int = 8, current_user: dict = Depends(get_current_user)):
    """为修行地图生成怪物 + NPC 弟子分布。

    ★ v3 — 按友好度加权 (怪物数量 ±40%)
    ★ Round 2 — 每个 slot 10% 概率出 NPC(跨派弟子)
    """
    user_id = current_user["id"]
    char = get_character(user_id)
    level = char.get("level", 1) if char else 1

    factions = char.get("factions", {}) if char else {}
    avg_friend = sum(factions.values()) / max(1, len(factions)) if factions else 0
    threat = max(-50, min(50, -avg_friend)) / 50
    count_mult = 1.0 + threat * 0.4
    final_count = max(3, min(15, int(count * count_mult)))
    level_shift = int(threat * 3)

    # ★ Round 2: 分配 NPC 与怪物名额(每个 slot 10% NPC)
    from .npc import generate_npc, npc_to_spawn_dict, cache_npc
    player_sect = char.get("sect", "canglan") if char else "canglan"
    npc_count = sum(1 for _ in range(final_count) if _random.random() < 0.10)
    monster_count = final_count - npc_count

    def _weighted_monster_pick(base_level: int):
        pools = [
            ("safe", 0.45, -8, -3),
            ("peer", 0.35, -3, 2),
            ("elite", 0.15, 3, 6),
            ("danger", 0.05, 7, 10),
        ]
        roll = _random.random()
        acc = 0
        chosen = pools[-1]
        for pool in pools:
            acc += pool[1]
            if roll <= acc:
                chosen = pool
                break
        pool_id, _weight, lo, hi = chosen
        candidates = [
            e for e in ENEMIES.values()
            if base_level + lo <= e.level <= base_level + hi
            and not e.id.startswith(("wild_", "spirit_", "poison_", "lightning_", "heavenly_"))
        ]
        if not candidates:
            candidates = list_enemies_for_level(base_level, span=12) or list(ENEMIES.values())
            pool_id = "peer"
        return _random.choice(candidates), pool_id

    # 怪物部分
    spawns = []
    if monster_count > 0:
        seen_monsters = set()
        for _ in range(monster_count):
            e, pool_id = _weighted_monster_pick(level + level_shift)
            tries = 0
            while e.id in seen_monsters and tries < 5:
                e, pool_id = _weighted_monster_pick(level + level_shift)
                tries += 1
            seen_monsters.add(e.id)
            d = enemy_to_dict(e, char)
            d["spawn_x"] = _random.uniform(8, 92)
            d["spawn_y"] = _random.uniform(15, 85)
            d["move_speed"] = _random.uniform(0.2, 0.8)
            d["move_dir"] = _random.uniform(0, 360)
            d["is_npc"] = False
            d["danger_level"] = pool_id
            d["danger_label"] = {"safe": "安全", "peer": "同级", "elite": "精英", "danger": "危险"}[pool_id]
            d["is_dangerous"] = pool_id == "danger"
            spawns.append(d)

    # NPC 部分
    for _ in range(npc_count):
        npc = generate_npc(player_sect, level, factions)
        cache_npc(npc)
        d = npc_to_spawn_dict(npc)
        d["spawn_x"] = _random.uniform(8, 92)
        d["spawn_y"] = _random.uniform(15, 85)
        d["move_speed"] = _random.uniform(0.3, 0.9)  # NPC 略快
        d["move_dir"] = _random.uniform(0, 360)
        spawns.append(d)

    _random.shuffle(spawns)
    # ★ 项目标准:统一 {data: ...} 包装,前端 const {data} = await ... 解构能拿到
    return {"data": spawns}

# 实际上述 if False 是为了不破坏前端老格式;新版前端可改读 .data.spawns


@app.get("/api/enemies/count")
async def get_enemies_count():
    total, by_clan = count_enemies()
    return {"data": {"total": total, "by_clan": by_clan, "clans_total": len(by_clan)}}


# ============================================================
# Boss / 故事线 API
# ============================================================
@app.get("/api/boss/list")
async def list_bosses(current_user: dict = Depends(get_current_user)):
    char = get_character(current_user["id"])
    return {"data": [boss_to_dict(b, char) for b in BOSSES.values()]}


@app.get("/api/boss/{boss_id}")
async def get_boss_detail(boss_id: str, current_user: dict = Depends(get_current_user)):
    b = BOSSES.get(boss_id)
    if not b:
        raise HTTPException(404, "Boss 不存在")
    char = get_character(current_user["id"])
    return {"data": boss_to_dict(b, char)}


@app.post("/api/boss/{boss_id}/chapter")
async def create_boss_chapter(boss_id: str, current_user: dict = Depends(get_current_user)):
    user_id = current_user["id"]
    char = get_character(user_id)
    if not char:
        raise HTTPException(404, "未创建角色")
    b = BOSSES.get(boss_id)
    if not b:
        raise HTTPException(404, "Boss 不存在")
    fatigue_delta = add_fatigue(char, "boss_chapter")
    save_character(user_id, char)
    sect = BOSS_SECTS.get(getattr(b, "sect_id", "") or "")
    task = enqueue_task(
        user_id=user_id,
        task_type="boss_chapter",
        title=f"道君外传 · {b.name}",
        prompt_payload={
            "boss_name": b.name,
            "title": b.title,
            "sect_name": getattr(b, "sect_name", ""),
            "company": getattr(b, "company", ""),
            "lore": b.lore,
            "real_background": getattr(sect, "real_background", "") if sect else "",
        },
        source_type="boss",
        source_id=boss_id,
        priority=5,
        model="",
    )
    return {"data": {"task": task, "fatigue": fatigue_delta}}


@app.get("/api/boss-sects/list")
async def list_boss_sects():
    return {"data": [boss_sect_to_dict(s) for s in BOSS_SECTS.values()]}


@app.get("/api/storylines")
async def list_storylines():
    return {"data": STORYLINES}


# ============================================================
# 物品 API
# ============================================================
@app.get("/api/items/list")
async def list_items():
    return {"data": [item_to_dict(item) for item in ITEMS.values()]}


@app.get("/api/items/{item_id}")
async def get_item_detail(item_id: str):
    item = get_item(item_id)
    if not item:
        raise HTTPException(404, "物品不存在")
    return {"data": item_to_dict(item)}


@app.get("/api/inventory")
async def get_my_inventory(current_user: dict = Depends(get_current_user)):
    user_id = current_user["id"]
    """玩家背包"""
    char = get_character(user_id)
    if not char:
        raise HTTPException(404, "未创建角色")
    inv = get_inventory(user_id)
    detailed = []
    for item_id, count in inv.items():
        item = get_item(item_id)
        if item:
            d = item_to_dict(item)
            d["count"] = count
            detailed.append(d)
    return {"data": {
        "items": detailed,
        "total_kinds": len(detailed),
        "total_count": sum(inv.values()),
    }}


@app.post("/api/inventory/use/{item_id}")
async def use_item(item_id: str, current_user: dict = Depends(get_current_user)):
    user_id = current_user["id"]
    char = get_character(user_id)
    if not char:
        raise HTTPException(404, "未创建角色")
    inv = get_inventory(user_id)
    if inv.get(item_id, 0) < 1:
        raise HTTPException(400, "物品不足")

    item = get_item(item_id)
    if not item:
        raise HTTPException(404, "物品不存在")
    if item.type != "consumable":
        raise HTTPException(400, f"该物品({item.type})不能使用")

    # 应用效果
    msg = []
    eff = item.use_effect or {}
    if "qi" in eff:
        add = int(eff["qi"])
        char["qi"] = min(char.get("max_qi", 600), char.get("qi", 0) + add)
        msg.append(f"灵气 +{add}")
    if "qi_percent" in eff:
        add = max(int(eff.get("qi_min", 0) or 0), int(char.get("max_qi", 600) * float(eff["qi_percent"]) / 100))
        char["qi"] = min(char.get("max_qi", 600), char.get("qi", 0) + add)
        msg.append(f"灵气 +{add}")
    if "hp" in eff:
        add = int(eff["hp"])
        char["hp"] = min(char.get("max_hp", 100), char.get("hp", 0) + add)
        msg.append(f"HP +{add}")
    if "hp_percent" in eff:
        add = int(char["max_hp"] * eff["hp_percent"] / 100)
        char["hp"] = min(char["max_hp"], char["hp"] + add)
        msg.append(f"HP +{add}")
    if "breakthrough_bonus" in eff:
        char["breakthrough_bonus"] = char.get("breakthrough_bonus", 0) + eff["breakthrough_bonus"]
        msg.append(f"突破成功率 +{int(eff['breakthrough_bonus']*100)}%")
    if "unlock_card" in eff:
        msg.append(f"已学习招式: {eff['unlock_card']}")

    fatigue_delta = add_fatigue(char, "inventory_use")
    if fatigue_delta["gain"]:
        msg.append(f"疲劳 +{fatigue_delta['gain']}")

    remove_item(user_id, item_id, 1)
    save_character(user_id, char)
    return {"data": {"effect_summary": " · ".join(msg), "remaining": inv.get(item_id, 0),
                     "fatigue": fatigue_delta,
                     "character": {k: v for k, v in char.items() if k != "api_key"}}}


@app.post("/api/inventory/grant/{item_id}")
async def grant_item(item_id: str, count: int = 1, admin: dict = Depends(require_admin)):
    """管理员调试接口:给自己的测试账号发物品。普通用户不可调用。"""
    user_id = admin["id"]
    item = get_item(item_id)
    if not item:
        raise HTTPException(404, "物品不存在")
    count = int(count or 0)
    if count <= 0:
        raise HTTPException(400, "数量必须大于 0")
    before = int(get_inventory(user_id).get(item_id, 0) or 0)
    new_count = add_item(user_id, item_id, count)
    add_item_ledger(
        user_id=user_id,
        item_id=item_id,
        delta_count=count,
        before_count=before,
        after_count=new_count,
        source="admin_debug",
        reason="管理员调试接口发放",
        admin_user_id=admin["id"],
    )
    add_admin_audit_log(
        admin_user_id=admin["id"],
        action="inventory.grant.self",
        target_type="user",
        target_id=user_id,
        before={"item_id": item_id, "count": before},
        after={"item_id": item_id, "count": new_count, "delta": count},
        reason="管理员调试接口发放",
    )
    return {"data": {"item": item_to_dict(item), "count": new_count}}


@app.get("/api/battle/cards")
async def list_battle_cards(current_user: dict = Depends(get_current_user)):
    user_id = current_user["id"]
    """当前角色可用卡牌 — ★ Round 1: 用 equipped_skills 替代固定 sect cards"""
    char = get_character(user_id)
    if not char:
        raise HTTPException(404, "未创建角色")
    # 首次访问 → 同步学到的招式
    sync_learned_skills(char)
    save_character(user_id, char)

    learned_map = {ls["skill_id"]: ls["level"] for ls in char.get("learned_skills", [])}
    equipped = char.get("equipped_skills", [])
    cards_out = []
    for sid in equipped:
        tpl = get_skill(sid)
        if not tpl:
            continue
        lvl = learned_map.get(sid, 1)
        battle_cost = effective_battle_qi_cost(tpl, lvl, char.get("max_qi", 600))
        cards_out.append({
            "id": tpl.id,
            "name": tpl.name,
            "icon": tpl.icon,
            "type": tpl.type,
            "tier": tpl.tier,
            "qi_cost": battle_cost,
            "qi_cost_base": __import__("app.skill_templates", fromlist=["effective_qi_cost"]).effective_qi_cost(tpl, lvl),
            "qi_cost_mode": "percent_max_qi",
            "power": __import__("app.skill_templates", fromlist=["effective_power"]).effective_power(tpl, lvl),
            "hit_rate": tpl.hit_rate,
            "crit_bonus": __import__("app.skill_templates", fromlist=["effective_crit_bonus"]).effective_crit_bonus(tpl, lvl),
            "description": tpl.description,
            "level": lvl,
            "sect_requirement": tpl.sect,
        })
    return {"data": cards_out}


@app.post("/api/battle/start")
async def start_battle(req: StartBattleRequest, current_user: dict = Depends(get_current_user)):
    user_id = current_user["id"]
    char = get_character(user_id)
    if not char:
        raise HTTPException(404, "未创建角色")

    # ★ 新手第一战:固定弱怪 + 教学模式
    is_first_battle = len(char.get("battle_history", [])) == 0
    if is_first_battle and req.enemy_id != "tutorial_enemy":
        # 首战重定向到教学怪物(使用最弱的狐妖)
        tutorial_enemy_id = "fox_01"  # 山林小狐 Lv.3
        try:
            engine = BattleEngine(
                character=char,
                enemy_id=tutorial_enemy_id,
                mode="drama",
                tutorial=True,  # 标记教学战
                user_id=user_id,
            )
        except ValueError:
            # fallback to requested enemy
            engine = BattleEngine(character=char, enemy_id=req.enemy_id, mode=req.mode or "drama", user_id=user_id)
    else:
        try:
            engine = BattleEngine(character=char, enemy_id=req.enemy_id, mode=req.mode or "drama", user_id=user_id)
        except ValueError as e:
            raise HTTPException(400, str(e))

    save_battle(engine.battle_id, engine)

    return {
        "data": {
            "battle_id": engine.battle_id,
            "snapshot": engine.snapshot(),
            "ws_url": f"/ws/battle/{engine.battle_id}",
            "mode": engine.mode,
            "is_tutorial": is_first_battle,
        }
    }


@app.get("/api/battle/{battle_id}")
async def get_battle_status(battle_id: str):
    """检查战斗是否存在(给前端路由守卫用)"""
    engine = get_battle(battle_id)
    if not engine:
        raise HTTPException(404, {
            "code": "BATTLE_NOT_FOUND",
            "message": "战斗不存在或已结束",
            "battle_id": battle_id,
        })
    return {
        "data": {
            "battle_id": battle_id,
            "snapshot": engine.snapshot(),
            "is_finished": engine.is_finished(),
        }
    }


@app.get("/api/battle/{battle_id}/card-preview")
async def get_card_damage_preview(battle_id: str, current_user: dict = Depends(get_current_user)):
    user_id = current_user["id"]
    """返回当前战斗中每张卡的预估伤害/效果"""
    engine = get_battle(battle_id)
    if not engine:
        raise HTTPException(404, "战斗不存在")

    char = get_character(user_id)
    if not char:
        raise HTTPException(404, "未创建角色")

    # 卡牌预览走 BattleEngine.preview_card,和真实结算共用 combat_balance 公式。
    sync_learned_skills(char)
    save_character(user_id, char)
    equipped = char.get("equipped_skills") or [c.id for c in get_cards_for_sect(char["sect"])]
    previews = []
    for card_id in equipped:
        card = engine._get_player_card(card_id)
        if card:
            previews.append(engine.preview_card(card))

    return {"data": previews}


# ============================================================
# WebSocket 战斗主入口
# ============================================================
@app.websocket("/ws/battle/{battle_id}")
async def ws_battle(ws: WebSocket, battle_id: str):
    """v2 WS handler:事件队列驱动,双协程收发解耦。

    收 (recv_loop):接 cast/skip/flee/ping,asyncio.create_task(engine.cast())
    发 (send_loop):从 engine.events() 拉事件转 ws.send_json
    """
    await ws.accept()
    print(f"[WS] {battle_id} accepted")

    # ★ Phase C: WS 鉴权 — ?token=xxx 不正确直接拒绝
    ws_user = await get_ws_user(ws)
    if not ws_user:
        await ws.send_json({"type": "error", "data": {"message": "需要登录后再进入战斗"}})
        await ws.close(code=1008)  # 1008 = Policy Violation
        return
    user_id = ws_user["id"]

    engine: BattleEngine = get_battle(battle_id)
    if not engine:
        await ws.send_json({"type": "error", "data": {"message": "战斗不存在或已过期"}})
        await ws.close()
        return

    # 验证 battle 是该用户的,防止偷窥别人的 battle_id
    if engine.user_id != user_id:
        await ws.send_json({"type": "error", "data": {"message": "此战斗不属于你"}})
        await ws.close(code=1008)
        return

    # ★ Phase 4: 同一 battle 单 WS 连接,防止多标签页抢事件
    if engine.ws_attached:
        await ws.send_json({"type": "error", "data": {"message": "战斗已在其他窗口打开,请先关闭"}})
        await ws.close()
        return
    engine.ws_attached = True

    # 推初始状态
    await ws.send_json({"type": "state", "data": engine.snapshot()})

    # ★ 教学模式:仅当未看过教学时推欢迎提示
    if engine.tutorial:
        char_check = get_character(user_id)
        already_seen = (char_check or {}).get("flags", {}).get("battle_tutorial_done", False)
        if not already_seen:
            await ws.send_json({"type": "tutorial_hint", "data": {
                "step": "welcome",
                "message": "这是你的第一场战斗!点击下方卡牌释放招式。灵气(Token)越高的招式威力越强。",
            }})

    # 启动预生成池(非 speed 模式)— track 后台 task
    if engine.mode != "speed":
        engine._track_task(asyncio.create_task(engine.warmup_pool(count=3)))

    async def recv_loop():
        """接消息 — cast/use_item 用 create_task 异步触发,不阻塞收消息"""
        try:
            while not engine.is_finished():
                raw = await ws.receive_text()
                try:
                    msg = json.loads(raw)
                except json.JSONDecodeError:
                    await ws.send_json({"type": "error", "data": {"message": "消息格式错误"}})
                    continue

                action = msg.get("action")
                if action == "ping":
                    await ws.send_json({"type": "pong"})
                elif action == "cast":
                    card_id = msg.get("payload", {}).get("card_id")
                    if not card_id:
                        await ws.send_json({"type": "error", "data": {"message": "缺少 card_id"}})
                        continue
                    engine._track_task(asyncio.create_task(engine.cast(card_id)))
                elif action == "use_item":
                    # ★ Phase 3: 战斗内使用道具(走 BattleEngine 的原子方法)
                    item_id = msg.get("payload", {}).get("item_id")
                    if not item_id:
                        await ws.send_json({"type": "error", "data": {"message": "缺少 item_id"}})
                        continue
                    engine._track_task(asyncio.create_task(engine.use_item(item_id)))
                elif action == "skip":
                    engine.skip_narration()
                elif action == "skip_chapter":
                    # ★ Phase 4: 跳过战后章节
                    engine.skip_narration(include_chapter=True)
                elif action == "flee":
                    await engine.flee()
                    return
                else:
                    await ws.send_json({"type": "error", "data": {"message": f"未知 action: {action}"}})
        except WebSocketDisconnect:
            print(f"[WS recv] {battle_id} 玩家断开")
        except Exception as e:
            print(f"[WS recv] {battle_id} 异常: {type(e).__name__}: {e}")

    async def send_loop():
        """从 engine.events() 拉事件转 WS"""
        try:
            count = 0
            async for event in engine.events():
                count += 1
                try:
                    await ws.send_json(event)
                except Exception as e:
                    print(f"[WS send] {battle_id} ws.send 失败 (event #{count}): {e}")
                    return
            print(f"[WS send] {battle_id} events() 自然结束 (推了 {count} 个事件)")
        except Exception as e:
            print(f"[WS send] {battle_id} 异常: {type(e).__name__}: {e}")

    recv_t = asyncio.create_task(recv_loop())
    send_t = asyncio.create_task(send_loop())

    try:
        done, pending = await asyncio.wait(
            [recv_t, send_t],
            return_when=asyncio.FIRST_COMPLETED,
        )
        which = "recv" if recv_t in done else "send"
        print(f"[WS] {battle_id} {which} 先完成,cancel 另一个")
        for t in pending:
            t.cancel()
    finally:
        # ★ Phase 4: 清理后台 task + 释放 WS attach 标记
        engine.ws_attached = False
        try:
            await engine.cleanup()
        except Exception as e:
            print(f"[WS cleanup] {battle_id} err: {e}")
        try:
            await ws.close()
        except Exception:
            pass
        # 只在战斗真正结束才删 battle(允许重连未实现 — 暂留)
        if engine.is_finished():
            delete_battle(battle_id)
            print(f"[WS] {battle_id} 已清理")


# ============================================================
# ★ 今日修行令 API
# ============================================================
@app.get("/api/daily")
async def get_daily(current_user: dict = Depends(get_current_user)):
    user_id = current_user["id"]
    """获取今日修行令状态"""
    char = get_character(user_id)
    if not char:
        raise HTTPException(404, "未创建角色")
    today = get_today()
    state = get_daily_state(user_id, today)
    tasks = get_daily_status(state["tasks_done"])
    completed = count_completed(state["tasks_done"])
    return {"data": {
        "date": today,
        "tasks": tasks,
        "completed_count": completed,
        "required": 4,
        "can_claim": can_claim(state["tasks_done"]) and not state["claimed"],
        "claimed": state["claimed"],
        "reward_preview": get_reward_preview(),
    }}


@app.post("/api/daily/claim")
async def claim_daily(current_user: dict = Depends(get_current_user)):
    user_id = current_user["id"]
    """领取今日奖励"""
    char = get_character(user_id)
    if not char:
        raise HTTPException(404, "未创建角色")
    today = get_today()
    state = get_daily_state(user_id, today)
    if state["claimed"]:
        raise HTTPException(400, "今日已领取")
    if not can_claim(state["tasks_done"]):
        raise HTTPException(400, f"需完成至少 4 个任务,当前 {count_completed(state['tasks_done'])} 个")

    # 发放奖励:日课不再直接给修为,只给材料与宗门贡献
    for item_id, count in DAILY_REWARD["items"]:
        add_item(user_id, item_id, count)
    # 宗门贡献
    sect_id = char.get("sect", "canglan")
    factions = char.get("factions", {})
    factions[sect_id] = factions.get(sect_id, 0) + DAILY_REWARD["faction_rep"]
    char["factions"] = factions
    fatigue_delta = add_fatigue(char, "daily_claim")

    save_character(user_id, char)
    claim_daily_reward(user_id, today)
    _journal_safe(user_id, "daily_claim",
                  "领取今日修行令",
                  f"获得材料与宗门贡献 +{DAILY_REWARD['faction_rep']}",
                  {"tags": ["日课"]})

    return {"data": {
        "exp_gained": 0,
        "items_gained": DAILY_REWARD["items"],
        "faction_rep_gained": DAILY_REWARD["faction_rep"],
        "fatigue": fatigue_delta,
    }}


# ============================================================
# ★ 山海经图鉴 API
# ============================================================
@app.get("/api/bestiary")
async def get_bestiary_api(current_user: dict = Depends(get_current_user)):
    user_id = current_user["id"]
    """获取图鉴全览"""
    char = get_character(user_id)
    if not char:
        raise HTTPException(404, "未创建角色")
    bestiary = get_bestiary(user_id)

    # 按族群整理
    from .enemies import ALL_CLANS, ENEMIES
    clans_data = []
    for clan_name, members in ALL_CLANS.items():
        clan_entries = []
        discovered = 0
        for e in members:
            entry = bestiary.get(e.id)
            if entry and entry["encountered"] > 0:
                discovered += 1
                clan_entries.append({
                    "id": e.id,
                    "name": e.name,
                    "emoji": e.image_emoji,
                    "level": e.level,
                    "tier": e.tier,
                    **entry,
                    "discovered": True,
                })
            else:
                clan_entries.append({
                    "id": e.id,
                    "name": "???",
                    "emoji": "❓",
                    "level": e.level,
                    "tier": e.tier,
                    "discovered": False,
                })
        clans_data.append({
            "clan_name": clan_name,
            "total": len(members),
            "discovered": discovered,
            "progress": round(discovered / len(members) * 100),
            "entries": clan_entries,
        })

    total_discovered = sum(c["discovered"] for c in clans_data)
    total_enemies = sum(c["total"] for c in clans_data)

    return {"data": {
        "total_discovered": total_discovered,
        "total_enemies": total_enemies,
        "progress": round(total_discovered / total_enemies * 100) if total_enemies else 0,
        "clans": clans_data,
    }}


@app.get("/api/bestiary/{enemy_id}")
async def get_bestiary_entry(enemy_id: str, current_user: dict = Depends(get_current_user)):
    user_id = current_user["id"]
    """获取单个怪物图鉴详情"""
    from .enemies import get_enemy as _get_enemy, enemy_to_dict as _etd
    e = _get_enemy(enemy_id)
    if not e:
        raise HTTPException(404, "未知怪物")
    bestiary = get_bestiary(user_id)
    entry = bestiary.get(enemy_id, {})
    discovered = entry.get("encountered", 0) > 0

    data = _etd(e) if discovered else {"id": e.id, "name": "???", "level": e.level}
    data["bestiary"] = entry if discovered else None
    data["discovered"] = discovered
    # 材料来源
    if discovered:
        data["lore"] = e.lore
        data["drops_detail"] = [item_to_dict(get_item(d)) for d in e.drops if get_item(d)]
    return {"data": data}


# ============================================================
# ★ 炼丹炼器 API
# ============================================================
@app.get("/api/recipes")
async def list_recipes(current_user: dict = Depends(get_current_user)):
    """获取可用配方列表"""
    user_id = current_user["id"]
    char = get_character(user_id)
    if not char:
        raise HTTPException(404, "未创建角色")
    level = char.get("level", 1)
    inv = get_inventory(user_id)

    recipes = list_available_recipes(level)
    result = []
    for r in recipes:
        d = recipe_to_dict(r)
        d["can_craft"] = can_craft(r, inv)
        # 标注每个材料当前持有量 + 名称
        for mat in d["materials"]:
            mat["have"] = inv.get(mat["item_id"], 0)
            item_obj = get_item(mat["item_id"])
            mat["item_name"] = item_obj.name if item_obj else mat["item_id"]
            mat["item_icon"] = item_obj.icon if item_obj else "🎁"
            mat["item_icon_url"] = item_icon_url(mat["item_id"])
        # 产出物名称 / 图标 / 稀有度(让前端能正确显示)
        result_item = get_item(r.result_id)
        if result_item:
            d["result_name"] = result_item.name
            d["result_icon"] = result_item.icon
            d["result_icon_url"] = item_icon_url(r.result_id)
            d["result_rarity"] = result_item.rarity
            d["result_desc"] = result_item.description
        else:
            d["result_name"] = r.result_id
            d["result_icon"] = "❓"
            d["result_icon_url"] = ""
            d["result_rarity"] = 1
            d["result_desc"] = ""
        result.append(d)
    return {"data": result}


class CraftRequest(BaseModel):
    recipe_id: str


@app.post("/api/recipes/craft")
async def craft_item(req: CraftRequest, current_user: dict = Depends(get_current_user)):
    """合成物品"""
    user_id = current_user["id"]
    char = get_character(user_id)
    if not char:
        raise HTTPException(404, "未创建角色")

    recipe = get_recipe(req.recipe_id)
    if not recipe:
        raise HTTPException(404, "配方不存在")
    if recipe.unlock_level > char.get("level", 1):
        raise HTTPException(400, f"需达到 Lv.{recipe.unlock_level} 才能合成")

    inv = get_inventory(user_id)
    if not can_craft(recipe, inv):
        raise HTTPException(400, "材料不足")

    # 扣材料
    for mat_id, count in recipe.materials:
        remove_item(user_id, mat_id, count)

    # 给成品
    add_item(user_id, recipe.result_id, recipe.result_count)

    # 记录日课
    today = get_today()
    record_daily_task(user_id, today, "craft")
    fatigue_delta = add_fatigue(char, "craft")
    save_character(user_id, char)

    result_item = get_item(recipe.result_id)
    # ★ 写修行录:炼丹
    _result_name = result_item.name if result_item else recipe.result_id
    _journal_safe(user_id, "craft",
                  f"炼制 · {recipe.name}",
                  f"成功炼制 {_result_name} ×{recipe.result_count}",
                  {"tags": ["炼丹", recipe.category]})
    return {"data": {
        "recipe_name": recipe.name,
        "result": item_to_dict(result_item) if result_item else {"id": recipe.result_id},
        "result_count": recipe.result_count,
        "fatigue": fatigue_delta,
    }}


@app.get("/api/items/{item_id}/usages")
async def get_item_usages(item_id: str):
    """查询某材料可用于哪些配方"""
    usages = get_material_usages(item_id)
    recipes = [recipe_to_dict(get_recipe(rid)) for rid in usages if get_recipe(rid)]
    return {"data": {"item_id": item_id, "recipes": recipes}}


# ============================================================
# ★ Round 2: NPC 弟子互动 API
# ============================================================
from .npc import get_cached_npc, cache_npc, NpcSpawn


class NpcEngageRequest(BaseModel):
    npc_id: str
    intent: str   # pass / spar / hostile / trade / teach
    npc: Optional[dict] = None


def _int_between(value, default: int, min_value: int, max_value: int) -> int:
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        return default
    return max(min_value, min(max_value, parsed))


def _restore_npc_from_snapshot(snapshot: Optional[dict], npc_id: str) -> Optional[NpcSpawn]:
    if not snapshot or snapshot.get("id") != npc_id or not snapshot.get("is_npc"):
        return None

    sect_id = str(snapshot.get("sect_id") or "").strip()
    sect = get_sect(sect_id)
    if not sect:
        return None

    level = _int_between(snapshot.get("level"), 1, 1, 999)
    hp = _int_between(snapshot.get("max_hp") or snapshot.get("hp"), 100, 1, 1_000_000)
    atk = _int_between(snapshot.get("atk"), max(1, level * 3), 1, 100_000)
    def_ = _int_between(snapshot.get("def_"), max(1, level * 2), 0, 100_000)
    spd = _int_between(snapshot.get("spd"), 90, 1, 10_000)
    rank = str(snapshot.get("rank") or "弟子")[:12]
    intent = str(snapshot.get("intent") or "pass")
    if intent not in {"pass", "spar", "hostile", "trade", "teach"}:
        intent = "pass"

    npc = NpcSpawn(
        id=npc_id,
        name=str(snapshot.get("name") or "路过修士")[:24],
        sect_id=sect_id,
        sect_name=str(snapshot.get("sect_name") or sect.name)[:24],
        rank=rank,
        level=level,
        title=str(snapshot.get("title") or f"{sect.name} · {rank}弟子")[:40],
        intent=intent,
        hp=hp,
        max_hp=hp,
        atk=atk,
        def_=def_,
        spd=spd,
        rewards_exp=max(1, level * 8),
        rewards_qi=max(1, level * 5),
        drops=[],
        image_url=str(snapshot.get("image_url") or "")[:160],
        image_emoji=str(snapshot.get("image_emoji") or "👤")[:4],
        description=str(snapshot.get("description") or f"路遇{sect.name}弟子,行色匆匆。")[:160],
        clan=str(snapshot.get("clan") or f"{sect.name}弟子")[:40],
        tier=str(snapshot.get("tier") or "mid")[:16],
        portrait_kind=str(snapshot.get("portrait_kind") or "player")[:16],
        portrait_id=str(snapshot.get("portrait_id") or "")[:80],
    )
    cache_npc(npc)
    return npc


@app.post("/api/npc/engage")
async def npc_engage(req: NpcEngageRequest, current_user: dict = Depends(get_current_user)):
    """与 NPC 互动主入口 — 根据 intent 分发到 5 种处理"""
    user_id = current_user["id"]
    char = get_character(user_id)
    if not char:
        raise HTTPException(404, "未创建角色")
    npc = get_cached_npc(req.npc_id) or _restore_npc_from_snapshot(req.npc, req.npc_id)
    if not npc:
        raise HTTPException(404, "NPC 已离开或不存在")

    if req.intent == "pass":
        fatigue_delta = add_fatigue(char, "npc_pass")
        save_character(user_id, char)
        _journal_safe(user_id, "fortune", f"路遇·{npc.sect_name}",
                      f"擦肩而过,留下一缕灵气共鸣。",
                      {"tags":["邂逅", npc.sect_name]})
        return {"data": {
            "result": "pass",
            "narrative": f"{npc.name}向你拱手作礼,擦肩而过。「修行路漫漫,望君早日得道。」",
            "exp_gained": 0,
            "fatigue": fatigue_delta,
        }}

    if req.intent == "trade":
        fatigue_delta = add_fatigue(char, "npc_trade")
        save_character(user_id, char)
        # 返回商店物品 — 由前端打开 modal,玩家挑选
        from .items import get_item
        # 商店物品池:NPC 派系材料 + 心得
        pool_ids = list(set([
            "item_skill_essence_basic",
            "item_skill_essence_mid",
            "item_skill_codex_universal",
            "item_focus_pill",
            "item_lingdan_basic",
        ] + (npc.drops or [])))
        items_for_sale = []
        for iid in pool_ids:
            it = get_item(iid)
            if it:
                items_for_sale.append({
                    "id": iid,
                    "name": it.name,
                    "icon": it.icon,
                    "icon_url": item_icon_url(iid),
                    "rarity": it.rarity,
                    "description": it.description,
                    # 价格 = value_qi × (1 + 派系敌意 / 10) 暂用固定 1.2x
                    "price_qi": int(it.value_qi * 1.2) if it.value_qi else 50,
                })
        return {"data": {
            "result": "trade_offer",
            "narrative": f"{npc.name}打开行囊:「修行人有缘,我这里有些上好的东西。」",
            "items": items_for_sale,
            "fatigue": fatigue_delta,
        }}

    if req.intent == "teach":
        # 30% 成功传授一招跨派招式 + 需要消耗 1 个 通用秘籍
        from .store import get_inventory, remove_item, add_item
        inv = get_inventory(user_id)
        have_codex = next((it["count"] for it in inv if it["id"] == "item_skill_codex_universal"), 0)
        if have_codex < 1:
            return {"data": {
                "result": "teach_no_codex",
                "narrative": f"{npc.name}问道:「持通用秘籍而来否?无秘籍则无以承学。」",
                "required": {"item_id": "item_skill_codex_universal", "count": 1, "have": have_codex},
            }}
        fatigue_delta = add_fatigue(char, "npc_teach")
        # 扣秘籍
        remove_item(user_id, "item_skill_codex_universal", 1)
        # 30% 成功
        if _random.random() < 0.30:
            # 选一个 NPC 派的同等级或更低的招式
            from .skill_templates import ALL_SKILLS_LIST, skills_for_sect_at_realm
            char_realm = char.get("realm", "qi")
            candidates = skills_for_sect_at_realm(npc.sect_id, char_realm)
            # 排除玩家已学的
            learned_ids = {ls["skill_id"] for ls in char.get("learned_skills", [])}
            unlearned = [s for s in candidates if s.id not in learned_ids and s.sect == npc.sect_id]
            if unlearned:
                taught = _random.choice(unlearned)
                char.setdefault("learned_skills", []).append({"skill_id": taught.id, "level": 1})
                save_character(user_id, char)
                _journal_safe(user_id, "teach", f"求道·{npc.sect_name}",
                              f"{npc.name}传你 {taught.name}",
                              {"tags":["跨派", npc.sect_name, taught.name]})
                return {"data": {
                    "result": "teach_success",
                    "narrative": f"{npc.name}演示一招《{taught.name}》:「拙学,望君笑纳。」",
                    "skill": {"id": taught.id, "name": taught.name, "icon": taught.icon,
                              "sect": npc.sect_id, "description": taught.description},
                    "fatigue": fatigue_delta,
                }}
            else:
                # 没有可教的(玩家全学了)→ 返还秘籍
                add_item(user_id, "item_skill_codex_universal", 1)
                save_character(user_id, char)
                return {"data": {
                    "result": "teach_no_new",
                    "narrative": f"{npc.name}叹道:「君于敝派之学,已尽得其妙,无所传授。」",
                    "fatigue": fatigue_delta,
                }}
        else:
            # 失败,秘籍消耗
            save_character(user_id, char)
            return {"data": {
                "result": "teach_fail",
                "narrative": f"{npc.name}摇头:「时机不对,缘分未到。」秘籍化作飞灰。",
                "fatigue": fatigue_delta,
            }}

    if req.intent == "spar":
        # 切磋 — 创建一场友好战斗(后续接 battle/start-vs-npc)
        # 这里我们用 enemy_id 注册一个伪 enemy,然后调 BattleEngine
        return await _start_npc_battle(user_id, char, npc, friendly=True)

    if req.intent == "hostile":
        # 真斗
        return await _start_npc_battle(user_id, char, npc, friendly=False)

    raise HTTPException(400, f"未知意图: {req.intent}")


async def _start_npc_battle(user_id: str, char: dict, npc, friendly: bool) -> dict:
    """启动 NPC 战斗(切磋/真斗共用,通过 friendly flag 区分)"""
    # 注册一个临时 enemy 让 BattleEngine 能 lookup
    # 利用 enemies.ENEMIES 缓存:塞进去临时 entry
    from .enemies import ENEMIES, Enemy
    # 用 Enemy dataclass 复用
    fake_enemy = Enemy(
        id=npc.id, name=npc.name, clan=npc.clan, tier=npc.tier, level=npc.level,
        hp=npc.hp, atk=npc.atk, def_=npc.def_, spd=npc.spd, evasion=0.05,
        rewards_exp=npc.rewards_exp, rewards_qi=npc.rewards_qi,
        image_emoji=npc.image_emoji, description=npc.description,
        lore=f"{npc.sect_name}{npc.rank}弟子",
        drops=list(npc.drops),
    )
    fake_enemy.image_url = npc.image_url
    fake_enemy.is_npc = True
    fake_enemy.sect_id = npc.sect_id
    fake_enemy.sect_name = npc.sect_name
    fake_enemy.rank = npc.rank
    fake_enemy.portrait_kind = npc.portrait_kind
    fake_enemy.portrait_id = npc.portrait_id
    ENEMIES[npc.id] = fake_enemy   # 注入临时 enemy

    # 启动战斗(复用 start_battle 逻辑)
    engine = BattleEngine(char, npc.id, mode="drama", tutorial=False, user_id=user_id)
    # ★ 标记友好模式 — BattleEngine 在 _commit_battle_result 里区分
    engine.state["friendly"] = friendly
    engine.state["is_npc_battle"] = True
    engine.state["npc_sect"] = npc.sect_id
    engine.state["npc_rank"] = npc.rank
    engine.state["enemy_portrait_kind"] = npc.portrait_kind
    engine.state["enemy_portrait_id"] = npc.portrait_id
    save_battle(engine.battle_id, engine)
    return {"data": {
        "result": "battle_start",
        "battle_id": engine.battle_id,
        "narrative": (
            f"{npc.name}笑道:「请赐教!」(切磋开始)" if friendly
            else f"{npc.name}冷笑:「来吧!」(真斗开始,死生由命)"
        ),
        "friendly": friendly,
        "snapshot": engine.snapshot(),
    }}


class NpcTradeBuyRequest(BaseModel):
    npc_id: str
    item_id: str
    count: int = 1


@app.post("/api/npc/trade-buy")
async def npc_trade_buy(req: NpcTradeBuyRequest, current_user: dict = Depends(get_current_user)):
    """从 NPC 处购买物品"""
    user_id = current_user["id"]
    char = get_character(user_id)
    if not char:
        raise HTTPException(404, "未创建角色")
    npc = get_cached_npc(req.npc_id)
    if not npc:
        raise HTTPException(404, "商人已离开")

    from .items import get_item
    item = get_item(req.item_id)
    if not item:
        raise HTTPException(404, "物品不存在")
    price = int((item.value_qi or 50) * 1.2 * req.count)
    if char.get("qi", 0) < price:
        raise HTTPException(400, f"灵气不足(需 {price})")
    char["qi"] -= price
    fatigue_delta = add_fatigue(char, "npc_trade")
    add_item(user_id, req.item_id, req.count)
    save_character(user_id, char)
    return {"data": {
        "result": "bought",
        "item_id": req.item_id, "count": req.count, "price_qi": price,
        "qi_left": char["qi"],
        "fatigue": fatigue_delta,
    }}


# ============================================================
# ★ Round 1: 技能树 API
# ============================================================
from .skill_templates import (
    ALL_SKILLS, ALL_SKILLS_LIST, UPGRADE_COST, REALM_ORDER,
    skill_to_dict, get_skill, skills_for_sect_at_realm, effective_battle_qi_cost,
)
from .attributes import sync_learned_skills


def _skill_drop_sources(item_id: str, limit: int = 8) -> dict:
    item = get_item(item_id)
    if not item:
        return {"item_id": item_id, "item_name": item_id, "sources": [], "more_count": 0}

    sources = []
    seen = set()
    for enemy in ENEMIES.values():
        if enemy.id in seen:
            continue
        seen.add(enemy.id)
        if item_id not in getattr(enemy, "drops", []):
            continue
        rate = skill_drop_rate_for_enemy(enemy)
        sources.append({
            "enemy_id": enemy.id,
            "enemy_name": enemy.name,
            "clan": enemy.clan,
            "tier": enemy.tier,
            "level": enemy.level,
            "rate": rate,
            "rate_label": drop_rate_label(rate),
        })

    sources.sort(key=lambda s: (-s["rate"], s["level"]))
    return {
        "item_id": item.id,
        "item_name": item.name,
        "item_icon": item.icon,
        "item_icon_url": item_icon_url(item.id),
        "item_rarity": item.rarity,
        "sources": sources[:limit],
        "more_count": max(0, len(sources) - limit),
    }


@app.get("/api/skills/all")
async def list_all_skills(current_user: dict = Depends(get_current_user)):
    """技能树:返回全部 56 招式 + 玩家当前学习/装备状态"""
    user_id = current_user["id"]
    char = get_character(user_id)
    if not char:
        raise HTTPException(404, "未创建角色")
    sync_learned_skills(char)
    save_character(user_id, char)

    learned = {ls["skill_id"]: ls["level"] for ls in char.get("learned_skills", [])}
    equipped = set(char.get("equipped_skills", []))
    sect = char.get("sect", "canglan")
    realm = char.get("realm", "qi")
    realm_idx = REALM_ORDER.index(realm) if realm in REALM_ORDER else 0

    skills_out = []
    for s in ALL_SKILLS_LIST:
        if s.sect not in ("any", sect):
            # 跨派招式不展示(除非已学到)
            if s.id not in learned:
                continue
        unlock_idx = REALM_ORDER.index(s.realm_unlock) if s.realm_unlock in REALM_ORDER else 0
        unlocked = unlock_idx <= realm_idx
        level = learned.get(s.id, 1)
        d = skill_to_dict(s, level=level, learned=(s.id in learned), equipped=(s.id in equipped))
        d["battle_qi_cost"] = effective_battle_qi_cost(s, level, char.get("max_qi", 600))
        d["qi_cost_mode"] = "percent_max_qi"
        d["unlocked"] = unlocked or s.id in learned
        d["realm_unlock_name"] = {"qi":"炼气","foundation":"筑基","golden":"金丹","yuanying":"元婴",
                                  "huashen":"化神","hetishi":"合体","dacheng":"大乘","dujie":"渡劫",
                                  "feisheng":"飞升"}.get(s.realm_unlock, s.realm_unlock)
        if d.get("next_upgrade"):
            d["drop_hint"] = _skill_drop_sources(d["next_upgrade"]["material_id"])
        skills_out.append(d)
    return {"data": {
        "skills": skills_out,
        "drop_overview": [
            hint for hint in (
                _skill_drop_sources(item_id)
                for item_id in [
                    SKILL_DROP_BY_TIER["low"],
                    SKILL_DROP_BY_TIER["mid"],
                    SKILL_DROP_BY_TIER["high"],
                    SKILL_DROP_BY_TIER["myth"],
                ]
            )
            if hint["sources"]
        ],
        "current_realm": realm,
        "current_realm_name": char.get("realm_name", ""),
        "sect": sect,
        "equipped_slots_used": len(equipped),
        "equipped_slots_max": 6,
    }}


class EquipSkillsRequest(BaseModel):
    skill_ids: list   # 最多 6 个


@app.post("/api/skills/equip")
async def equip_skills(req: EquipSkillsRequest, current_user: dict = Depends(get_current_user)):
    """装备技能(替换当前 equipped_skills 列表,最多 6 个)"""
    user_id = current_user["id"]
    char = get_character(user_id)
    if not char:
        raise HTTPException(404, "未创建角色")
    learned_ids = {ls["skill_id"] for ls in char.get("learned_skills", [])}
    new_eq = []
    for sid in req.skill_ids[:6]:
        if sid not in learned_ids:
            raise HTTPException(400, f"招式 {sid} 尚未学习")
        if sid not in new_eq:  # 去重
            new_eq.append(sid)
    char["equipped_skills"] = new_eq
    fatigue_delta = add_fatigue(char, "skill_equip")
    save_character(user_id, char)
    return {"data": {"equipped_skills": new_eq, "fatigue": fatigue_delta}}


class UpgradeSkillRequest(BaseModel):
    skill_id: str


@app.post("/api/skills/upgrade")
async def upgrade_skill(req: UpgradeSkillRequest, current_user: dict = Depends(get_current_user)):
    """升级招式 1 级,消耗对应等级心得"""
    user_id = current_user["id"]
    char = get_character(user_id)
    if not char:
        raise HTTPException(404, "未创建角色")
    tpl = get_skill(req.skill_id)
    if not tpl:
        raise HTTPException(404, "招式不存在")
    learned = char.get("learned_skills", [])
    ls = next((x for x in learned if x["skill_id"] == req.skill_id), None)
    if not ls:
        raise HTTPException(400, "尚未学习此招式")
    if ls["level"] >= tpl.max_level:
        raise HTTPException(400, f"此招式已满级 Lv{tpl.max_level}")
    target_level = ls["level"] + 1
    if target_level not in UPGRADE_COST:
        raise HTTPException(400, "升级配置错误")
    mat_id, mat_count = UPGRADE_COST[target_level]
    inv = get_inventory(user_id)
    have = inv.get(mat_id, 0) if isinstance(inv, dict) else next((it["count"] for it in inv if it["id"] == mat_id), 0)
    if have < mat_count:
        item = get_item(mat_id)
        raise HTTPException(400, f"需要 {mat_count}× {item.name if item else mat_id} (持有 {have})")
    # 扣材料 + 升级
    remove_item(user_id, mat_id, mat_count)
    ls["level"] = target_level
    char["learned_skills"] = learned
    fatigue_delta = add_fatigue(char, "skill_upgrade")
    save_character(user_id, char)
    _journal_safe(user_id, "skill_upgrade", f"招式精进·{tpl.name}",
                  f"{tpl.name} 已晋升至 Lv {target_level}", {"tags":["招式","精进"]})
    return {"data": {
        "skill_id": req.skill_id, "new_level": target_level,
        "consumed": {"item_id": mat_id, "count": mat_count},
        "fatigue": fatigue_delta,
        "new_stats": skill_to_dict(tpl, level=target_level, learned=True,
                                   equipped=(req.skill_id in char.get("equipped_skills", []))),
    }}


# ============================================================
# ★ 修行录 API
# ============================================================
@app.get("/api/journal")
async def list_journal(limit: int = 20, offset: int = 0, current_user: dict = Depends(get_current_user)):
    user_id = current_user["id"]
    """获取修行录列表"""
    entries = get_journal(user_id, limit, offset)
    total = count_journal(user_id)
    return {"data": {"entries": entries, "total": total}}


# ============================================================
# 启动
# ============================================================
if __name__ == "__main__":
    import uvicorn
    host = os.getenv("HOST", "127.0.0.1")
    port = int(os.getenv("PORT", "8020"))
    uvicorn.run("app.main:app", host=host, port=port, reload=True)
