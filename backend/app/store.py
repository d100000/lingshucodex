"""持久化存储 — SQLite 后端

保持原有函数签名不变,所有调用方无需修改。
- 角色/背包/装备/图鉴/日课 → SQLite 持久化
- 战斗实例 → 仍在内存(WebSocket 生命周期内)
"""

from __future__ import annotations

import json
import sqlite3
import os
import threading
import uuid
from typing import Optional

# ════════════════════════════════════════════════════════════
# SQLite 初始化
# ════════════════════════════════════════════��═══════════════
_DB_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "lingshu.db")
_local = threading.local()


def _get_conn() -> sqlite3.Connection:
    """每线程一个 connection(SQLite 不允许跨线程共享)"""
    if not hasattr(_local, "conn") or _local.conn is None:
        os.makedirs(os.path.dirname(_DB_PATH), exist_ok=True)
        _local.conn = sqlite3.connect(_DB_PATH, check_same_thread=False)
        _local.conn.execute("PRAGMA journal_mode=WAL")
        _local.conn.execute("PRAGMA synchronous=NORMAL")
        _local.conn.row_factory = sqlite3.Row
    return _local.conn


def _init_db():
    """建表 — 幂等执行"""
    conn = _get_conn()
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS characters (
            user_id TEXT PRIMARY KEY,
            data TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS inventories (
            user_id TEXT NOT NULL,
            item_id TEXT NOT NULL,
            count INTEGER NOT NULL DEFAULT 0,
            PRIMARY KEY (user_id, item_id)
        );
        CREATE TABLE IF NOT EXISTS equipped (
            user_id TEXT NOT NULL,
            slot TEXT NOT NULL,
            item_id TEXT NOT NULL,
            PRIMARY KEY (user_id, slot)
        );
        CREATE TABLE IF NOT EXISTS bestiary (
            user_id TEXT NOT NULL,
            enemy_id TEXT NOT NULL,
            encountered INTEGER NOT NULL DEFAULT 0,
            defeated INTEGER NOT NULL DEFAULT 0,
            gifted INTEGER NOT NULL DEFAULT 0,
            drops_found TEXT NOT NULL DEFAULT '[]',
            first_kill_at TEXT,
            PRIMARY KEY (user_id, enemy_id)
        );
        CREATE TABLE IF NOT EXISTS daily_state (
            user_id TEXT NOT NULL,
            date TEXT NOT NULL,
            tasks_done TEXT NOT NULL DEFAULT '{}',
            claimed INTEGER NOT NULL DEFAULT 0,
            PRIMARY KEY (user_id, date)
        );
        CREATE TABLE IF NOT EXISTS journal (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT NOT NULL,
            type TEXT NOT NULL,
            title TEXT NOT NULL,
            content TEXT,
            meta TEXT,
            created_at TEXT NOT NULL DEFAULT (datetime('now'))
        );
        CREATE INDEX IF NOT EXISTS idx_journal_user ON journal(user_id);

        -- ★ 用户表(支持多账号 + JWT)
        CREATE TABLE IF NOT EXISTS users (
            id TEXT PRIMARY KEY,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            is_admin INTEGER DEFAULT 0,
            created_at TEXT NOT NULL DEFAULT (datetime('now')),
            last_login_at TEXT
        );
        CREATE INDEX IF NOT EXISTS idx_users_username ON users(username);

        CREATE TABLE IF NOT EXISTS schema_meta (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL
        );
        INSERT OR REPLACE INTO schema_meta (key, value)
            VALUES ('schema_version', 'cultivation_v2');

        CREATE TABLE IF NOT EXISTS cultivation_tasks (
            id TEXT PRIMARY KEY,
            user_id TEXT NOT NULL,
            task_type TEXT NOT NULL,
            source_type TEXT,
            source_id TEXT,
            status TEXT NOT NULL DEFAULT 'queued',
            priority INTEGER NOT NULL DEFAULT 0,
            title TEXT NOT NULL,
            prompt_payload TEXT NOT NULL DEFAULT '{}',
            content_partial TEXT NOT NULL DEFAULT '',
            estimated_tokens INTEGER NOT NULL DEFAULT 0,
            settled_tokens INTEGER NOT NULL DEFAULT 0,
            input_tokens INTEGER NOT NULL DEFAULT 0,
            output_tokens INTEGER NOT NULL DEFAULT 0,
            reasoning_tokens INTEGER NOT NULL DEFAULT 0,
            cultivation_gained INTEGER NOT NULL DEFAULT 0,
            model TEXT,
            usage_source TEXT NOT NULL DEFAULT 'estimated',
            budget_snapshot TEXT NOT NULL DEFAULT '{}',
            error TEXT,
            created_at TEXT NOT NULL DEFAULT (datetime('now')),
            started_at TEXT,
            paused_at TEXT,
            finished_at TEXT,
            cancelled_at TEXT
        );
        CREATE INDEX IF NOT EXISTS idx_cultivation_tasks_user_status
            ON cultivation_tasks(user_id, status, priority, created_at);

        CREATE TABLE IF NOT EXISTS novel_chapters (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT NOT NULL,
            chapter_no INTEGER NOT NULL,
            volume_no INTEGER NOT NULL,
            chapter_type TEXT NOT NULL,
            title TEXT NOT NULL,
            content TEXT NOT NULL,
            summary TEXT,
            status TEXT NOT NULL DEFAULT 'completed',
            is_partial INTEGER NOT NULL DEFAULT 0,
            task_id TEXT,
            source_type TEXT,
            source_id TEXT,
            battle_id TEXT,
            enemy_id TEXT,
            boss_id TEXT,
            npc_id TEXT,
            token_count INTEGER NOT NULL DEFAULT 0,
            input_tokens INTEGER NOT NULL DEFAULT 0,
            output_tokens INTEGER NOT NULL DEFAULT 0,
            reasoning_tokens INTEGER NOT NULL DEFAULT 0,
            cultivation_gained INTEGER NOT NULL DEFAULT 0,
            model TEXT,
            usage_source TEXT NOT NULL DEFAULT 'estimated',
            word_count INTEGER NOT NULL DEFAULT 0,
            created_at TEXT NOT NULL DEFAULT (datetime('now')),
            completed_at TEXT
        );
        CREATE INDEX IF NOT EXISTS idx_novel_chapters_user
            ON novel_chapters(user_id, volume_no, chapter_no);

        CREATE TABLE IF NOT EXISTS token_ledger (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT NOT NULL,
            task_id TEXT,
            chapter_id INTEGER,
            source TEXT NOT NULL,
            delta_tokens INTEGER NOT NULL DEFAULT 0,
            input_tokens INTEGER NOT NULL DEFAULT 0,
            output_tokens INTEGER NOT NULL DEFAULT 0,
            reasoning_tokens INTEGER NOT NULL DEFAULT 0,
            usage_source TEXT NOT NULL DEFAULT 'estimated',
            provider TEXT,
            model TEXT,
            created_at TEXT NOT NULL DEFAULT (datetime('now'))
        );
        CREATE INDEX IF NOT EXISTS idx_token_ledger_user
            ON token_ledger(user_id, created_at);

        CREATE TABLE IF NOT EXISTS world_saves (
            user_id TEXT PRIMARY KEY,
            revision INTEGER NOT NULL DEFAULT 0,
            data TEXT NOT NULL,
            updated_at TEXT NOT NULL DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS admin_audit_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            admin_user_id TEXT NOT NULL,
            action TEXT NOT NULL,
            target_type TEXT NOT NULL,
            target_id TEXT NOT NULL,
            before_json TEXT,
            after_json TEXT,
            reason TEXT,
            created_at TEXT NOT NULL DEFAULT (datetime('now'))
        );
        CREATE INDEX IF NOT EXISTS idx_admin_audit_target
            ON admin_audit_logs(target_type, target_id, created_at);

        CREATE TABLE IF NOT EXISTS item_ledger (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT NOT NULL,
            item_id TEXT NOT NULL,
            delta_count INTEGER NOT NULL,
            before_count INTEGER NOT NULL DEFAULT 0,
            after_count INTEGER NOT NULL DEFAULT 0,
            source TEXT NOT NULL DEFAULT 'admin',
            reason TEXT,
            admin_user_id TEXT,
            created_at TEXT NOT NULL DEFAULT (datetime('now'))
        );
        CREATE INDEX IF NOT EXISTS idx_item_ledger_user
            ON item_ledger(user_id, created_at);

        CREATE TABLE IF NOT EXISTS world_round_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT NOT NULL,
            client_round_id TEXT,
            from_revision INTEGER NOT NULL DEFAULT 0,
            to_revision INTEGER NOT NULL DEFAULT 0,
            from_day INTEGER NOT NULL DEFAULT 0,
            to_day INTEGER NOT NULL DEFAULT 0,
            character_patch_json TEXT,
            summary_json TEXT,
            event_count INTEGER NOT NULL DEFAULT 0,
            payload_size INTEGER NOT NULL DEFAULT 0,
            status TEXT NOT NULL DEFAULT 'saved',
            error TEXT,
            created_at TEXT NOT NULL DEFAULT (datetime('now'))
        );
        CREATE INDEX IF NOT EXISTS idx_world_round_logs_user
            ON world_round_logs(user_id, created_at);
    """)
    conn.commit()


# 启动时初始化
_init_db()

SITE_CONFIG_DEFAULTS = {
    "show_bobdong_ads": False,
}


def get_site_config() -> dict:
    """读取全站配置。默认关闭 BobDong.cn 广告。"""
    conn = _get_conn()
    row = conn.execute(
        "SELECT value FROM schema_meta WHERE key = ?",
        ("site_config",),
    ).fetchone()
    saved = {}
    if row:
        try:
            saved = json.loads(row[0]) or {}
        except Exception:
            saved = {}
    return {**SITE_CONFIG_DEFAULTS, **saved}


def save_site_config(config: dict) -> dict:
    cfg = {**SITE_CONFIG_DEFAULTS, **(config or {})}
    conn = _get_conn()
    conn.execute(
        "INSERT OR REPLACE INTO schema_meta (key, value) VALUES (?, ?)",
        ("site_config", json.dumps(cfg, ensure_ascii=False)),
    )
    conn.commit()
    return cfg


def update_site_config(patch: dict) -> dict:
    cfg = get_site_config()
    for key in SITE_CONFIG_DEFAULTS:
        if key in patch:
            cfg[key] = patch[key]
    return save_site_config(cfg)


# ════════════════════════════════════════════════════════════
# 角色 CRUD(保持原 API)
# ════════════════════════════════════════════════════════════
def get_character(user_id: str) -> Optional[dict]:
    conn = _get_conn()
    row = conn.execute(
        "SELECT data FROM characters WHERE user_id = ?", (user_id,)
    ).fetchone()
    if row:
        return json.loads(row[0])
    return None


def save_character(user_id: str, character: dict):
    conn = _get_conn()
    conn.execute(
        "INSERT OR REPLACE INTO characters (user_id, data) VALUES (?, ?)",
        (user_id, json.dumps(character, ensure_ascii=False)),
    )
    conn.commit()


def delete_character(user_id: str):
    conn = _get_conn()
    conn.execute("DELETE FROM characters WHERE user_id = ?", (user_id,))
    conn.execute("DELETE FROM inventories WHERE user_id = ?", (user_id,))
    conn.execute("DELETE FROM equipped WHERE user_id = ?", (user_id,))
    conn.execute("DELETE FROM bestiary WHERE user_id = ?", (user_id,))
    conn.execute("DELETE FROM daily_state WHERE user_id = ?", (user_id,))
    conn.execute("DELETE FROM journal WHERE user_id = ?", (user_id,))
    conn.execute("DELETE FROM cultivation_tasks WHERE user_id = ?", (user_id,))
    conn.execute("DELETE FROM novel_chapters WHERE user_id = ?", (user_id,))
    conn.execute("DELETE FROM token_ledger WHERE user_id = ?", (user_id,))
    conn.execute("DELETE FROM world_saves WHERE user_id = ?", (user_id,))
    conn.commit()


def get_world_save(user_id: str) -> Optional[dict]:
    conn = _get_conn()
    row = conn.execute(
        "SELECT revision, data, updated_at FROM world_saves WHERE user_id = ?",
        (user_id,),
    ).fetchone()
    if not row:
        return None
    try:
        data = json.loads(row["data"])
    except Exception:
        data = {}
    return {"revision": row["revision"], "data": data, "updated_at": row["updated_at"]}


def save_world_save(user_id: str, revision: int, data: dict) -> dict:
    revision = max(0, int(revision or 0))
    conn = _get_conn()
    conn.execute(
        """
        INSERT INTO world_saves (user_id, revision, data, updated_at)
        VALUES (?, ?, ?, datetime('now'))
        ON CONFLICT(user_id) DO UPDATE SET
          revision = excluded.revision,
          data = excluded.data,
          updated_at = datetime('now')
        """,
        (user_id, revision, json.dumps(data or {}, ensure_ascii=False)),
    )
    conn.commit()
    return get_world_save(user_id) or {"revision": revision, "data": data or {}, "updated_at": None}


def add_admin_audit_log(
    admin_user_id: str,
    action: str,
    target_type: str,
    target_id: str,
    before: dict | None = None,
    after: dict | None = None,
    reason: str = "",
) -> int:
    conn = _get_conn()
    cur = conn.execute(
        """INSERT INTO admin_audit_logs
           (admin_user_id, action, target_type, target_id, before_json, after_json, reason)
           VALUES (?, ?, ?, ?, ?, ?, ?)""",
        (
            admin_user_id,
            action,
            target_type,
            target_id,
            json.dumps(before or {}, ensure_ascii=False),
            json.dumps(after or {}, ensure_ascii=False),
            reason or "",
        ),
    )
    conn.commit()
    return cur.lastrowid


def list_admin_audit_logs(target_type: str = "", target_id: str = "", limit: int = 50) -> list[dict]:
    conn = _get_conn()
    if target_type and target_id:
        rows = conn.execute(
            """SELECT * FROM admin_audit_logs
               WHERE target_type = ? AND target_id = ?
               ORDER BY id DESC LIMIT ?""",
            (target_type, target_id, limit),
        ).fetchall()
    else:
        rows = conn.execute(
            "SELECT * FROM admin_audit_logs ORDER BY id DESC LIMIT ?",
            (limit,),
        ).fetchall()
    return [
        {
            "id": r["id"],
            "admin_user_id": r["admin_user_id"],
            "action": r["action"],
            "target_type": r["target_type"],
            "target_id": r["target_id"],
            "before": _json_loads(r["before_json"], {}),
            "after": _json_loads(r["after_json"], {}),
            "reason": r["reason"],
            "created_at": r["created_at"],
        }
        for r in rows
    ]


def add_item_ledger(
    user_id: str,
    item_id: str,
    delta_count: int,
    before_count: int,
    after_count: int,
    source: str = "admin",
    reason: str = "",
    admin_user_id: str = "",
) -> int:
    conn = _get_conn()
    cur = conn.execute(
        """INSERT INTO item_ledger
           (user_id, item_id, delta_count, before_count, after_count, source, reason, admin_user_id)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
        (user_id, item_id, delta_count, before_count, after_count, source, reason, admin_user_id or None),
    )
    conn.commit()
    return cur.lastrowid


def list_item_ledger(user_id: str, limit: int = 80) -> list[dict]:
    conn = _get_conn()
    rows = conn.execute(
        """SELECT * FROM item_ledger
           WHERE user_id = ?
           ORDER BY id DESC LIMIT ?""",
        (user_id, limit),
    ).fetchall()
    return [
        {
            "id": r["id"],
            "user_id": r["user_id"],
            "item_id": r["item_id"],
            "delta_count": r["delta_count"],
            "before_count": r["before_count"],
            "after_count": r["after_count"],
            "source": r["source"],
            "reason": r["reason"],
            "admin_user_id": r["admin_user_id"],
            "created_at": r["created_at"],
        }
        for r in rows
    ]


def add_world_round_log(
    user_id: str,
    client_round_id: str = "",
    from_revision: int = 0,
    to_revision: int = 0,
    from_day: int = 0,
    to_day: int = 0,
    character_patch: dict | None = None,
    summary: dict | None = None,
    event_count: int = 0,
    payload_size: int = 0,
    status: str = "saved",
    error: str = "",
) -> int:
    conn = _get_conn()
    cur = conn.execute(
        """INSERT INTO world_round_logs
           (user_id, client_round_id, from_revision, to_revision, from_day, to_day,
            character_patch_json, summary_json, event_count, payload_size, status, error)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (
            user_id,
            client_round_id or None,
            int(from_revision or 0),
            int(to_revision or 0),
            int(from_day or 0),
            int(to_day or 0),
            json.dumps(character_patch or {}, ensure_ascii=False),
            json.dumps(summary or {}, ensure_ascii=False),
            int(event_count or 0),
            int(payload_size or 0),
            status,
            error or None,
        ),
    )
    conn.commit()
    return cur.lastrowid


def list_world_round_logs(user_id: str, limit: int = 50) -> list[dict]:
    conn = _get_conn()
    rows = conn.execute(
        """SELECT * FROM world_round_logs
           WHERE user_id = ?
           ORDER BY id DESC LIMIT ?""",
        (user_id, limit),
    ).fetchall()
    return [
        {
            "id": r["id"],
            "user_id": r["user_id"],
            "client_round_id": r["client_round_id"],
            "from_revision": r["from_revision"],
            "to_revision": r["to_revision"],
            "from_day": r["from_day"],
            "to_day": r["to_day"],
            "character_patch": _json_loads(r["character_patch_json"], {}),
            "summary": _json_loads(r["summary_json"], {}),
            "event_count": r["event_count"],
            "payload_size": r["payload_size"],
            "status": r["status"],
            "error": r["error"],
            "created_at": r["created_at"],
        }
        for r in rows
    ]


# ════════════════════════════════════════════════════════════
# 战斗(内存 — WebSocket 生命周期)
# ════════════════════════════════════════════════════════════
_battles: dict[str, object] = {}


def get_battle(battle_id: str):
    return _battles.get(battle_id)


def save_battle(battle_id: str, engine):
    _battles[battle_id] = engine


def delete_battle(battle_id: str):
    _battles.pop(battle_id, None)


# ════════════════════════════════════════════════════════════
# 背包
# ════════════════════════════════════════════════════════════
def get_inventory(user_id: str) -> dict[str, int]:
    conn = _get_conn()
    rows = conn.execute(
        "SELECT item_id, count FROM inventories WHERE user_id = ? AND count > 0",
        (user_id,),
    ).fetchall()
    return {r[0]: r[1] for r in rows}


def add_item(user_id: str, item_id: str, count: int = 1) -> int:
    conn = _get_conn()
    conn.execute(
        """INSERT INTO inventories (user_id, item_id, count)
           VALUES (?, ?, ?)
           ON CONFLICT(user_id, item_id) DO UPDATE SET count = count + excluded.count""",
        (user_id, item_id, count),
    )
    conn.commit()
    row = conn.execute(
        "SELECT count FROM inventories WHERE user_id = ? AND item_id = ?",
        (user_id, item_id),
    ).fetchone()
    return row[0] if row else 0


def remove_item(user_id: str, item_id: str, count: int = 1) -> bool:
    conn = _get_conn()
    row = conn.execute(
        "SELECT count FROM inventories WHERE user_id = ? AND item_id = ?",
        (user_id, item_id),
    ).fetchone()
    cur = row[0] if row else 0
    if cur < count:
        return False
    new_count = cur - count
    if new_count == 0:
        conn.execute(
            "DELETE FROM inventories WHERE user_id = ? AND item_id = ?",
            (user_id, item_id),
        )
    else:
        conn.execute(
            "UPDATE inventories SET count = ? WHERE user_id = ? AND item_id = ?",
            (new_count, user_id, item_id),
        )
    conn.commit()
    return True


# ════════════════════════════════════════════════════════════
# 装备
# ════════════════════════════════════════════════════════════
def get_equipped(user_id: str) -> dict[str, str]:
    conn = _get_conn()
    rows = conn.execute(
        "SELECT slot, item_id FROM equipped WHERE user_id = ?", (user_id,)
    ).fetchall()
    return {r[0]: r[1] for r in rows}


def equip_item(user_id: str, slot: str, item_id: str):
    conn = _get_conn()
    conn.execute(
        "INSERT OR REPLACE INTO equipped (user_id, slot, item_id) VALUES (?, ?, ?)",
        (user_id, slot, item_id),
    )
    conn.commit()


def unequip_item(user_id: str, slot: str):
    conn = _get_conn()
    conn.execute(
        "DELETE FROM equipped WHERE user_id = ? AND slot = ?", (user_id, slot)
    )
    conn.commit()


# ════════════════════════════════════════════════════════════
# 山海经图鉴
# ════════════════════════════════════════════════════════════
def get_bestiary(user_id: str) -> dict:
    """返回 { enemy_id: { encountered, defeated, gifted, drops_found, first_kill_at } }"""
    conn = _get_conn()
    rows = conn.execute(
        "SELECT enemy_id, encountered, defeated, gifted, drops_found, first_kill_at FROM bestiary WHERE user_id = ?",
        (user_id,),
    ).fetchall()
    result = {}
    for r in rows:
        result[r[0]] = {
            "encountered": r[1],
            "defeated": r[2],
            "gifted": r[3],
            "drops_found": json.loads(r[4]),
            "first_kill_at": r[5],
        }
    return result


def record_encounter(user_id: str, enemy_id: str):
    """记录一次遭遇"""
    conn = _get_conn()
    conn.execute(
        """INSERT INTO bestiary (user_id, enemy_id, encountered)
           VALUES (?, ?, 1)
           ON CONFLICT(user_id, enemy_id) DO UPDATE SET encountered = encountered + 1""",
        (user_id, enemy_id),
    )
    conn.commit()


def record_kill(user_id: str, enemy_id: str):
    """记录一次击杀"""
    conn = _get_conn()
    # 检查是否首杀
    row = conn.execute(
        "SELECT defeated FROM bestiary WHERE user_id = ? AND enemy_id = ?",
        (user_id, enemy_id),
    ).fetchone()
    is_first = row is None or row[0] == 0
    from datetime import datetime
    now = datetime.now().isoformat()

    if row is None:
        conn.execute(
            "INSERT INTO bestiary (user_id, enemy_id, encountered, defeated, first_kill_at) VALUES (?, ?, 1, 1, ?)",
            (user_id, enemy_id, now),
        )
    else:
        if is_first:
            conn.execute(
                "UPDATE bestiary SET defeated = defeated + 1, first_kill_at = ? WHERE user_id = ? AND enemy_id = ?",
                (now, user_id, enemy_id),
            )
        else:
            conn.execute(
                "UPDATE bestiary SET defeated = defeated + 1 WHERE user_id = ? AND enemy_id = ?",
                (user_id, enemy_id),
            )
    conn.commit()
    return is_first


def record_drop(user_id: str, enemy_id: str, item_id: str):
    """记录从某怪获得的掉落"""
    conn = _get_conn()
    row = conn.execute(
        "SELECT drops_found FROM bestiary WHERE user_id = ? AND enemy_id = ?",
        (user_id, enemy_id),
    ).fetchone()
    if row:
        drops = json.loads(row[0])
        if item_id not in drops:
            drops.append(item_id)
            conn.execute(
                "UPDATE bestiary SET drops_found = ? WHERE user_id = ? AND enemy_id = ?",
                (json.dumps(drops), user_id, enemy_id),
            )
            conn.commit()


def record_gift(user_id: str, enemy_id: str):
    """记录赠礼成功"""
    conn = _get_conn()
    conn.execute(
        """INSERT INTO bestiary (user_id, enemy_id, gifted)
           VALUES (?, ?, 1)
           ON CONFLICT(user_id, enemy_id) DO UPDATE SET gifted = gifted + 1""",
        (user_id, enemy_id),
    )
    conn.commit()


# ════════════════════════════════════════════════════════════
# 今日修行令
# ════════════════════════════════════════════════════════════
def get_daily_state(user_id: str, date: str) -> dict:
    """获取今日任务状态 {tasks_done: {task_id: count}, claimed: bool}"""
    conn = _get_conn()
    row = conn.execute(
        "SELECT tasks_done, claimed FROM daily_state WHERE user_id = ? AND date = ?",
        (user_id, date),
    ).fetchone()
    if row:
        return {"tasks_done": json.loads(row[0]), "claimed": bool(row[1])}
    return {"tasks_done": {}, "claimed": False}


def record_daily_task(user_id: str, date: str, task_id: str, count: int = 1):
    """记录今日完成某任务"""
    conn = _get_conn()
    state = get_daily_state(user_id, date)
    tasks = state["tasks_done"]
    tasks[task_id] = tasks.get(task_id, 0) + count
    conn.execute(
        """INSERT OR REPLACE INTO daily_state (user_id, date, tasks_done, claimed)
           VALUES (?, ?, ?, ?)""",
        (user_id, date, json.dumps(tasks), int(state["claimed"])),
    )
    conn.commit()


def claim_daily_reward(user_id: str, date: str) -> bool:
    """领取今日奖励,成功返回 True"""
    conn = _get_conn()
    state = get_daily_state(user_id, date)
    if state["claimed"]:
        return False
    conn.execute(
        "UPDATE daily_state SET claimed = 1 WHERE user_id = ? AND date = ?",
        (user_id, date),
    )
    conn.commit()
    return True


# ════════════════════════════════════════════════════════════
# 修行录
# ════════════════════════════════════════════════════════════
def add_journal_entry(user_id: str, entry_type: str, title: str, content: str = "", meta: dict = None) -> int:
    """添加修行录条目,返回 id"""
    conn = _get_conn()
    cur = conn.execute(
        "INSERT INTO journal (user_id, type, title, content, meta) VALUES (?, ?, ?, ?, ?)",
        (user_id, entry_type, title, content, json.dumps(meta or {}, ensure_ascii=False)),
    )
    conn.commit()
    return cur.lastrowid


def get_journal(user_id: str, limit: int = 20, offset: int = 0) -> list:
    """获取修行录列表 — 字段名按前端 Journal.vue 期望对齐"""
    conn = _get_conn()
    rows = conn.execute(
        "SELECT id, type, title, content, meta, created_at FROM journal WHERE user_id = ? ORDER BY id DESC LIMIT ? OFFSET ?",
        (user_id, limit, offset),
    ).fetchall()
    out = []
    for r in rows:
        meta = json.loads(r[4] or "{}")
        # 把 created_at 从 SQL 字符串转毫秒(前端 new Date() 用)
        ts = r[5]
        if isinstance(ts, str):
            try:
                from datetime import datetime
                ts = int(datetime.fromisoformat(ts.replace("Z", "+00:00")).timestamp() * 1000)
            except Exception:
                pass
        out.append({
            "id": r[0],
            "event_type": r[1],          # 前端字段名
            "title": r[2],
            "detail": r[3],              # 前端字段名
            "tags": meta.get("tags", []),
            "meta": meta,
            "created_at": ts,
        })
    return out


def count_journal(user_id: str) -> int:
    conn = _get_conn()
    row = conn.execute(
        "SELECT COUNT(*) FROM journal WHERE user_id = ?", (user_id,)
    ).fetchone()
    return row[0]


# ════════════════════════════════════════════════════════════
# 墨炉 / 本命书 / token ledger
# ════════════════════════════════════════════════════════════
def _json_loads(raw: str | None, default):
    if not raw:
        return default
    try:
        return json.loads(raw)
    except Exception:
        return default


def _task_from_row(r) -> dict:
    return {
        "id": r["id"],
        "user_id": r["user_id"],
        "task_type": r["task_type"],
        "source_type": r["source_type"],
        "source_id": r["source_id"],
        "status": r["status"],
        "priority": r["priority"],
        "title": r["title"],
        "prompt_payload": _json_loads(r["prompt_payload"], {}),
        "content_partial": r["content_partial"] or "",
        "estimated_tokens": r["estimated_tokens"],
        "settled_tokens": r["settled_tokens"],
        "input_tokens": r["input_tokens"],
        "output_tokens": r["output_tokens"],
        "reasoning_tokens": r["reasoning_tokens"],
        "cultivation_gained": r["cultivation_gained"],
        "model": r["model"],
        "usage_source": r["usage_source"],
        "budget_snapshot": _json_loads(r["budget_snapshot"], {}),
        "error": r["error"],
        "created_at": r["created_at"],
        "started_at": r["started_at"],
        "paused_at": r["paused_at"],
        "finished_at": r["finished_at"],
        "cancelled_at": r["cancelled_at"],
    }


def _chapter_from_row(r) -> dict:
    return {
        "id": r["id"],
        "user_id": r["user_id"],
        "chapter_no": r["chapter_no"],
        "volume_no": r["volume_no"],
        "chapter_type": r["chapter_type"],
        "title": r["title"],
        "content": r["content"],
        "summary": r["summary"],
        "status": r["status"],
        "is_partial": bool(r["is_partial"]),
        "task_id": r["task_id"],
        "source_type": r["source_type"],
        "source_id": r["source_id"],
        "battle_id": r["battle_id"],
        "enemy_id": r["enemy_id"],
        "boss_id": r["boss_id"],
        "npc_id": r["npc_id"],
        "token_count": r["token_count"],
        "input_tokens": r["input_tokens"],
        "output_tokens": r["output_tokens"],
        "reasoning_tokens": r["reasoning_tokens"],
        "cultivation_gained": r["cultivation_gained"],
        "model": r["model"],
        "usage_source": r["usage_source"],
        "word_count": r["word_count"],
        "created_at": r["created_at"],
        "completed_at": r["completed_at"],
    }


def create_cultivation_task(
    user_id: str,
    task_type: str,
    title: str,
    prompt_payload: dict | None = None,
    source_type: str = "",
    source_id: str = "",
    priority: int = 0,
    model: str = "",
) -> dict:
    conn = _get_conn()
    task_id = f"cult_{uuid.uuid4().hex[:16]}"
    conn.execute(
        """INSERT INTO cultivation_tasks
           (id, user_id, task_type, source_type, source_id, status, priority, title,
            prompt_payload, model)
           VALUES (?, ?, ?, ?, ?, 'queued', ?, ?, ?, ?)""",
        (
            task_id, user_id, task_type, source_type, source_id, priority, title,
            json.dumps(prompt_payload or {}, ensure_ascii=False), model,
        ),
    )
    conn.commit()
    return get_cultivation_task(task_id)


def get_cultivation_task(task_id: str) -> Optional[dict]:
    conn = _get_conn()
    row = conn.execute(
        "SELECT * FROM cultivation_tasks WHERE id = ?", (task_id,)
    ).fetchone()
    return _task_from_row(row) if row else None


def get_next_queued_task(user_id: str) -> Optional[dict]:
    conn = _get_conn()
    row = conn.execute(
        """SELECT * FROM cultivation_tasks
           WHERE user_id = ? AND status = 'queued'
           ORDER BY priority DESC, created_at ASC
           LIMIT 1""",
        (user_id,),
    ).fetchone()
    return _task_from_row(row) if row else None


def list_cultivation_tasks(user_id: str, include_done: bool = False, limit: int = 30) -> list:
    conn = _get_conn()
    if include_done:
        rows = conn.execute(
            "SELECT * FROM cultivation_tasks WHERE user_id = ? ORDER BY created_at DESC LIMIT ?",
            (user_id, limit),
        ).fetchall()
    else:
        rows = conn.execute(
            """SELECT * FROM cultivation_tasks
               WHERE user_id = ? AND status IN ('queued','running','paused','budget_blocked')
               ORDER BY CASE status WHEN 'running' THEN 0 WHEN 'budget_blocked' THEN 1
                         WHEN 'paused' THEN 2 WHEN 'queued' THEN 3 ELSE 4 END,
                        priority DESC, created_at ASC
               LIMIT ?""",
            (user_id, limit),
        ).fetchall()
    return [_task_from_row(r) for r in rows]


def list_pending_cultivation_user_ids() -> list[str]:
    conn = _get_conn()
    rows = conn.execute(
        """SELECT DISTINCT user_id FROM cultivation_tasks
           WHERE status IN ('queued','running')"""
    ).fetchall()
    return [r[0] for r in rows]


def reset_interrupted_cultivation_tasks() -> int:
    """进程重启后,把可恢复任务放回 queued,等待墨炉恢复。"""
    conn = _get_conn()
    cur = conn.execute(
        """UPDATE cultivation_tasks
           SET status = 'queued', error = NULL, paused_at = NULL
           WHERE status IN ('running', 'budget_blocked')"""
    )
    conn.commit()
    return cur.rowcount


def update_cultivation_task(task_id: str, **fields) -> Optional[dict]:
    if not fields:
        return get_cultivation_task(task_id)
    allowed = {
        "status", "priority", "title", "prompt_payload", "content_partial",
        "estimated_tokens", "settled_tokens", "input_tokens", "output_tokens",
        "reasoning_tokens", "cultivation_gained", "model", "usage_source",
        "budget_snapshot", "error", "started_at", "paused_at", "finished_at",
        "cancelled_at",
    }
    sets = []
    values = []
    for k, v in fields.items():
        if k not in allowed:
            continue
        if k in ("prompt_payload", "budget_snapshot") and not isinstance(v, str):
            v = json.dumps(v or {}, ensure_ascii=False)
        sets.append(f"{k} = ?")
        values.append(v)
    if not sets:
        return get_cultivation_task(task_id)
    values.append(task_id)
    conn = _get_conn()
    conn.execute(f"UPDATE cultivation_tasks SET {', '.join(sets)} WHERE id = ?", values)
    conn.commit()
    return get_cultivation_task(task_id)


def append_task_content(
    task_id: str,
    content_delta: str,
    output_tokens_delta: int = 0,
    cultivation_delta: int = 0,
) -> Optional[dict]:
    conn = _get_conn()
    conn.execute(
        """UPDATE cultivation_tasks
           SET content_partial = content_partial || ?,
               output_tokens = output_tokens + ?,
               estimated_tokens = estimated_tokens + ?,
               cultivation_gained = cultivation_gained + ?
           WHERE id = ?""",
        (content_delta, output_tokens_delta, output_tokens_delta, cultivation_delta, task_id),
    )
    conn.commit()
    return get_cultivation_task(task_id)


def add_task_input_tokens(task_id: str, input_tokens_delta: int) -> Optional[dict]:
    conn = _get_conn()
    conn.execute(
        """UPDATE cultivation_tasks
           SET input_tokens = input_tokens + ?,
               estimated_tokens = estimated_tokens + ?,
               cultivation_gained = cultivation_gained + ?
           WHERE id = ?""",
        (input_tokens_delta, input_tokens_delta, input_tokens_delta, task_id),
    )
    conn.commit()
    return get_cultivation_task(task_id)


def add_token_ledger(
    user_id: str,
    source: str,
    delta_tokens: int,
    task_id: str = "",
    chapter_id: int | None = None,
    input_tokens: int = 0,
    output_tokens: int = 0,
    reasoning_tokens: int = 0,
    usage_source: str = "estimated",
    provider: str = "",
    model: str = "",
) -> int:
    conn = _get_conn()
    cur = conn.execute(
        """INSERT INTO token_ledger
           (user_id, task_id, chapter_id, source, delta_tokens, input_tokens,
            output_tokens, reasoning_tokens, usage_source, provider, model)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (
            user_id, task_id or None, chapter_id, source, delta_tokens,
            input_tokens, output_tokens, reasoning_tokens, usage_source, provider, model,
        ),
    )
    conn.commit()
    return cur.lastrowid


def create_novel_chapter(
    user_id: str,
    chapter_type: str,
    title: str,
    content: str,
    task_id: str = "",
    source_type: str = "",
    source_id: str = "",
    battle_id: str = "",
    enemy_id: str = "",
    boss_id: str = "",
    npc_id: str = "",
    token_count: int = 0,
    input_tokens: int = 0,
    output_tokens: int = 0,
    reasoning_tokens: int = 0,
    cultivation_gained: int = 0,
    model: str = "",
    usage_source: str = "estimated",
    is_partial: bool = False,
    summary: str = "",
) -> dict:
    conn = _get_conn()
    row = conn.execute(
        "SELECT COALESCE(MAX(chapter_no), 0) FROM novel_chapters WHERE user_id = ?",
        (user_id,),
    ).fetchone()
    chapter_no = int(row[0] or 0) + 1
    volume_no = ((chapter_no - 1) // 20) + 1
    clean_content = content or ""
    word_count = len(clean_content)
    summary = summary or clean_content[:180]
    cur = conn.execute(
        """INSERT INTO novel_chapters
           (user_id, chapter_no, volume_no, chapter_type, title, content, summary,
            status, is_partial, task_id, source_type, source_id, battle_id, enemy_id,
            boss_id, npc_id, token_count, input_tokens, output_tokens, reasoning_tokens,
            cultivation_gained, model, usage_source, word_count, completed_at)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, datetime('now'))""",
        (
            user_id, chapter_no, volume_no, chapter_type, title, clean_content, summary,
            "partial" if is_partial else "completed", int(is_partial), task_id or None,
            source_type or None, source_id or None, battle_id or None, enemy_id or None,
            boss_id or None, npc_id or None, token_count, input_tokens, output_tokens,
            reasoning_tokens, cultivation_gained, model, usage_source, word_count,
        ),
    )
    conn.commit()
    return get_novel_chapter(user_id, cur.lastrowid)


def get_novel_chapter(user_id: str, chapter_id: int) -> Optional[dict]:
    conn = _get_conn()
    row = conn.execute(
        "SELECT * FROM novel_chapters WHERE user_id = ? AND id = ?",
        (user_id, chapter_id),
    ).fetchone()
    return _chapter_from_row(row) if row else None


def list_novel_chapters(user_id: str, limit: int = 30, offset: int = 0) -> list:
    conn = _get_conn()
    rows = conn.execute(
        """SELECT * FROM novel_chapters
           WHERE user_id = ?
           ORDER BY chapter_no DESC
           LIMIT ? OFFSET ?""",
        (user_id, limit, offset),
    ).fetchall()
    return [_chapter_from_row(r) for r in rows]


def get_novel_stats(user_id: str) -> dict:
    conn = _get_conn()
    row = conn.execute(
        """SELECT COUNT(*), COALESCE(MAX(volume_no), 0), COALESCE(SUM(token_count), 0),
                  COALESCE(SUM(word_count), 0), COALESCE(SUM(cultivation_gained), 0)
           FROM novel_chapters WHERE user_id = ?""",
        (user_id,),
    ).fetchone()
    latest = conn.execute(
        """SELECT * FROM novel_chapters WHERE user_id = ?
           ORDER BY chapter_no DESC LIMIT 1""",
        (user_id,),
    ).fetchone()
    running = conn.execute(
        """SELECT COUNT(*) FROM cultivation_tasks
           WHERE user_id = ? AND status IN ('queued','running','paused','budget_blocked')""",
        (user_id,),
    ).fetchone()
    return {
        "chapters_count": int(row[0] or 0),
        "current_volume": int(row[1] or 0),
        "token_total": int(row[2] or 0),
        "word_total": int(row[3] or 0),
        "cultivation_total_from_chapters": int(row[4] or 0),
        "active_tasks": int(running[0] or 0),
        "latest_chapter": _chapter_from_row(latest) if latest else None,
    }


def list_novel_volumes(user_id: str) -> list[dict]:
    conn = _get_conn()
    rows = conn.execute(
        """SELECT volume_no, COUNT(*), COALESCE(SUM(token_count), 0),
                  COALESCE(SUM(word_count), 0), MIN(chapter_no), MAX(chapter_no)
           FROM novel_chapters
           WHERE user_id = ?
           GROUP BY volume_no
           ORDER BY volume_no DESC""",
        (user_id,),
    ).fetchall()
    return [
        {
            "volume_no": r[0],
            "title": f"第 {r[0]} 卷",
            "chapters_count": r[1],
            "token_count": r[2],
            "word_count": r[3],
            "chapter_start": r[4],
            "chapter_end": r[5],
        }
        for r in rows
    ]
