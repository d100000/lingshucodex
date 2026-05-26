#!/bin/bash
# 灵枢笔录 · 一键启动脚本

set -e

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT"

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${CYAN}  ✨ 灵枢笔录 · Lingshu Codex 启动${NC}"
echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"

# ===== 后端 =====
echo -e "\n${YELLOW}[1/3] 后端环境检查...${NC}"
cd "$ROOT/backend"

if [ ! -d ".venv" ]; then
  echo -e "${YELLOW}  → 创建 Python 虚拟环境${NC}"
  python3 -m venv .venv
fi

source .venv/bin/activate

if [ ! -f ".venv/.deps_installed" ]; then
  echo -e "${YELLOW}  → 安装后端依赖${NC}"
  pip install -q --upgrade pip
  pip install -q -r requirements.txt
  touch .venv/.deps_installed
fi

if [ ! -f ".env" ]; then
  echo -e "${RED}  ✗ 缺少 .env 文件,请复制 .env.example 并填入 LLM_API_KEY${NC}"
  exit 1
fi

echo -e "${GREEN}  ✓ 后端就绪${NC}"

# ===== 前端 =====
echo -e "\n${YELLOW}[2/3] 前端环境检查...${NC}"
cd "$ROOT/frontend"

if [ ! -d "node_modules" ]; then
  echo -e "${YELLOW}  → 安装前端依赖(可能需要 1-2 分钟)${NC}"
  npm install --silent
fi

echo -e "${GREEN}  ✓ 前端就绪${NC}"

# ===== 启动 =====
echo -e "\n${YELLOW}[3/3] 启动服务...${NC}"
echo -e ""
echo -e "${CYAN}  后端: ${GREEN}http://127.0.0.1:8020${NC}"
echo -e "${CYAN}  前端: ${GREEN}http://127.0.0.1:5173${NC}  ← ${YELLOW}在浏览器打开此地址${NC}"
echo -e ""
echo -e "${CYAN}  按 Ctrl+C 停止两个服务${NC}"
echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e ""

# 同时启动后端和前端
cd "$ROOT/backend"
source .venv/bin/activate

# 后端在后台
uvicorn app.main:app --host 127.0.0.1 --port 8020 --reload &
BACKEND_PID=$!

# 前端在前台(便于 Ctrl+C)
cd "$ROOT/frontend"

# 退出时清理
trap "kill $BACKEND_PID 2>/dev/null; exit" SIGINT SIGTERM

npm run dev

# 兜底等待
wait $BACKEND_PID
