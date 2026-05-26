# 灵枢笔录 · Lingshu Codex

> 一款 Web 版国风修仙文字 RPG。**门派 = LLM 厂商,境界 = 模型档位**。
> 玩家选派之后,每场战斗由 LLM 实时生成 200 字仙侠叙事;数值结算由后端权威计算。
> 零动画美术,所有视觉反馈靠静态立绘 + 屏幕震动 + 文字流。

---

## ✨ MVP 特性(本版本)

- ✅ 选派(沧澜剑派 / 天机阁 可用,其余 3 派 UI 占位)
- ✅ 主城界面:角色 / HP / 灵气 / 经验 + 敌人选择
- ✅ 战斗系统:回合制 + 卡牌 + LLM 实时叙事(打字机效果)
- ✅ 屏幕反馈:震动、闪光、数字飞屏、立绘抖动
- ✅ WebSocket 实时通信
- ✅ 5 个代表性敌人(山林狐妖 → 天魔王)
- ✅ 8 张战斗卡牌(通用 4 张 + 门派专属 2 张 × 2 派)
- ✅ Fallback 兜底(LLM 失败时用预设模板,不中断游戏)

---

## 🚀 一键启动

### 前置要求
- Python 3.11+
- Node.js 18+
- 一个 bobdong.cn 的 API Key(已在 `backend/.env` 配好测试用 key)

### 启动

```bash
cd ~/项目/LingshuCodex
./start.sh
```

脚本会自动:
1. 创建 Python 虚拟环境 + 装后端依赖
2. 装前端 npm 依赖
3. 同时启动后端(8020) + 前端(5173)

打开浏览器:**http://127.0.0.1:5173**

### 手动启动(如果脚本不工作)

```bash
# Terminal 1 - 后端
cd backend
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --host 127.0.0.1 --port 8020 --reload

# Terminal 2 - 前端
cd frontend
npm install
npm run dev
```

---

## 🎮 体验流程

1. **选派**:打开后看到 5 派立绘,选"沧澜剑派"或"天机阁"
2. **入门**:输入道号,确认加入(弹窗"师承不可背叛"二次确认)
3. **主城**:看到角色卡 + 5 个可挑战敌人
4. **战斗**:点击"山林狐妖" → 进入战斗页
5. **出招**:点击底部"剑诀·初"等卡牌 → LLM 实时生成战斗叙事
6. **结算**:战胜后获得经验 / 灵气 → 返回主城

---

## 📁 目录结构

```
LingshuCodex/
├── start.sh                    # 一键启动脚本
├── README.md                   # 本文件
├── .gitignore
│
├── backend/                    # Python FastAPI 后端
│   ├── requirements.txt
│   ├── .env                    # 已配置测试 key
│   ├── .env.example
│   └── app/
│       ├── main.py             # FastAPI 入口 + REST + WebSocket
│       ├── sects.py            # 5 门派配置
│       ├── enemies.py          # 敌人配置
│       ├── cards.py            # 战斗卡牌
│       ├── battle.py           # 战斗引擎(数值 + LLM)
│       ├── llm_client.py       # LLM 调用 + fallback
│       └── store.py            # 内存存储(MVP)
│
└── frontend/                   # Vue 3 + Naive UI 前端
    ├── package.json
    ├── vite.config.js
    ├── index.html
    └── src/
        ├── main.js
        ├── App.vue
        ├── router.js
        ├── api/client.js       # axios 客户端
        ├── stores/game.js      # Pinia 全局状态
        └── views/
            ├── SectChoose.vue  # 选派页
            ├── Home.vue        # 主城页
            └── Battle.vue      # 战斗页
```

---

## 🔧 核心技术栈

| 模块 | 技术 |
|---|---|
| 后端 | FastAPI + Pydantic + httpx + python-dotenv |
| 前端 | Vue 3 + Naive UI + Pinia + Vite |
| 实时通信 | WebSocket(原生)|
| LLM 网关 | bobdong.cn(OpenAI 兼容协议) |
| 模型 | Claude 4.5/4.6/4.7 + GPT 5.4/5.5 |
| 部署 | 暂未做(MVP 本地运行) |

---

## 🎨 5 大门派 ↔ LLM 厂商

| 门派 | LLM 厂商 | 当前可用模型(bobdong.cn) | MVP 状态 |
|---|---|---|---|
| 🗡️ 沧澜剑派 | Anthropic | claude-haiku-4-5 → sonnet-4-6 → opus-4-6/4-7 | ✅ 可用 |
| ⚙️ 天机阁 | OpenAI | gpt-5.4-mini → gpt-5.4 → gpt-5.5 | ✅ 可用 |
| 🧠 玄机宗 | DeepSeek | — | ⏳ 待开放 |
| 📜 青冥派 | 智谱 GLM | — | ⏳ 待开放 |
| 🌙 月隐宫 | Kimi | — | ⏳ 待开放 |

---

## 🔐 安全提示

- `backend/.env` 文件包含真实 API Key,**不要提交到 Git**(已加入 .gitignore)
- 生产环境部署时,API Key 应通过环境变量或 KMS 注入,不要写文件
- MVP 版本未实现 BYOK 加密,**仅适合本地测试**
- 完整 BYOK 架构见 `~/项目/FireworkRouter/docs/game-plan/04-byok-architecture.md`

---

## 🐞 常见问题

### 启动报错 "ModuleNotFoundError: No module named 'fastapi'"
进入 backend 目录,激活虚拟环境:
```bash
cd backend && source .venv/bin/activate
pip install -r requirements.txt
```

### 前端启动报错
检查 Node.js 版本:
```bash
node -v   # 需要 18+
```

### LLM 调用超时 / 报错
检查:
- `backend/.env` 中的 `LLM_API_KEY` 是否正确
- 网络是否能访问 `bobdong.cn`
- 后台日志会显示 `[LLM Fallback]` 字样(此时会用预设叙事兜底,不影响战斗)

### 战斗界面没有叙事
F12 看浏览器 Console:
- 看 WS 连接是否建立(`ws://127.0.0.1:8020/ws/battle/...`)
- 看是否有 `narration` 事件

---

## 📚 设计文档

完整设计文档在 `~/项目/FireworkRouter/docs/game-plan/`:

- `00-README.md` — 文档总入口
- `11-PRD-final.md` — 完整 PRD ⭐
- `10-sect-system.md` — 5 大门派完整设计 ⭐
- `01-game-design.md` 至 `09-risks.md` — 各方面详细设计
- `prompts/` — 出图 + LLM 战斗 prompt 库

---

## 🛣️ 后续扩展(超出 MVP)

按优先级排序:

1. **接入更多 LLM**(DeepSeek / GLM / Kimi)→ 解锁玄机/青冥/月隐 3 派
2. **真 BYOK**(玩家自己填 Key + RSA + AES 加密)
3. **持久化**(SQLite / Postgres + Alembic 迁移)
4. **8 大养成线**(笔器、笔魂、笔灵、灵兽、砚田、道相、印纽)
5. **更多副本**(爬塔 / Boss / PVP)
6. **AI 美术**(用 SiliconFlow Flux 出立绘 / 场景)
7. **商业化**(月卡 / 抽卡 / 终身卡)
8. **多账号** + **JWT 登录**

---

## 📜 License

MIT(or whatever you prefer)

---

**最后更新**:2026-05-24
**版本**:v0.1.0 (MVP)
**作者**:bobdong
