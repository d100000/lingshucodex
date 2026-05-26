"""战斗引擎 v2 — 数值/叙事解耦 + 事件队列架构

核心变化(vs v1):
1. process_action() 拆成 cast(card_id) 异步推事件 + events() 主消费 generator
2. 数值结算立即推(<100ms),LLM 叙事 fire-and-forget 后台 task
3. mode = "drama" / "speed":speed 完全不调 LLM,极快节奏
4. LLM 模型由角色门派 + 等级阶段决定
5. 双方动作合并到 1 次 LLM 调用(原本 2 次,减半等待)
6. 预生成池:进战时后台 Haiku 生 3 段普攻叙事备用
7. skip 支持:cancel 当前叙事 task,释放下一回合
8. 战后章节:end 后异步 Opus 写 500 字回顾
"""

import asyncio
import random
import time
import uuid
from typing import Optional, List
from .sects import get_sect, get_tier_for_level, get_destiny_skill
from .enemies import get_enemy, enemy_to_dict
from .cards import get_card
from .items import get_item, item_to_dict
from .monster_skills import pick_skill_for_enemy
from .bosses import boss_to_dict
from .drop_rules import is_skill_drop_item, skill_drop_rate_for_enemy
from .combat_balance import (
    balanced_enemy_stats,
    combat_damage,
    combat_hit_rate,
    expected_combat_damage,
)
from .fatigue import add_battle_fatigue
from .llm_client import (
    build_combined_user_prompt,
    stream_combined_narration,
    stream_chapter_narration,
    prefetch_pool_narrations,
    pick_narration_model,
)
from .store import add_item, get_character, save_character

REALM_DISPLAY = {
    "qi": "炼气期", "foundation": "筑基期", "golden": "金丹期",
    "yuanying": "元婴期", "huashen": "化神期", "hetishi": "合体期",
    "dacheng": "大乘期", "dujie": "渡劫期", "feisheng": "飞升期",
}


class BattleEngine:
    """单场战斗(内存版) — 事件队列驱动"""

    def __init__(self, character: dict, enemy_id: str, mode: str = "drama", tutorial: bool = False,
                 user_id: str = "demo_player"):
        sect = get_sect(character["sect"])
        if not sect or not sect.available:
            raise ValueError(f"门派 {character['sect']} 暂未开放")

        enemy = get_enemy(enemy_id)
        if not enemy:
            raise ValueError(f"敌人 {enemy_id} 不存在")

        tier = get_tier_for_level(character["sect"], character.get("level", 1))

        self.sect = sect
        self.tier = tier
        self.user_id = user_id   # ★ Phase C: 多用户隔离
        self.battle_id = f"btl_{uuid.uuid4().hex[:12]}"
        self.api_key = character.get("api_key") or None
        self.base_url = character.get("base_url") or None
        # ★ 战斗/本命书模型:门派 + 等级阶段。
        self.narration_model = tier.model if tier else (sect.tiers[-1].model if sect.tiers else "")
        self.narration_api_key = self.api_key
        self.narration_base_url = self.base_url
        # ★ 战斗模式
        self.mode = mode if mode in ("drama", "speed") else "drama"
        # ★ 教学模式
        self.tutorial = tutorial
        self._tutorial_cast_count = 0  # 跟踪教学中的出招次数
        self.learned_levels = {}
        for item in character.get("learned_skills", []):
            skill_id = item.get("skill_id")
            if not skill_id:
                continue
            try:
                level = int(item.get("level", 1) or 1)
            except (TypeError, ValueError):
                level = 1
            self.learned_levels[skill_id] = max(1, level)

        # ★ 图鉴:记录遭遇
        from .store import record_encounter
        record_encounter(self.user_id, enemy.id)

        # ★ 事件队列 — 所有 push 进来,events() 消费给 WS
        self.events_queue: asyncio.Queue = asyncio.Queue()
        # ★ 当前正在跑的叙事 task(可被 cancel)
        self.current_narration_task: Optional[asyncio.Task] = None
        # ★ 预生成的普攻叙事池(用 Haiku)
        self.narration_pool: List[str] = []
        # ★ 回合历史(战后章节用)
        self.history: List[dict] = []
        # ★ 异步生成的"章节"task
        self.chapter_task: Optional[asyncio.Task] = None
        # ★ Phase 1: 行动锁(串行化 cast/use_item/flee) + commit 幂等标记
        self._action_lock = asyncio.Lock()
        self._committed = False
        # ★ Phase 4: 后台 task 集合 + WS 单连接保护
        self._bg_tasks: set = set()
        self.ws_attached: bool = False
        # ★ Phase 3: 服务端记的赠礼次数(替代信任前端)
        self.gift_count = 0

        enemy_stats = balanced_enemy_stats(enemy, character)

        self.state = {
            "battle_id": self.battle_id,
            "user_id": self.user_id,
            "round": 0,
            "status": "player_turn",
            "result": None,
            "buffs": {"focus_next": False},
            "destiny_charged": False,
            "destiny_used": False,
            "mode": self.mode,

            # 玩家
            "sect_id": sect.id,
            "sect_name": sect.name,
            "realm": character.get("realm", "qi"),
            "realm_name": REALM_DISPLAY.get(character.get("realm", "qi"), "炼气期"),
            "model": tier.model if tier else "claude-haiku-4-5-20251001",
            "narration_max_tokens": tier.max_tokens if tier else 200,
            "atk_mult": tier.atk_multiplier if tier else 1.0,
            "player_hp": character.get("hp", sect.initial_stats["hp"]),
            "player_max_hp": character.get("max_hp", sect.initial_stats["hp"]),
            "player_atk": int(character.get("atk", sect.initial_stats["atk"]) * (tier.atk_multiplier if tier else 1.0)),
            "player_def": character.get("def_", sect.initial_stats["def_"]),
            "player_spd": character.get("spd", sect.initial_stats["spd"]),
            "player_crit": character.get("crit_rate", sect.initial_stats["crit_rate"]),
            "player_crit_dmg": character.get("crit_dmg", sect.initial_stats["crit_dmg"]),
            "player_evasion": character.get("evasion", sect.initial_stats["evasion"]),
            "player_qi": character.get("qi", sect.initial_stats["qi"]),
            "player_max_qi": character.get("max_qi", sect.initial_stats["qi"]),

            # 敌人 — 由统一战斗平衡模块生成最终数值,避免静态表值重复乘等级倍率。
            "enemy_id": enemy.id,
            "enemy_name": enemy.name,
            "enemy_clan": enemy.clan,
            "enemy_level": enemy.level,
            "enemy_emoji": enemy.image_emoji,
            "enemy_image_url": getattr(enemy, 'image_url', ''),
            "enemy_is_npc": bool(getattr(enemy, 'is_npc', False)),
            "enemy_sect_id": getattr(enemy, 'sect_id', ''),
            "enemy_sect_name": getattr(enemy, 'sect_name', ''),
            "enemy_rank": getattr(enemy, 'rank', ''),
            "enemy_portrait_kind": getattr(enemy, 'portrait_kind', ''),
            "enemy_portrait_id": getattr(enemy, 'portrait_id', ''),
            "enemy_balance_profile": enemy_stats["profile"],
            "enemy_hp": enemy_stats["hp"],
            "enemy_max_hp": enemy_stats["max_hp"],
            "enemy_atk": enemy_stats["atk"],
            "enemy_def": enemy_stats["def_"],
            "enemy_spd": enemy_stats["spd"],
            "enemy_evasion": enemy_stats["evasion"],
            "enemy_rewards_exp": enemy_stats["rewards_exp"],
            "enemy_rewards_qi": enemy_stats["rewards_qi"],
        }

    # ================================================================
    # 快照
    # ================================================================
    def snapshot(self) -> dict:
        s = self.state
        enemy_meta = {}
        enemy_obj = get_enemy(s["enemy_id"])
        if enemy_obj:
            try:
                if hasattr(enemy_obj, "description"):
                    enemy_meta = enemy_to_dict(enemy_obj)
                else:
                    enemy_meta = boss_to_dict(enemy_obj)
            except Exception:
                enemy_meta = {}
        enemy_snap = {
            "id": s["enemy_id"],
            "name": s["enemy_name"],
            "clan": s.get("enemy_clan"),
            "level": s.get("enemy_level"),
            "emoji": s["enemy_emoji"],
            "image_emoji": s["enemy_emoji"],
            "image_url": s.get("enemy_image_url", ""),
            "hp": s["enemy_hp"],
            "max_hp": s["enemy_max_hp"],
            "atk": s.get("enemy_atk"),
            "def_": s.get("enemy_def"),
            "spd": s.get("enemy_spd"),
            "evasion": s.get("enemy_evasion"),
        }
        for key, value in enemy_meta.items():
            if key not in {"hp", "max_hp", "atk", "def_", "spd", "evasion"}:
                enemy_snap[key] = value
        if s.get("enemy_is_npc") or s.get("is_npc_battle"):
            enemy_snap.update({
                "is_npc": True,
                "sect_id": s.get("enemy_sect_id") or s.get("npc_sect") or enemy_snap.get("sect_id", ""),
                "sect_name": s.get("enemy_sect_name") or enemy_snap.get("sect_name", ""),
                "rank": s.get("enemy_rank") or s.get("npc_rank") or enemy_snap.get("rank", ""),
                "portrait_kind": s.get("enemy_portrait_kind") or enemy_snap.get("portrait_kind", "player"),
                "portrait_id": s.get("enemy_portrait_id") or enemy_snap.get("portrait_id", ""),
            })
        snap = {
            "battle_id": s["battle_id"],
            "round": s["round"],
            "status": s["status"],
            "result": s["result"],
            "mode": s["mode"],
            "tutorial": self.tutorial,
            "destiny_charged": s.get("destiny_charged", False),
            "destiny_used": s.get("destiny_used", False),
            "player": {
                "sect_id": s["sect_id"],
                "sect_name": s["sect_name"],
                "realm_name": s["realm_name"],
                "model": s["model"],
                "hp": s["player_hp"],
                "max_hp": s["player_max_hp"],
                "qi": s["player_qi"],
                "max_qi": s["player_max_qi"],
                "atk": s["player_atk"],
            },
            "enemy": enemy_snap,
        }
        destiny = get_destiny_skill(s["sect_id"])
        if destiny:
            snap["destiny_skill"] = destiny
        return snap

    def is_finished(self) -> bool:
        return self.state["status"] == "ended"

    def _active_buff(self, key: str, default=0):
        return self.state.setdefault("buffs", {}).get(key, default)

    def _consume_attack_buffs(self):
        buffs = self.state.setdefault("buffs", {})
        for key in ("focus_next", "crit_next_bonus", "crit_dmg_next_bonus", "hit_floor_next", "hit_bonus_next"):
            if key in buffs:
                buffs.pop(key, None)

    def _tick_player_buffs(self):
        buffs = self.state.setdefault("buffs", {})
        for key in ("defense_turns", "evasion_turns", "no_crit_turns", "def_mult_turns"):
            if buffs.get(key, 0) > 0:
                buffs[key] -= 1
            if buffs.get(key, 0) <= 0:
                buffs.pop(key, None)
                paired = {
                    "defense_turns": "damage_reduction",
                    "evasion_turns": "evasion_bonus",
                    "no_crit_turns": "no_crit",
                    "def_mult_turns": "def_mult",
                }.get(key)
                if paired:
                    buffs.pop(paired, None)

    def _pressure_mult(self) -> float:
        """Long fights reveal flaws so battle keeps visibly progressing."""
        if self.state.get("round", 0) < 8:
            return 1.0
        return min(1.8, 1.0 + (self.state["round"] - 7) * 0.08)

    def _get_player_card(self, card_id: str):
        card = get_card(card_id)
        try:
            from .skill_templates import (
                effective_battle_qi_cost,
                get_skill,
                effective_crit_bonus,
                effective_power,
            )
            tpl = get_skill(card_id)
            if tpl:
                level = max(1, min(tpl.max_level, int(self.learned_levels.get(card_id, 1) or 1)))
                return type("BattleCard", (), {
                    "id": tpl.id,
                    "name": tpl.name,
                    "sect_requirement": tpl.sect,
                    "type": tpl.type,
                    "qi_cost": effective_battle_qi_cost(tpl, level, self.state.get("player_max_qi", 600)),
                    "power": effective_power(tpl, level),
                    "hit_rate": tpl.hit_rate,
                    "crit_bonus": effective_crit_bonus(tpl, level),
                    "description": tpl.description,
                    "icon": tpl.icon,
                    "level": level,
                    "tier": tpl.tier,
                })()
        except Exception:
            pass
        return card

    def preview_card(self, card) -> dict:
        s = self.state
        qi_cost = int(getattr(card, "qi_cost", 0) or 0)
        if card.type == "attack":
            atk = s["player_atk"]
            if s["buffs"].get("focus_next"):
                atk = int(atk * 1.5)
            crit_rate = min(0.95, s["player_crit"] + float(getattr(card, "crit_bonus", 0) or 0))
            return {
                "card_id": card.id,
                "type": "attack",
                "estimated_damage": expected_combat_damage(
                    atk, s["enemy_def"], card.power, crit_rate, s["player_crit_dmg"]
                ),
                "crit_damage": combat_damage(
                    atk, s["enemy_def"], card.power, True, s["player_crit_dmg"], 1.0
                ),
                "hit_rate": combat_hit_rate(card.hit_rate, s["enemy_evasion"]),
                "crit_rate": round(crit_rate, 3),
                "qi_cost": qi_cost,
                "qi_after": max(0, s.get("player_qi", 0) - qi_cost),
            }
        if card.type == "heal":
            return {
                "card_id": card.id,
                "type": "heal",
                "estimated_heal": int(s.get("player_max_hp", 100) * 0.3),
                "hit_rate": 1.0,
                "crit_rate": 0,
                "qi_cost": qi_cost,
                "qi_after": max(0, s.get("player_qi", 0) - qi_cost),
            }
        return {
            "card_id": card.id,
            "type": card.type,
            "hit_rate": 1.0,
            "crit_rate": 0,
            "qi_cost": qi_cost,
            "qi_after": max(0, s.get("player_qi", 0) - qi_cost),
            "note": {
                "focus": "下一击伤害 +50%",
                "canglan_intent": "下一击暴击率 +30%,暴击伤害 +20%",
                "body_guard": "3 回合受到伤害 -25%",
                "swift_wind": "3 回合闪避 +8%,下一击命中 +8%",
                "tianji_calc": "下一击命中下限提升至 85%",
                "qingming_root": "本战生命上限 +15% 并恢复对应气血",
                "qingming_classic": "3 回合防御 +25%",
                "yueyin_swift": "3 回合闪避 +10%",
                "yueyin_hide": "2 回合不会被暴击",
            }.get(card.id, "增益效果"),
        }

    # ================================================================
    # 事件总线
    # ================================================================
    async def events(self):
        """主消费 generator — WS handler 从这里拉事件"""
        chapter_grace_until = None  # end 后给章节流一段宽限期
        while True:
            try:
                event = await asyncio.wait_for(
                    self.events_queue.get(), timeout=0.3
                )
                yield event
                if event.get("type") == "end":
                    # speed 模式没有章节 task,直接退出
                    if self.mode == "speed" or self.chapter_task is None:
                        # 给 0.5s 让可能的尾部事件落地
                        chapter_grace_until = time.time() + 0.5
                    else:
                        # 给章节 stream 最多 60s 时间出完
                        chapter_grace_until = time.time() + 60
                if event.get("type") == "chapter_end":
                    return  # 章节结束才真正退出
            except asyncio.TimeoutError:
                if chapter_grace_until and time.time() > chapter_grace_until:
                    return
                if self.is_finished() and chapter_grace_until is None:
                    # 没启动章节就结束
                    return
                continue

    async def _push(self, event: dict):
        await self.events_queue.put(event)

    # ================================================================
    # 玩家出招(主入口 — 异步,立即推数值,fire-and-forget LLM)
    # ================================================================
    async def cast(self, card_id: str):
        """玩家出牌 — 用 action_lock 串行化,严格校验回合状态"""
        async with self._action_lock:
            await self._cast_locked(card_id)

    async def _cast_locked(self, card_id: str):
        """实际出牌逻辑(已持锁)"""
        if self.is_finished():
            await self._push({"type": "error", "data": {"message": "战斗已结束"}})
            return

        # ★ Phase 1: 回合校验 — 只能在 player_turn 状态出招,防止脚本/多连接绕过
        if self.state.get("status") != "player_turn":
            await self._push({"type": "error", "data": {
                "message": f"尚未轮到你出手(当前状态: {self.state.get('status')})",
            }})
            return

        # === 卡牌 / 天命 校验 ===
        is_destiny = card_id.startswith("destiny_")
        if is_destiny:
            destiny = get_destiny_skill(self.state["sect_id"])
            if not destiny or destiny["id"] != card_id:
                await self._push({"type": "error", "data": {"message": "此天命非汝之天命"}})
                return
            if not self.state["destiny_charged"] or self.state["destiny_used"]:
                await self._push({"type": "error", "data": {"message": "天命尚未降临"}})
                return
            card = type("DestinyCard", (), {
                "id": destiny["id"], "name": destiny["name"],
                "icon": destiny["icon"], "qi_cost": 0,
                "power": destiny["power"], "hit_rate": destiny["hit_rate"],
                "crit_bonus": 0,
                "type": "attack",
                "sect_requirement": self.state["sect_id"],
                "description": destiny["description"],
            })()
            self.state["destiny_used"] = True
            self.state["destiny_charged"] = False
        else:
            card = self._get_player_card(card_id)
            if not card:
                await self._push({"type": "error", "data": {"message": "卡牌不存在"}})
                return
            if card.sect_requirement != "any" and card.sect_requirement != self.state["sect_id"]:
                await self._push({"type": "error", "data": {"message": "此招式不属于你的门派"}})
                return
            if self.state["player_qi"] < card.qi_cost:
                await self._push({"type": "error", "data": {"message": f"灵气不足(需 {card.qi_cost}, 余 {self.state['player_qi']})"}})
                return

        # === 进入处理 ===
        self.state["round"] += 1
        self.state["status"] = "processing"
        self.state["player_qi"] -= card.qi_cost

        # === 1. 玩家数值结算 ===
        my_outcome = (self._compute_destiny_outcome(card) if is_destiny
                      else self._compute_outcome(card))
        self._apply_outcome(my_outcome, card)

        await self._push({"type": "action_resolved", "data": {
            "card": {"id": card.id, "name": card.name, "icon": getattr(card, "icon", "⚔️")},
            "round": self.state["round"],
            "outcome": my_outcome,
        }})

        # ★ 教学模式:第一次成功出招后推叙事提示
        if self.tutorial:
            self._tutorial_cast_count += 1
            if self._tutorial_cast_count == 1 and my_outcome["type"] not in ("miss",):
                await self._push({"type": "tutorial_hint", "data": {
                    "step": "narration",
                    "message": "AI 正在为这一击撰写叙事。你可以点击「跳过」按钮加速。",
                }})

        if my_outcome["damage"] > 0:
            await self._push({"type": "damage", "data": {
                "target": "enemy",
                "amount": my_outcome["damage"],
                "is_crit": my_outcome["is_crit"],
            }})
            await self._push({"type": "effect", "data": {
                "fx": "screen_shake",
                "intensity": 12 if my_outcome["is_crit"] else 6,
            }})
            if my_outcome["is_crit"]:
                await self._push({"type": "effect", "data": {"fx": "flash", "color": "#FFD700"}})
        await self._push({"type": "damage_summary", "data": self._build_summary(
            "player", card.name, my_outcome, is_destiny, getattr(card, "icon", "⚔️"),
        )})

        # === 2. 检查 enemy 是否死 ===
        # ★ Round 2: 友好切磋模式 — 任一方 HP ≤ 1 即停(玩家胜判)
        if self.state.get("friendly") and (self.state["enemy_hp"] <= 1 or self.state["player_hp"] <= 1):
            # 强制 enemy_hp 归 1 触发下方胜利路径(简化:总是玩家胜,但奖励减半 + 友好度 +3)
            self.state["enemy_hp"] = max(1, self.state["enemy_hp"])
            self.state["player_hp"] = max(1, self.state["player_hp"])
            if self.state["player_hp"] <= 1:
                # 玩家先到 1 → 切磋认输,但不掉血
                self.state["status"] = "ended"
                self.state["result"] = "spar_loss"
                await self._push({"type": "state", "data": self.snapshot()})
                # 写 journal
                npc_sect = self.state.get("npc_sect", "")
                _enemy_name = self.state.get("enemy_name", "对方")
                self._spar_commit("loss", npc_sect)
                await self._push({"type": "end", "data": {
                    "result": "spar_loss",
                    "narrative": f"{_enemy_name}手下留情,你拱手致谢。承让!",
                }})
                return
            # 否则 enemy 先到 1 → 玩家胜
            self.state["status"] = "ended"
            self.state["result"] = "spar_win"
            npc_sect = self.state.get("npc_sect", "")
            commit = self._spar_commit("win", npc_sect)
            await self._push({"type": "state", "data": self.snapshot()})
            await self._push({"type": "end", "data": {
                "result": "spar_win",
                "narrative": f"{self.state.get('enemy_name','对方')}抱拳:「承让!」",
                "rewards": commit,
            }})
            return

        if self.state["enemy_hp"] <= 0:
            self.state["status"] = "ended"
            self.state["result"] = "victory"
            await self._push({"type": "state", "data": self.snapshot()})

            if self.mode != "speed":
                self._start_narration(card, my_outcome, None, None, is_destiny)

            drops = self._roll_drops()
            reward_data = {
                "exp": 0,
                "legacy_exp": self.state["enemy_rewards_exp"],
                "qi": self.state["enemy_rewards_qi"],
                "drops": drops,
            }
            self.history.append({
                "round": self.state["round"],
                "player_action": {"name": card.name, "outcome": my_outcome},
                "enemy_action": None,
            })

            # ★ Phase 2: 统一提交(同步 HP/Qi + 加奖励 + 升级 + 写历史)
            commit = self._commit_battle_result("victory", rewards=reward_data, drops=drops)
            if commit.get("level_up"):
                reward_data["level_up"] = commit["level_up"]
                await self._push({"type": "level_up", "data": commit["level_up"]})

            # 升级后状态变了,推一次 snapshot 让前端看到满血
            await self._push({"type": "state", "data": self.snapshot()})

            # ★ 图鉴 + 日课:记录击杀 + 掉落 + 今日战斗
            from .store import record_kill, record_drop, record_daily_task
            from .daily import get_today
            enemy_id = self.state.get("enemy_id", "")
            user_id = self.state.get("user_id", self.user_id)
            record_kill(user_id, enemy_id)
            for drop in drops:
                if isinstance(drop, dict):
                    record_drop(user_id, enemy_id, drop.get("id", ""))
                elif isinstance(drop, str):
                    record_drop(user_id, enemy_id, drop)
            record_daily_task(user_id, get_today(), "battle")

            # ★ 教学模式:胜利提示
            if self.tutorial:
                await self._push({"type": "tutorial_hint", "data": {
                    "step": "victory",
                    "message": "恭喜!战斗中消耗的灵气会在回城后恢复。继续修行吧!",
                }})

            await self._push({"type": "end", "data": {
                "result": "victory",
                "rewards": reward_data,
                "commit": commit,
            }})
            if self.mode != "speed":
                self._start_narration(card, my_outcome, None, None, is_destiny)
            return

        # === 3. 敌人回合 ===
        self.state["status"] = "enemy_turn"
        enemy_skill = pick_skill_for_enemy(self.state["enemy_clan"], self.state["enemy_level"])
        enemy_outcome = self._compute_enemy_action(enemy_skill)
        self._apply_enemy_outcome(enemy_outcome)

        await self._push({"type": "enemy_action", "data": {
            "round": self.state["round"],
            "skill_name": enemy_skill.name if enemy_skill else "扑击",
            "skill_tier": enemy_skill.tier if enemy_skill else "basic",
            "outcome": enemy_outcome,
        }})
        if enemy_outcome["damage"] > 0:
            await self._push({"type": "damage", "data": {
                "target": "player",
                "amount": enemy_outcome["damage"],
                "is_crit": enemy_outcome.get("is_crit", False),
            }})
            await self._push({"type": "effect", "data": {
                "fx": "screen_shake",
                "intensity": 8 + (4 if enemy_outcome.get("is_crit") else 0),
            }})
        await self._push({"type": "damage_summary", "data": self._build_summary(
            "enemy", enemy_skill.name if enemy_skill else "扑击", enemy_outcome, False,
            self.state.get("enemy_emoji", "👹"),
            tier=enemy_skill.tier if enemy_skill else "basic",
        )})

        # === 4. 检查 player 是否死 ===
        if self.state["player_hp"] <= 0:
            self.state["status"] = "ended"
            self.state["result"] = "defeat"
            self.state["player_hp"] = 1  # 残血保底

            # ★ 墨炉方案:战败只同步 HP,修为由败笔章 token 结算
            self.history.append({
                "round": self.state["round"],
                "player_action": {"name": card.name, "outcome": my_outcome},
                "enemy_action": {"name": enemy_skill.name if enemy_skill else "扑击", "outcome": enemy_outcome},
            })
            commit = self._commit_battle_result("defeat")

            await self._push({"type": "state", "data": self.snapshot()})
            await self._push({"type": "end", "data": {
                "result": "defeat",
                "penalty": {"hp": 1, "exp_lost": 0},
                "commit": commit,
            }})
            if self.mode != "speed":
                self._start_narration(card, my_outcome, enemy_skill, enemy_outcome, is_destiny)
            return

        # === 5. 回玩家回合 ===
        self.state["status"] = "player_turn"

        # 天命降临:5%
        if not self.state["destiny_used"] and not self.state["destiny_charged"]:
            if random.random() < 0.05:
                self.state["destiny_charged"] = True
                destiny = get_destiny_skill(self.state["sect_id"])
                await self._push({
                    "type": "destiny_trigger",
                    "data": {
                        "skill": destiny,
                        "round": self.state["round"] + 1,
                        "message": f"⚡ 天命降临!{self.state['sect_name']}独家神技已就绪。",
                    },
                })

        await self._push({"type": "state", "data": self.snapshot()})
        await self._push({"type": "turn_ready", "data": {"round": self.state["round"] + 1}})

        # 记录 history
        self.history.append({
            "round": self.state["round"],
            "player_action": {"name": card.name, "outcome": my_outcome},
            "enemy_action": {"name": enemy_skill.name if enemy_skill else "扑击", "outcome": enemy_outcome},
        })

        # === 6. fire-and-forget LLM 叙事(非阻塞) ===
        if self.mode != "speed":
            self._start_narration(card, my_outcome, enemy_skill, enemy_outcome, is_destiny)

    # ================================================================
    # LLM 叙事(后台 task,可 skip)
    # ================================================================
    def _start_narration(self, card, my_outcome, enemy_skill, enemy_outcome, is_destiny):
        # 若上一回合叙事还在跑(用户已点下一招),取消它
        if self.current_narration_task and not self.current_narration_task.done():
            self.current_narration_task.cancel()

        self.current_narration_task = self._track_task(asyncio.create_task(
            self._narrate_round(card, my_outcome, enemy_skill, enemy_outcome, is_destiny)
        ))

    async def _narrate_round(self, card, my_outcome, enemy_skill, enemy_outcome, is_destiny):
        round_no = self.state["round"]
        try:
            # ★ 使用角色当前门派境界模型,仅按动作强度调整输出长度。
            model, max_tokens = pick_narration_model(
                self.state["model"],
                is_destiny=is_destiny,
                is_crit=my_outcome.get("is_crit", False),
            )

            # ★ Phase 5: 池只服务"普攻成功命中"(basic_strike + attack type + hit)
            # 治疗/buff/天命/暴击/未命中 都不应该用普攻池
            card_id = getattr(card, "id", "")
            card_type = getattr(card, "type", "attack")
            is_basic_attack_hit = (
                card_id == "basic_strike"
                and card_type == "attack"
                and my_outcome.get("type") == "hit"
                and not my_outcome.get("is_crit", False)
            )
            if (not is_destiny and is_basic_attack_hit and self.narration_pool):
                text = self.narration_pool.pop(0)
                await self._push({"type": "narration_start", "data": {
                    "round": round_no, "model": model + " (cached)",
                    "max_tokens": max_tokens, "cached": True,
                }})
                # 模拟流式打字
                for i in range(0, len(text), 6):
                    await self._push({"type": "narration", "data": {"delta": text[i:i+6]}})
                    await asyncio.sleep(0.03)
                await self._push({"type": "narration_end", "data": {
                    "round": round_no, "elapsed_ms": 0, "chars": len(text),
                    "model": model + " (cached)", "cached": True,
                }})
                # 后台补充池子
                self._track_task(asyncio.create_task(self._refill_pool()))
                return

            start_time = time.time()
            await self._push({"type": "narration_start", "data": {
                "round": round_no, "model": model, "max_tokens": max_tokens,
            }})

            char_count = 0
            output_text = []
            usage_holder = {"usage": None, "fallback": False}
            FIRST_CHUNK_TIMEOUT = 3.0   # 首字超时:LLM 3s 还没吐字 → 直接 fallback
            TOTAL_TIMEOUT = 8.0          # 总超时:整段叙事 8s 上限
            first_chunk_received = False
            need_fallback = False

            # 用一个 inner task 跑 LLM 流,主协程负责超时控制
            stream_done = asyncio.Event()

            async def _on_usage(usage: dict):
                usage_holder["usage"] = usage

            async def _on_fallback():
                usage_holder["fallback"] = True

            async def _consume_stream():
                nonlocal first_chunk_received, char_count
                try:
                    async for chunk in stream_combined_narration(
                        sect_style=self.sect.narration_style,
                        model=model,
                        max_tokens=max_tokens,
                        state=self.state,
                        player_card=card,
                        player_outcome=my_outcome,
                        enemy_skill=enemy_skill,
                        enemy_outcome=enemy_outcome,
                        api_key=self.narration_api_key,
                        base_url=self.narration_base_url,
                        on_usage=_on_usage,
                        on_fallback=_on_fallback,
                    ):
                        if not first_chunk_received:
                            first_chunk_received = True
                        char_count += len(chunk)
                        output_text.append(chunk)
                        await self._push({"type": "narration", "data": {"delta": chunk}})
                        if time.time() - start_time > TOTAL_TIMEOUT:
                            break
                finally:
                    stream_done.set()

            stream_task = asyncio.create_task(_consume_stream())

            try:
                # 等首字 OR 流自然结束 OR 首字超时
                async def _wait_first_chunk():
                    while not first_chunk_received and not stream_done.is_set():
                        await asyncio.sleep(0.05)

                try:
                    await asyncio.wait_for(_wait_first_chunk(), timeout=FIRST_CHUNK_TIMEOUT)
                except asyncio.TimeoutError:
                    # 3 秒内没收到任何 content → 直接 fallback
                    need_fallback = True
                    stream_task.cancel()

                # 边界:stream 自然结束但 content 全空(全 reasoning)→ 也 fallback
                if stream_done.is_set() and not first_chunk_received:
                    need_fallback = True

                if need_fallback:
                    # 上游卡住/返回空 → 本地模板兜底,不阻塞战斗
                    fallback = self._fallback_narration(card, my_outcome, enemy_skill, enemy_outcome)
                    for i in range(0, len(fallback), 8):
                        await self._push({"type": "narration", "data": {"delta": fallback[i:i+8]}})
                        await asyncio.sleep(0.02)
                    char_count = len(fallback)
                    model = model + " (fallback)"
                else:
                    # 首字已收到 → 等流自然结束(总 8s 兜底)
                    try:
                        await asyncio.wait_for(stream_done.wait(), timeout=TOTAL_TIMEOUT)
                    except asyncio.TimeoutError:
                        stream_task.cancel()
            except Exception as stream_err:
                # 其他异常 → 没收到字就 fallback,收到了就直接结束
                if not first_chunk_received:
                    fallback = self._fallback_narration(card, my_outcome, enemy_skill, enemy_outcome)
                    for i in range(0, len(fallback), 8):
                        await self._push({"type": "narration", "data": {"delta": fallback[i:i+8]}})
                        await asyncio.sleep(0.02)
                    char_count = len(fallback)
                    model = model + " (fallback)"
                print(f"[Battle Narration] {stream_err}")

            elapsed_ms = int((time.time() - start_time) * 1000)
            if first_chunk_received and not usage_holder.get("fallback"):
                try:
                    from .cultivation import apply_cultivation_gain, estimate_tokens
                    usage = usage_holder.get("usage")
                    if usage and usage.get("total_tokens"):
                        token_delta = int(usage.get("total_tokens") or 0)
                        apply_cultivation_gain(
                            self.user_id, token_delta, "", "battle_round_narration",
                            model=model,
                            input_tokens=int(usage.get("input_tokens") or 0),
                            output_tokens=int(usage.get("output_tokens") or 0),
                            reasoning_tokens=int(usage.get("reasoning_tokens") or 0),
                            usage_source="provider",
                        )
                    else:
                        prompt = build_combined_user_prompt(self.state, card, my_outcome, enemy_skill, enemy_outcome)
                        token_delta = estimate_tokens(prompt) + estimate_tokens("".join(output_text))
                        apply_cultivation_gain(
                            self.user_id, token_delta, "", "battle_round_narration",
                            model=model,
                            usage_source="estimated",
                        )
                except Exception as e:
                    print(f"[Battle Narration Ledger] {e}")
            await self._push({"type": "narration_end", "data": {
                "round": round_no, "elapsed_ms": elapsed_ms,
                "chars": char_count, "model": model,
            }})
        except asyncio.CancelledError:
            await self._push({"type": "narration_end", "data": {
                "round": round_no, "cancelled": True,
            }})
            raise
        except Exception as e:
            print(f"[Battle Narration] {e}")
            await self._push({"type": "narration_end", "data": {
                "round": round_no, "error": str(e)[:200],
            }})

    def _fallback_narration(self, card, my_outcome, enemy_skill, enemy_outcome):
        """LLM 超时后的模板叙事兜底 — 简短、信息完整、世界观一致"""
        player_name = self.state.get("player", {}).get("name", "执笔者")
        enemy_name = self.state.get("enemy", {}).get("name", "妖兽")
        dmg = my_outcome.get("damage", 0)
        enemy_dmg = enemy_outcome.get("damage", 0)

        templates = [
            f"{player_name}以「{card.name}」出击,{enemy_name}受创 **{dmg}**。{enemy_name}反手一击,造成 **{enemy_dmg}** 伤害。",
            f"灵力涌动,{player_name}施展{card.name},命中{enemy_name},扣除生命 **{dmg}**。{enemy_name}不甘示弱,回击 **{enemy_dmg}**。",
            f"一招{card.name}破空而出,{enemy_name}吃下 **{dmg}** 伤害。{enemy_name}怒吼回击,{player_name}承受 **{enemy_dmg}**。",
        ]

        if my_outcome.get("is_crit"):
            templates = [f"暴击!{player_name}的{card.name}精准命中{enemy_name}要害,**{dmg}** 点伤害!{enemy_name}反扑造成 **{enemy_dmg}**。"]
        elif my_outcome.get("missed"):
            templates = [f"{player_name}的{card.name}被{enemy_name}闪避!{enemy_name}趁势反击,造成 **{enemy_dmg}** 伤害。"]

        return random.choice(templates)

    def skip_narration(self, include_chapter: bool = False):
        """玩家点跳过 — cancel 当前叙事 task。include_chapter=True 同时跳过战后章节"""
        if self.current_narration_task and not self.current_narration_task.done():
            self.current_narration_task.cancel()
        if include_chapter and self.chapter_task and not self.chapter_task.done():
            self.chapter_task.cancel()

    # ================================================================
    # 预生成池(后台)
    # ================================================================
    async def warmup_pool(self, count: int = 3):
        """进战时调用一次,后台并发生 N 段通用普攻叙事备用"""
        if self.mode == "speed":
            return
        try:
            async def _on_usage(usage: dict):
                try:
                    from .cultivation import apply_cultivation_gain
                    apply_cultivation_gain(
                        self.user_id,
                        int(usage.get("total_tokens") or 0),
                        "",
                        "battle_prefetch_narration",
                        model=self.narration_model,
                        input_tokens=int(usage.get("input_tokens") or 0),
                        output_tokens=int(usage.get("output_tokens") or 0),
                        reasoning_tokens=int(usage.get("reasoning_tokens") or 0),
                        usage_source="estimated" if usage.get("estimated") else "provider",
                    )
                except Exception as e:
                    print(f"[Battle Pool Ledger] {e}")
            texts = await prefetch_pool_narrations(
                sect_style=self.sect.narration_style,
                state=self.state,
                count=count,
                api_key=self.narration_api_key,
                base_url=self.narration_base_url,
                model=self.narration_model,
                on_usage=_on_usage,
            )
            self.narration_pool.extend(texts)
        except Exception as e:
            print(f"[Battle Pool] warmup 失败: {e}")

    async def _refill_pool(self):
        """池子被消耗后,后台补 1 段"""
        if self.mode == "speed" or self.is_finished():
            return
        try:
            async def _on_usage(usage: dict):
                try:
                    from .cultivation import apply_cultivation_gain
                    apply_cultivation_gain(
                        self.user_id,
                        int(usage.get("total_tokens") or 0),
                        "",
                        "battle_prefetch_narration",
                        model=self.narration_model,
                        input_tokens=int(usage.get("input_tokens") or 0),
                        output_tokens=int(usage.get("output_tokens") or 0),
                        reasoning_tokens=int(usage.get("reasoning_tokens") or 0),
                        usage_source="estimated" if usage.get("estimated") else "provider",
                    )
                except Exception as e:
                    print(f"[Battle Pool Ledger] {e}")
            texts = await prefetch_pool_narrations(
                sect_style=self.sect.narration_style,
                state=self.state,
                count=1,
                api_key=self.narration_api_key,
                base_url=self.narration_base_url,
                model=self.narration_model,
                on_usage=_on_usage,
            )
            self.narration_pool.extend(texts)
        except Exception as e:
            print(f"[Battle Pool] refill 失败: {e}")

    # ================================================================
    # 战后章节(后台)
    # ================================================================
    async def _generate_chapter(self):
        """战后章节 — 使用当前门派境界模型写完整章节"""
        if not self.history:
            return
        try:
            await self._push({"type": "chapter_start", "data": {
                "rounds": len(self.history),
                "result": self.state.get("result"),
            }})
            async for chunk in stream_chapter_narration(
                sect_style=self.sect.narration_style,
                state=self.state,
                history=self.history,
                api_key=self.narration_api_key,
                base_url=self.narration_base_url,
                model=self.narration_model,
            ):
                await self._push({"type": "chapter", "data": {"delta": chunk}})
            await self._push({"type": "chapter_end", "data": {}})
        except Exception as e:
            print(f"[Battle Chapter] {e}")
            await self._push({"type": "chapter_end", "data": {"error": str(e)[:200]}})

    # ================================================================
    # ★ Phase 3: 战斗内使用道具(原子,修改 self.state 而非 character)
    # ================================================================
    async def use_item(self, item_id: str):
        """战斗中使用道具 — 持锁防止并发"""
        async with self._action_lock:
            if self.is_finished():
                await self._push({"type": "error", "data": {"message": "战斗已结束"}})
                return
            if self.state.get("status") not in ("player_turn",):
                await self._push({"type": "error", "data": {"message": "尚未轮到你出手"}})
                return

            from .items import get_item
            from .store import remove_item, get_inventory
            item = get_item(item_id)
            if not item:
                await self._push({"type": "error", "data": {"message": f"道具 {item_id} 不存在"}})
                return

            # 原子扣物品(remove_item 返回 False 表示不足)
            inv = get_inventory(self.user_id)
            cur_count = inv.get(item_id, 0) if isinstance(inv, dict) else next((it["count"] for it in inv if it["id"] == item_id), 0)
            if cur_count < 1:
                await self._push({"type": "error", "data": {"message": "背包中没有此物品"}})
                return
            removed = remove_item(self.user_id, item_id, 1)
            if not removed:
                await self._push({"type": "error", "data": {"message": "扣除物品失败"}})
                return

            # 应用道具效果到战斗内存态
            effects = item.get("use_effect", {}) if isinstance(item, dict) else getattr(item, "use_effect", {}) or {}
            heal = int(effects.get("hp_restore", effects.get("hp", 0)) or 0)
            if effects.get("hp_percent"):
                heal = max(heal, int(self.state["player_max_hp"] * float(effects["hp_percent"]) / 100))
            qi_add = int(effects.get("qi_restore", effects.get("qi", 0)) or 0)
            if effects.get("qi_percent"):
                qi_add = max(
                    qi_add,
                    int(self.state["player_max_qi"] * float(effects["qi_percent"]) / 100),
                    int(effects.get("qi_min", 0) or 0),
                )
            atk_buff = int(effects.get("atk_buff_turns", 0) or 0)

            applied = {}
            if heal > 0:
                old = self.state["player_hp"]
                self.state["player_hp"] = min(self.state["player_max_hp"], old + heal)
                applied["hp_delta"] = self.state["player_hp"] - old
            if qi_add > 0:
                old = self.state["player_qi"]
                self.state["player_qi"] = min(self.state["player_max_qi"], old + qi_add)
                applied["qi_delta"] = self.state["player_qi"] - old
            if atk_buff > 0:
                self.state.setdefault("buffs", {})["atk_buff_turns"] = atk_buff
                applied["atk_buff_turns"] = atk_buff

            await self._push({"type": "item_used", "data": {
                "item_id": item_id,
                "item_name": item.get("name", item_id) if isinstance(item, dict) else getattr(item, "name", item_id),
                "applied": applied,
                "remaining_count": cur_count - 1,
            }})
            await self._push({"type": "state", "data": self.snapshot()})

    # ================================================================
    # ★ Phase 3: 服务端赠礼次数管理
    # ================================================================
    def can_gift(self):
        """检查是否允许赠礼。返回 (allowed, reason)"""
        if self.is_finished():
            return False, "战斗已结束"
        if self.gift_count >= 3:
            return False, "本场战斗已赠礼 3 次"
        return True, ""

    def record_gift_attempt(self) -> int:
        """记录一次赠礼尝试,返回当前次数(用于计算接受概率衰减)"""
        self.gift_count += 1
        return self.gift_count

    async def end_with_gift(self, exp_reward: int):
        """赠礼成功 → 走统一 commit,result='pacified'"""
        async with self._action_lock:
            if self.is_finished():
                return
            self.state["status"] = "ended"
            self.state["result"] = "pacified"
            # 保留战斗剩余 hp/qi,加奖励 exp
            commit = self._commit_battle_result("pacified", rewards={"exp": exp_reward, "qi": 0})
            await self._push({"type": "state", "data": self.snapshot()})
            await self._push({"type": "end", "data": {
                "result": "victory",      # 前端兼容:仍按胜利处理
                "finish_reason": "gift",
                "rewards": {"exp": exp_reward},
                "commit": commit,
            }})

    # ================================================================
    # 撤退 — 终止信号,必须立即响应,不能等 cast 释放锁
    # ================================================================
    async def flee(self):
        """撤退 — 强制立即终止,不持锁(避免等正在跑的 cast/叙事)

        流程:
          1. 立即设 status=ended 防止后续 cast 进入
          2. cancel 所有后台 task(叙事/章节/池补充)
          3. 统一提交战斗结果(commit 自带幂等)
          4. 推 state + end 给前端
        """
        if self.is_finished():
            return
        # ★ 立即标 ended — 任何并发的 cast 进锁后会因 status 检查而拒绝
        self.state["status"] = "ended"
        self.state["result"] = "fled"
        self.state["player_hp"] = max(1, self.state.get("player_hp", 1))

        # ★ 主动 cancel 所有后台 task(包括叙事/章节,免得它们继续吐字)
        if self.current_narration_task and not self.current_narration_task.done():
            self.current_narration_task.cancel()
        if self.chapter_task and not self.chapter_task.done():
            self.chapter_task.cancel()
        for t in list(self._bg_tasks):
            if not t.done():
                t.cancel()

        # 统一提交(_commit_battle_result 自带 _committed 幂等保护)
        self._commit_battle_result("fled")
        await self._push({"type": "state", "data": self.snapshot()})
        await self._push({"type": "end", "data": {"result": "fled"}})

    # ================================================================
    # 数值层(同 v1)
    # ================================================================
    def _compute_outcome(self, card) -> dict:
        s = self.state

        if card.type == "heal":
            heal = int(s["player_max_hp"] * 0.3)
            return {
                "type": "heal", "type_zh": "回复",
                "damage": 0, "is_crit": False, "heal": heal,
                "effect_desc": f"回复 {heal} 点 HP",
            }
        if card.type == "buff":
            buff_map = {
                "focus": {
                    "focus_next": True,
                    "effect_desc": "凝神入微,下一击伤害 +50%",
                },
                "canglan_intent": {
                    "crit_next_bonus": 0.30,
                    "crit_dmg_next_bonus": 0.20,
                    "effect_desc": "剑意凝聚,下一击暴击率 +30%,暴击伤害 +20%",
                },
                "body_guard": {
                    "defense_turns": 3,
                    "damage_reduction": 0.25,
                    "effect_desc": "护体罡气护身,3 回合受到伤害 -25%",
                },
                "swift_wind": {
                    "evasion_turns": 3,
                    "evasion_bonus": 0.08,
                    "hit_bonus_next": 0.08,
                    "effect_desc": "御风而行,3 回合闪避 +8%,下一击命中 +8%",
                },
                "tianji_calc": {
                    "hit_floor_next": 0.85,
                    "effect_desc": "万象推演已定,下一击命中下限提升至 85%",
                },
                "qingming_root": {
                    "max_hp_bonus_pct": 0.15,
                    "effect_desc": "根基稳固,本战生命上限 +15% 并恢复对应气血",
                },
                "qingming_classic": {
                    "def_mult_turns": 3,
                    "def_mult": 0.25,
                    "effect_desc": "千古经文护身,3 回合防御 +25%",
                },
                "yueyin_swift": {
                    "evasion_turns": 3,
                    "evasion_bonus": 0.10,
                    "effect_desc": "夜行如风,3 回合闪避 +10%",
                },
                "yueyin_hide": {
                    "no_crit_turns": 2,
                    "no_crit": True,
                    "effect_desc": "月隐之姿遮蔽命门,2 回合不会被暴击",
                },
            }
            config = buff_map.get(card.id, {
                "focus_next": True,
                "effect_desc": "心神集中,下一击伤害 +50%",
            })
            return {
                "type": "buff", "type_zh": "增益",
                "damage": 0, "is_crit": False, "buff": card.id,
                "buff_effects": config,
                "effect_desc": config["effect_desc"],
            }

        evasion = s["enemy_evasion"]
        hit_floor = float(self._active_buff("hit_floor_next", 0.65) or 0.65)
        hit_bonus = float(self._active_buff("hit_bonus_next", 0) or 0)
        miss_streak = s.setdefault("miss_streak", {}).get("player", 0)
        if miss_streak >= 2:
            hit_bonus += 0.15
        hit_rate = combat_hit_rate(card.hit_rate + hit_bonus, evasion, low=max(0.65, hit_floor))
        if random.random() > hit_rate:
            return {
                "type": "miss", "type_zh": "失手",
                "damage": 0, "is_crit": False,
                "effect_desc": "被对手闪避",
            }

        atk = s["player_atk"]
        if s["buffs"].get("focus_next"):
            atk = int(atk * 1.5)

        crit_rate = min(
            0.95,
            s["player_crit"] + float(getattr(card, "crit_bonus", 0) or 0) + float(self._active_buff("crit_next_bonus", 0) or 0),
        )
        is_crit = random.random() < crit_rate
        crit_dmg = s["player_crit_dmg"] + float(self._active_buff("crit_dmg_next_bonus", 0) or 0)
        damage = combat_damage(
            atk,
            s["enemy_def"],
            card.power,
            crit=is_crit,
            crit_dmg=crit_dmg,
            variance=random.uniform(0.92, 1.08),
        )
        pressure = self._pressure_mult()
        if pressure > 1.0:
            damage = int(damage * pressure)

        return {
            "type": "crit" if is_crit else "hit",
            "type_zh": "暴击!" if is_crit else "命中",
            "damage": damage, "is_crit": is_crit,
            "effect_desc": f"造成 {damage} 点伤害" + ("(暴击!)" if is_crit else "") + (" · 破绽显现" if pressure > 1.0 else ""),
        }

    def _apply_outcome(self, outcome, card):
        s = self.state
        if outcome["type"] == "heal":
            s["player_hp"] = min(s["player_max_hp"], s["player_hp"] + outcome["heal"])
        elif outcome["type"] == "buff":
            effects = outcome.get("buff_effects", {})
            if effects.get("max_hp_bonus_pct") and not s["buffs"].get("max_hp_bonus_applied"):
                bonus = int(s["player_max_hp"] * float(effects["max_hp_bonus_pct"]))
                s["player_max_hp"] += bonus
                s["player_hp"] = min(s["player_max_hp"], s["player_hp"] + bonus)
                s["buffs"]["max_hp_bonus_applied"] = True
            for key, value in effects.items():
                if key not in {"effect_desc", "max_hp_bonus_pct"}:
                    s["buffs"][key] = value
        else:
            s["enemy_hp"] = max(0, s["enemy_hp"] - outcome["damage"])
            if outcome["type"] == "miss":
                s.setdefault("miss_streak", {})["player"] = s.setdefault("miss_streak", {}).get("player", 0) + 1
            else:
                s.setdefault("miss_streak", {})["player"] = 0
            self._consume_attack_buffs()

    def _compute_enemy_action(self, skill=None) -> dict:
        s = self.state
        player_evasion = s["player_evasion"] + float(self._active_buff("evasion_bonus", 0) or 0)
        enemy_miss_streak = s.setdefault("miss_streak", {}).get("enemy", 0)
        enemy_hit_bonus = 0.12 if enemy_miss_streak >= 2 else 0
        hit_rate = combat_hit_rate((skill.hit_rate if skill else 0.90) + enemy_hit_bonus, player_evasion, low=0.60, high=0.96)
        if random.random() > hit_rate:
            return {
                "type": "miss", "type_zh": "失手",
                "damage": 0, "is_crit": False,
                "effect_desc": "你侧身闪过",
            }

        crit_chance = 0.05 + (skill.crit_bonus if skill else 0)
        if self._active_buff("no_crit", False):
            crit_chance = 0
        is_crit = random.random() < crit_chance

        power = skill.power if skill else 1.0
        player_def = int(s["player_def"] * (1 + float(self._active_buff("def_mult", 0) or 0)))
        damage = combat_damage(
            s["enemy_atk"],
            player_def,
            power,
            crit=is_crit,
            crit_dmg=1.6,
            variance=random.uniform(0.88, 1.12),
        )
        reduction = float(self._active_buff("damage_reduction", 0) or 0)
        if reduction:
            damage = max(1, int(damage * (1 - reduction)))

        return {
            "type": "crit" if is_crit else "hit",
            "type_zh": "暴击!" if is_crit else "命中",
            "damage": damage, "is_crit": is_crit,
            "effect_desc": f"对你造成 {damage} 点伤害" + ("(暴击!)" if is_crit else ""),
        }

    def _compute_destiny_outcome(self, card) -> dict:
        s = self.state
        atk = s["player_atk"]
        damage = combat_damage(
            atk,
            s["enemy_def"],
            card.power,
            crit=True,
            crit_dmg=s["player_crit_dmg"] * 1.5,
            variance=random.uniform(0.95, 1.05),
        )
        pressure = self._pressure_mult()
        if pressure > 1.0:
            damage = int(damage * pressure)
        return {
            "type": "destiny", "type_zh": "天命降世!",
            "damage": damage, "is_crit": True,
            "effect_desc": f"天道为之颤栗 — 一击造成 {damage} 点伤害!" + (" 破绽显现。" if pressure > 1.0 else ""),
        }

    def _apply_enemy_outcome(self, outcome):
        if outcome["damage"] > 0:
            self.state["player_hp"] = max(0, self.state["player_hp"] - outcome["damage"])
            self.state.setdefault("miss_streak", {})["enemy"] = 0
        elif outcome.get("type") == "miss":
            self.state.setdefault("miss_streak", {})["enemy"] = self.state.setdefault("miss_streak", {}).get("enemy", 0) + 1
        self._tick_player_buffs()

    # ================================================================
    # ★ 奖励 / 惩罚 — 真正写回 character 数据
    # ================================================================
    def _grant_rewards(self, rewards: dict) -> Optional[dict]:
        """[Deprecated] 只保留灵气兼容;修为必须由墨炉 token 结算。"""
        char = get_character(self.user_id)
        if not char:
            return None

        char["qi"] = min(char.get("max_qi", 800), char.get("qi", 0) + rewards.get("qi", 0))

        save_character(self.user_id, char)
        return None

    def _apply_defeat_penalty(self):
        """[Deprecated] 战败只残血,修为不回扣。"""
        char = get_character(self.user_id)
        if not char:
            return
        char["hp"] = 1
        save_character(self.user_id, char)

    def _record_battle_to_character(self, result: str):
        """[Deprecated] 已合并进 _commit_battle_result。保留向后兼容。"""
        self._commit_battle_result(result)

    def _spar_commit(self, outcome: str, npc_sect: str) -> dict:
        """★ Round 2 切磋结算 — 不走 _commit_battle_result(避免被 friendly 污染)
        - 胜利:对应派友好度 +3,修为由切磋章 token 结算
        - 失败:无惩罚,只 +1 友好度(认输也有礼貌)
        - HP/Qi 持久化战斗剩余值
        """
        if self._committed:
            return {"ok": True, "already_committed": True}
        self._committed = True
        char = get_character(self.user_id)
        if not char:
            return {"ok": False}
        # 同步 HP/Qi(切磋不死,保留剩余)
        final_hp = max(1, self.state.get("player_hp", char.get("hp", 1)))
        final_qi = max(0, self.state.get("player_qi", char.get("qi", 0)))
        char["hp"] = min(char.get("max_hp", 100), final_hp)
        char["qi"] = min(char.get("max_qi", 600), final_qi)
        # 奖励
        rep_gained = 0
        if outcome == "win":
            rep_gained = 3
        else:  # loss
            rep_gained = 1
        if npc_sect:
            f = char.setdefault("factions", {})
            f[npc_sect] = f.get(npc_sect, 0) + rep_gained
        fatigue_delta = add_battle_fatigue(
            char,
            f"spar_{outcome}",
            self.state.get("round", 0),
            friendly=True,
        )
        cultivation_task_id = None
        try:
            from .cultivation import make_battle_task
            task = make_battle_task(self.user_id, f"spar_{outcome}", dict(self.state), list(self.history))
            cultivation_task_id = task.get("id")
        except Exception as exc:
            print(f"[cultivation] enqueue spar chapter failed: {exc}")
        # 历史
        hist = char.setdefault("battle_history", [])
        hist.append({
            "battle_id": self.battle_id,
            "enemy_id": self.state.get("enemy_id"),
            "enemy_name": self.state.get("enemy_name"),
            "result": f"spar_{outcome}",
            "rounds": self.state.get("round", 0),
            "timestamp": time.time(),
            "rewards": {"exp": 0, "friendship_delta": rep_gained, "fatigue": fatigue_delta.get("gain", 0)},
            "cultivation_task_id": cultivation_task_id,
        })
        char["battle_history"] = hist[-50:]
        save_character(self.user_id, char)
        # journal
        from .store import add_journal_entry
        try:
            label = "切磋取胜" if outcome == "win" else "切磋认输"
            add_journal_entry(self.user_id, "spar",
                              f"{label}·{self.state.get('enemy_name','')}",
                              f"切磋章已入墨炉 · {npc_sect}友好度 +{rep_gained} · 疲劳 +{fatigue_delta.get('gain', 0)}",
                              {"tags":["切磋", npc_sect, label], "cultivation_task_id": cultivation_task_id})
        except Exception:
            pass
        return {"ok": True, "exp_gained": 0, "friendship_delta": rep_gained,
                "cultivation_task_id": cultivation_task_id, "fatigue": fatigue_delta}

    # ================================================================
    # ★ Phase 4: 后台任务统一跟踪 + 清理
    # ================================================================
    def _track_task(self, task: asyncio.Task) -> asyncio.Task:
        """注册后台 task,自动 done 时移除"""
        self._bg_tasks.add(task)
        task.add_done_callback(self._bg_tasks.discard)
        return task

    async def cleanup(self):
        """断开 WS / 战斗结束 → 清理所有后台 task"""
        if self.current_narration_task and not self.current_narration_task.done():
            self.current_narration_task.cancel()
        if self.chapter_task and not self.chapter_task.done():
            self.chapter_task.cancel()
        for t in list(self._bg_tasks):
            if not t.done():
                t.cancel()
        # 等所有 task 收尾,吞掉 CancelledError
        if self._bg_tasks:
            await asyncio.gather(*self._bg_tasks, return_exceptions=True)

    def _commit_battle_result(self, result: str,
                              rewards: Optional[dict] = None,
                              drops: Optional[list] = None,
                              extra: Optional[dict] = None) -> dict:
        """★ Phase 2: 统一战斗结算提交(幂等)

        一次性把战斗内存态写回 SQLite character JSON,避免分散 save_character 互相覆盖。

        result: "victory" / "defeat" / "fled" / "pacified"
        rewards: {"exp": int, "qi": int}  仅保留兼容; exp 不再直接加修为
        drops:   [{id, name, ...}, ...]  仅 victory 用
        extra:   {"drop_pity_delta": int, ...} 其他可选字段

        返回: {ok, level_up, new_hp, new_qi, new_level, new_realm}
        """
        # 幂等:已经 commit 过就直接返回
        if self._committed:
            return {"ok": True, "already_committed": True}
        self._committed = True

        char = get_character(self.user_id)
        if not char:
            return {"ok": False, "error": "no_character"}

        rewards = rewards or {}
        drops = drops or []
        extra = extra or {}

        # ─── 1. 同步战斗内存态的 HP/Qi 到存档 ────────────────────────
        final_hp = self.state.get("player_hp", char.get("hp", 1))
        final_qi = self.state.get("player_qi", char.get("qi", 0))

        if result == "defeat":
            # 战败惩罚:残血 1。修为不回扣,失败会以败笔章入墨炉。
            final_hp = 1
        elif result == "fled":
            final_hp = max(1, final_hp)

        char["hp"] = max(0, min(char.get("max_hp", 100), final_hp))
        char["qi"] = max(0, min(char.get("max_qi", 600), final_qi))

        # ─── 2. 胜利/安抚奖励(只保留即时灵气;修为改由墨炉 token 结算) ─────
        level_up_info = []
        if result in ("victory", "pacified"):
            qi_gained = rewards.get("qi", 0)
            char["qi"] = min(char.get("max_qi", 600), char["qi"] + qi_gained)

        # ─── 3. drop_pity 更新(掉落保底计数) ─────────────────────────
        if "drop_pity_delta" in extra:
            char["drop_pity"] = max(0, char.get("drop_pity", 0) + extra["drop_pity_delta"])

        # ─── 4. 战斗操作疲劳(按回合 + 结局累计,下一轮清零) ─────────────
        fatigue_delta = add_battle_fatigue(
            char,
            result,
            self.state.get("round", 0),
            friendly=bool(self.state.get("friendly")),
        )

        # ─── 5. 创建墨炉任务(只写一次) ───────────────────────────────
        cultivation_task_id = None
        if result in ("victory", "defeat", "fled", "pacified"):
            try:
                from .cultivation import make_battle_task
                task = make_battle_task(
                    self.user_id,
                    result,
                    dict(self.state),
                    list(self.history),
                    rewards=rewards,
                    drops=drops,
                )
                cultivation_task_id = task.get("id")
            except Exception as exc:
                print(f"[cultivation] enqueue battle chapter failed: {exc}")

        # ─── 6. 战斗历史(只写一次) ─────────────────────────────────
        history = char.get("battle_history", [])
        history.append({
            "battle_id": self.battle_id,
            "enemy_id": self.state.get("enemy_id"),
            "enemy_name": self.state.get("enemy_name"),
            "result": result,
            "rounds": self.state.get("round", 0),
            "timestamp": time.time(),
            "rewards": {
                "exp": rewards.get("exp", 0),
                "qi": rewards.get("qi", 0),
                "fatigue": fatigue_delta.get("gain", 0),
                "drops": [d.get("id") if isinstance(d, dict) else str(d) for d in drops],
            },
            "cultivation_task_id": cultivation_task_id,
        })
        char["battle_history"] = history[-50:]

        # ─── 7. 教学完成 flag(看一次就标记) ──────────────────────────
        flags = char.setdefault("flags", {})
        flags["battle_tutorial_done"] = True

        # ─── 8. 一次性持久化 ──────────────────────────────────────
        save_character(self.user_id, char)

        # ─── 9. ★ 写修行录(战斗 + 入炉)─────────────────────────
        try:
            from .store import add_journal_entry
            enemy_name = self.state.get("enemy_name", "妖兽")
            rounds = self.state.get("round", 0)
            result_label = {"victory":"战斗胜利","defeat":"战斗失败","fled":"撤退离场","pacified":"赠礼安抚"}.get(result, result)
            result_type = {"victory":"battle_victory","defeat":"battle_defeat","fled":"battle_flee","pacified":"gift"}.get(result, "battle_victory")
            detail_parts = [f"击战 {rounds} 回合"]
            if result == "victory":
                if rewards.get("qi"):  detail_parts.append(f"灵气 +{rewards['qi']}")
                if drops:
                    drop_names = [d.get("name", d.get("id","?")) for d in drops if isinstance(d, dict)]
                    if drop_names: detail_parts.append(f"战利品 {','.join(drop_names)}")
            elif result == "defeat":
                detail_parts.append("HP 降至 1")
            if cultivation_task_id:
                detail_parts.append("本命书章节已入墨炉")
            if fatigue_delta.get("gain"):
                detail_parts.append(f"疲劳 +{fatigue_delta['gain']}")
            tags = [enemy_name, result_label]
            add_journal_entry(self.user_id, result_type,
                              f"{result_label}·{enemy_name}",
                              " · ".join(detail_parts),
                              {"tags": tags, "battle_id": self.battle_id, "cultivation_task_id": cultivation_task_id})
        except Exception as _je:
            print(f"[journal] battle write err: {_je}")

        return {
            "ok": True,
            "level_up": level_up_info,
            "new_hp": char["hp"],
            "new_qi": char["qi"],
            "new_level": char["level"],
            "new_realm": char.get("realm_name", ""),
            "cultivation_task_id": cultivation_task_id,
            "fatigue": fatigue_delta,
        }

    def _roll_drops(self) -> list:
        """掉落判定 — 含保底机制(pity counter)"""
        enemy = get_enemy(self.state["enemy_id"])
        if not enemy:
            return []
        results = []
        tier_probs = {
            "low": {1: 0.70, 2: 0.25, 3: 0.06, 4: 0.0, 5: 0.0, 6: 0.0},
            "mid": {1: 0.80, 2: 0.45, 3: 0.15, 4: 0.04, 5: 0.0, 6: 0.0},
            "high": {1: 0.40, 2: 0.70, 3: 0.35, 4: 0.12, 5: 0.03, 6: 0.0},
            "myth": {1: 0.0, 2: 0.40, 3: 0.75, 4: 0.35, 5: 0.12, 6: 0.03},
        }
        rarity_probs = tier_probs.get(getattr(enemy, "tier", "mid"), tier_probs["mid"])
        max_material_drops = {"low": 2, "mid": 2, "high": 3, "myth": 4}.get(getattr(enemy, "tier", "mid"), 2)
        material_drops = 0

        # ★ 保底:连续 N 次无稀有(rarity≥3)掉落,概率递增
        char = get_character(self.user_id)
        pity = char.get("drop_pity", 0) if char else 0
        pity_bonus = pity * 0.03  # 每次无稀有 +3% 概率
        got_rare = False

        for item_id in enemy.drops:
            item = get_item(item_id)
            if not item:
                continue
            is_skill_drop = is_skill_drop_item(item)
            if not is_skill_drop and material_drops >= max_material_drops:
                continue
            base_rate = rarity_probs.get(item.rarity, 0.1)
            if is_skill_drop:
                rate = skill_drop_rate_for_enemy(enemy)
            # 稀有物品(rarity≥3)享受保底加成
            elif item.rarity >= 3 and base_rate > 0:
                rate = min(0.90, base_rate + pity_bonus)
            else:
                rate = base_rate

            if random.random() < rate:
                count = 1
                if item.rarity <= 2:
                    count = random.randint(1, 3)
                add_item(self.user_id, item_id, count)
                d = item_to_dict(item)
                d["count"] = count
                results.append(d)
                if not is_skill_drop:
                    material_drops += 1
                if item.rarity >= 3:
                    got_rare = True

        # 更新 pity counter
        if char:
            if got_rare:
                char["drop_pity"] = 0
            else:
                char["drop_pity"] = pity + 1
            save_character(self.user_id, char)

        return results

    def _build_summary(self, attacker, skill_name, outcome, is_destiny, icon, tier="normal"):
        return {
            "round": self.state["round"],
            "attacker": attacker,
            "skill_name": skill_name,
            "skill_icon": icon,
            "skill_tier": "destiny" if is_destiny else tier,
            "outcome_type": outcome["type"],
            "outcome_label": outcome["type_zh"],
            "damage": outcome.get("damage", 0),
            "is_crit": outcome.get("is_crit", False),
            "heal": outcome.get("heal", 0),
            "is_destiny": is_destiny,
        }
