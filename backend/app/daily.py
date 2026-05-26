"""今日修行令 — 每日 5 个目标,完成 4 个领奖

设计:
- 5 种行为各计 1 次即完成
- 完成 4/5 可领取日奖励(灵气尘+宗门贡献;修为只来自燃灵)
- 不强制全做,让玩家选喜欢的
- 每日 UTC+8 0 点重置
"""

from datetime import datetime, timezone, timedelta
from typing import Dict, List, Tuple

# ════════════════════════════════════════════════════════════
# 修行令定义
# ════════════════════════════════════════════════════════════
DAILY_TASKS = [
    {
        "id": "battle",
        "name": "斩妖除魔",
        "desc": "击败任意怪物 1 次",
        "icon": "⚔️",
        "target": 1,
    },
    {
        "id": "meditate",
        "name": "吐纳调息",
        "desc": "完成一次打坐",
        "icon": "🧘",
        "target": 1,
    },
    {
        "id": "fortune",
        "name": "机缘际遇",
        "desc": "触发或处理一次奇遇",
        "icon": "🍀",
        "target": 1,
    },
    {
        "id": "gift",
        "name": "以礼化敌",
        "desc": "成功赠送一次物品",
        "icon": "🎁",
        "target": 1,
    },
    {
        "id": "craft",
        "name": "炼丹修器",
        "desc": "合成或使用一个物品",
        "icon": "🔥",
        "target": 1,
    },
]

REQUIRED_COUNT = 4  # 完成 4/5 即可领奖

# 日奖励
DAILY_REWARD = {
    "exp": 0,
    "items": [("item_qi_dust", 3)],  # 灵气尘 ×3
    "faction_rep": 10,  # 宗门贡献
}

# UTC+8 时区
_TZ_CN = timezone(timedelta(hours=8))


def get_today() -> str:
    """返回今日日期字符串(UTC+8)"""
    return datetime.now(_TZ_CN).strftime("%Y-%m-%d")


def get_daily_status(tasks_done: dict) -> List[Dict]:
    """根据完成情况返回今日任务状态列表"""
    result = []
    for task in DAILY_TASKS:
        done_count = tasks_done.get(task["id"], 0)
        result.append({
            **task,
            "done": done_count,
            "completed": done_count >= task["target"],
        })
    return result


def count_completed(tasks_done: dict) -> int:
    """统计已完成的任务数"""
    count = 0
    for task in DAILY_TASKS:
        if tasks_done.get(task["id"], 0) >= task["target"]:
            count += 1
    return count


def can_claim(tasks_done: dict) -> bool:
    """是否满足领奖条件"""
    return count_completed(tasks_done) >= REQUIRED_COUNT


def get_reward_preview() -> Dict:
    """返回奖励预览"""
    return {
        "exp": DAILY_REWARD["exp"],
        "items": DAILY_REWARD["items"],
        "faction_rep": DAILY_REWARD["faction_rep"],
        "required": REQUIRED_COUNT,
        "total": len(DAILY_TASKS),
    }
