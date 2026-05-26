#!/bin/bash
# 灵枢笔录服务管理 — backend / frontend 独立运行,不会相互拖累
#
# 用法:
#   bash scripts/svc.sh status    # 看 backend/frontend 端口 + pid
#   bash scripts/svc.sh start     # 启动两者(已运行的跳过)
#   bash scripts/svc.sh stop      # 全停
#   bash scripts/svc.sh restart-back  # 只重启 backend(不动 frontend)
#   bash scripts/svc.sh restart-front # 只重启 frontend
#   bash scripts/svc.sh restart   # 都重启
#   bash scripts/svc.sh logs      # tail backend + frontend 日志

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
BACK_LOG=/tmp/lingshu-back.log
FRONT_LOG=/tmp/lingshu-fe.log

GREEN='\033[0;32m'; YELLOW='\033[1;33m'; RED='\033[0;31m'; CYAN='\033[0;36m'; NC='\033[0m'

cmd=${1:-status}

port_pid() {
  lsof -ti :"$1" 2>/dev/null | head -1
}

status() {
  echo -e "${CYAN}━━━━━━━━━━━ 服务状态 ━━━━━━━━━━━${NC}"
  local bp=$(port_pid 8020); local fp=$(port_pid 5173)
  [ -n "$bp" ] && echo -e "${GREEN}✓${NC} Backend  8020  pid=$bp" || echo -e "${RED}✗${NC} Backend  8020  (down)"
  [ -n "$fp" ] && echo -e "${GREEN}✓${NC} Frontend 5173  pid=$fp" || echo -e "${RED}✗${NC} Frontend 5173  (down)"
  [ -n "$bp" ] && curl -s http://127.0.0.1:8020/health > /dev/null && echo -e "${GREEN}  ↳ /health OK${NC}"
  [ -n "$fp" ] && curl -so /dev/null -w "  ↳ frontend HTTP %{http_code}\n" http://127.0.0.1:5173/
}

start_back() {
  if [ -n "$(port_pid 8020)" ]; then
    echo -e "${YELLOW}backend 已在运行(8020)${NC}"; return
  fi
  cd "$ROOT/backend" && source .venv/bin/activate
  nohup uvicorn app.main:app --host 127.0.0.1 --port 8020 --reload > "$BACK_LOG" 2>&1 &
  disown
  echo -e "${GREEN}✓ backend started${NC} (log: $BACK_LOG)"
}

start_front() {
  if [ -n "$(port_pid 5173)" ]; then
    echo -e "${YELLOW}frontend 已在运行(5173)${NC}"; return
  fi
  cd "$ROOT/frontend"
  nohup npm run dev > "$FRONT_LOG" 2>&1 &
  disown
  echo -e "${GREEN}✓ frontend started${NC} (log: $FRONT_LOG)"
}

stop_back() {
  local p=$(port_pid 8020)
  [ -n "$p" ] && kill "$p" 2>/dev/null && echo -e "${YELLOW}backend pid=$p stopped${NC}"
}

stop_front() {
  local p=$(port_pid 5173)
  [ -n "$p" ] && kill "$p" 2>/dev/null && echo -e "${YELLOW}frontend pid=$p stopped${NC}"
}

case "$cmd" in
  status)         status ;;
  start)          start_back; start_front; sleep 2; status ;;
  stop)           stop_back; stop_front ;;
  restart)        stop_back; stop_front; sleep 1; start_back; start_front; sleep 2; status ;;
  restart-back)   stop_back; sleep 1; start_back; sleep 2; status ;;
  restart-front)  stop_front; sleep 1; start_front; sleep 2; status ;;
  logs)           tail -F "$BACK_LOG" "$FRONT_LOG" ;;
  *)
    echo "usage: bash $0 {status|start|stop|restart|restart-back|restart-front|logs}"
    ;;
esac
