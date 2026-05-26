#!/bin/bash
# ───────────────────────────────────────────────────────────
# 全流程 E2E smoke test
# 注册→选派→创角→主城→战斗→打坐→修行录,每步 fail 立即报错
# ───────────────────────────────────────────────────────────
set -e
HOST="${HOST:-http://127.0.0.1:8020}"
USER="smoke_$(date +%s)"
PASS="smoke123"

# BYOK 配置。不要把真实 API Key 写进仓库,运行时通过环境变量传入。
BASE_URL="${BASE_URL:-https://bobdong.cn/v1}"
API_KEY="${API_KEY:-}"
if [ -z "$API_KEY" ]; then
  echo "请先设置 API_KEY 环境变量,例如: API_KEY=sk-... bash scripts/smoke_test.sh"
  exit 1
fi

color() { printf "\033[1;%dm%s\033[0m" "$1" "$2"; }
ok() { echo "$(color 32 '✅') $1"; }
fail() { echo "$(color 31 '❌') $1"; exit 1; }
step() { echo; echo "$(color 36 '▶ ') $1"; }

# ─── Step 1: 注册 ───
step "Step 1: 注册新用户 $USER"
RESP=$(curl -sS -X POST $HOST/api/auth/register \
  -H 'Content-Type: application/json' \
  -d "{\"username\":\"$USER\",\"password\":\"$PASS\"}")
TOKEN=$(echo "$RESP" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('data',{}).get('token','NO_TOKEN'))" 2>/dev/null)
[ "$TOKEN" = "NO_TOKEN" ] || [ -z "$TOKEN" ] && fail "注册失败: $RESP"
ok "注册成功 token=${TOKEN:0:16}..."

AUTH="-H Authorization:Bearer\ $TOKEN"
HDR="Authorization: Bearer $TOKEN"

# ─── Step 2: BYOK probe ───
step "Step 2: 探测 5 派可用性"
RESP=$(curl -sS -X POST $HOST/api/byok/probe \
  -H 'Content-Type: application/json' \
  -d "{\"base_url\":\"$BASE_URL\",\"api_key\":\"$API_KEY\"}")
AVAILABLE=$(echo "$RESP" | python3 -c "import sys,json; print(','.join(json.load(sys.stdin)['data']['available_sect_ids']))" 2>/dev/null)
[ -z "$AVAILABLE" ] && fail "Probe 失败: $RESP"
ok "可选派: $AVAILABLE"

# ─── Step 3: 创角(沧澜) ───
step "Step 3: 创角 沧澜剑派 名=测试道君"
RESP=$(curl -sS -X POST $HOST/api/character/choose-sect \
  -H "$HDR" -H 'Content-Type: application/json' \
  -d "{\"sect_id\":\"canglan\",\"character_name\":\"测试道君\",\"base_url\":\"$BASE_URL\",\"api_key\":\"$API_KEY\",\"battle_base_url\":\"\",\"battle_api_key\":\"\"}")
NAME=$(echo "$RESP" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('data',{}).get('name','FAIL'))" 2>/dev/null)
[ "$NAME" = "FAIL" ] && fail "创角失败: $RESP"
ok "创角: $NAME"

# ─── Step 4: GET /me ───
step "Step 4: GET /api/character/me"
RESP=$(curl -sS $HOST/api/character/me -H "$HDR")
INFO=$(echo "$RESP" | python3 -c "import sys,json; d=json.load(sys.stdin)['data']; print(f'Lv{d[\"level\"]} {d[\"sect_name\"]} HP{d[\"hp\"]}/{d[\"max_hp\"]} 学{len(d.get(\"learned_skills\",[]))}招 装备{len(d.get(\"equipped_skills\",[]))}招')")
ok "$INFO"

# ─── Step 5: skills/all ───
step "Step 5: GET /api/skills/all"
RESP=$(curl -sS $HOST/api/skills/all -H "$HDR")
SCOUNT=$(echo "$RESP" | python3 -c "import sys,json; d=json.load(sys.stdin)['data']; print(f'{len(d[\"skills\"])} 招式可见, 装备槽{d[\"equipped_slots_used\"]}/{d[\"equipped_slots_max\"]}')" 2>/dev/null)
[ -z "$SCOUNT" ] && fail "Skills 失败: $RESP"
ok "$SCOUNT"

# ─── Step 6: battle/cards ───
step "Step 6: GET /api/battle/cards (战斗装备的招式)"
RESP=$(curl -sS $HOST/api/battle/cards -H "$HDR")
NCARDS=$(echo "$RESP" | python3 -c "import sys,json; d=json.load(sys.stdin)['data']; print(len(d))" 2>/dev/null)
[ -z "$NCARDS" ] || [ "$NCARDS" -lt 1 ] && fail "无战斗卡: $RESP"
ok "战斗卡 $NCARDS 张"

# ─── Step 7: explore/spawn ───
step "Step 7: GET /api/explore/spawn?count=10"
RESP=$(curl -sS "$HOST/api/explore/spawn?count=10" -H "$HDR")
SPAWNS=$(echo "$RESP" | python3 -c "
import sys, json
raw = json.load(sys.stdin)
arr = raw.get('data', raw) if isinstance(raw, dict) else raw
if not isinstance(arr, list):
    print('FAIL'); exit()
mon = [x for x in arr if not x.get('is_npc')]
npc = [x for x in arr if x.get('is_npc')]
print(f'{len(arr)} 个: {len(mon)} 怪 + {len(npc)} NPC')
" 2>/dev/null)
[ "$SPAWNS" = "FAIL" ] && fail "Spawn 失败: $RESP"
ok "$SPAWNS"

# ─── Step 8: battle/start ───
step "Step 8: POST /api/battle/start (首战 → fox_01 教学怪)"
RESP=$(curl -sS -X POST $HOST/api/battle/start \
  -H "$HDR" -H 'Content-Type: application/json' \
  -d '{"enemy_id":"fox_01","mode":"drama"}')
BATTLE_ID=$(echo "$RESP" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('data',{}).get('battle_id','FAIL'))" 2>/dev/null)
[ "$BATTLE_ID" = "FAIL" ] && fail "战斗启动失败: $RESP"
ok "战斗启动 battle_id=$BATTLE_ID"

# ─── Step 9: battle exists check ───
step "Step 9: GET /api/battle/{id} 验证战斗存活"
RESP=$(curl -sS "$HOST/api/battle/$BATTLE_ID")
EXISTS=$(echo "$RESP" | python3 -c "import sys,json; d=json.load(sys.stdin).get('data',{}); print(d.get('battle_id','FAIL'))" 2>/dev/null)
[ "$EXISTS" = "FAIL" ] && fail "战斗查询失败: $RESP"
ok "战斗存活查询通过"

# ─── Step 10: 打坐 ───
step "Step 10: POST /api/character/meditate"
RESP=$(curl -sS -X POST $HOST/api/character/meditate -H "$HDR")
MEDI=$(echo "$RESP" | python3 -c "import sys,json; d=json.load(sys.stdin)['data']; print(f'修为+{d[\"exp_gain\"]} streak={d[\"streak\"]} HP+{d[\"heal\"]}')")
ok "$MEDI"

# ─── Step 11: 修行录 ───
step "Step 11: GET /api/journal"
RESP=$(curl -sS "$HOST/api/journal?limit=5" -H "$HDR")
JCOUNT=$(echo "$RESP" | python3 -c "import sys,json; d=json.load(sys.stdin)['data']; print(f'共{d[\"total\"]}条')" 2>/dev/null)
ok "$JCOUNT"

# ─── Step 12: 背包 ───
step "Step 12: GET /api/inventory"
RESP=$(curl -sS $HOST/api/inventory -H "$HDR")
INV=$(echo "$RESP" | python3 -c "import sys,json; d=json.load(sys.stdin)['data']; print(f'背包 {len(d.get(\"items\",[]))} 个物品')" 2>/dev/null)
ok "$INV"

# ─── Step 13: 怪物图鉴 ───
step "Step 13: GET /api/bestiary"
RESP=$(curl -sS $HOST/api/bestiary -H "$HDR")
BCOUNT=$(echo "$RESP" | python3 -c "import sys,json; d=json.load(sys.stdin)['data']; print(f'图鉴 {d.get(\"total_clans\",0)} 族 / {d.get(\"discovered_count\",0)} 已发现')" 2>/dev/null)
ok "$BCOUNT"

# ─── Step 14: 配方 ───
step "Step 14: GET /api/recipes"
RESP=$(curl -sS $HOST/api/recipes -H "$HDR")
RCOUNT=$(echo "$RESP" | python3 -c "import sys,json; d=json.load(sys.stdin)['data']; print(f'{len(d)} 个配方可见')" 2>/dev/null)
ok "$RCOUNT"

# ─── Step 15: 删除测试用户 ───
step "Step 15: DELETE /api/character/me (清理测试数据)"
curl -sS -X DELETE $HOST/api/character/me -H "$HDR" > /dev/null
ok "测试用户已清理"

echo
echo "$(color 32 '═══════════════════════════════════════════════')"
echo "$(color 32 '✅ 全流程 15/15 步骤通过')"
echo "$(color 32 '═══════════════════════════════════════════════')"
