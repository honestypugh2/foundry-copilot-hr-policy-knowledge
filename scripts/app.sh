#!/usr/bin/env bash
# Start/stop the Benchmark Workbench: FastAPI backend (:8000) + Vite frontend (:5174).
# Usage: scripts/app.sh {start|stop|restart|status|logs}
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

BACKEND_HOST="127.0.0.1"
BACKEND_PORT="8000"
FRONTEND_PORT="5174"
VENV="$ROOT/.venv"
RUN_DIR="$ROOT/.run"
BACKEND_PID="$RUN_DIR/backend.pid"
FRONTEND_PID="$RUN_DIR/frontend.pid"
BACKEND_LOG="$RUN_DIR/backend.log"
FRONTEND_LOG="$RUN_DIR/frontend.log"

mkdir -p "$RUN_DIR"

port_pids() { # $1=port -> space-separated listening pids; always exits 0
  local pids=""
  if command -v lsof >/dev/null 2>&1; then
    pids="$(lsof -ti "tcp:$1" -sTCP:LISTEN 2>/dev/null || true)"
  elif command -v fuser >/dev/null 2>&1; then
    pids="$(fuser "$1/tcp" 2>/dev/null || true)"
  fi
  printf '%s' "$pids" | tr '\n' ' '
  return 0
}

wait_http() { # $1=url $2=timeout_s
  local url="$1" timeout="${2:-40}" i=0
  while (( i < timeout )); do
    if curl -fsS -o /dev/null "$url" 2>/dev/null; then return 0; fi
    sleep 1; ((i++))
  done
  return 1
}

start_backend() {
  if [[ -n "$(port_pids "$BACKEND_PORT")" ]]; then
    echo "backend already listening on :$BACKEND_PORT"; return
  fi
  [[ -x "$VENV/bin/python" ]] || {
    echo "ERROR: venv not found at $VENV (create with: python -m venv .venv && .venv/bin/pip install -e .)"; exit 1; }
  echo "starting backend -> http://$BACKEND_HOST:$BACKEND_PORT"
  ENABLE_TRACING=false USE_AZURE_SERVICES=false \
    BENCHMARK_ARTIFACT_DIR="$ROOT/experiments/reports" \
    nohup "$VENV/bin/python" -m uvicorn src.backend.main:app \
      --host "$BACKEND_HOST" --port "$BACKEND_PORT" >"$BACKEND_LOG" 2>&1 &
  echo $! >"$BACKEND_PID"
}

start_frontend() {
  if [[ -n "$(port_pids "$FRONTEND_PORT")" ]]; then
    echo "frontend already listening on :$FRONTEND_PORT"; return
  fi
  command -v npm >/dev/null 2>&1 || { echo "ERROR: npm not found"; exit 1; }
  if [[ ! -d "$ROOT/src/frontend/node_modules" ]]; then
    echo "installing frontend dependencies (npm install)..."
    (cd "$ROOT/src/frontend" && npm install)
  fi
  echo "starting frontend -> http://$BACKEND_HOST:$FRONTEND_PORT"
  nohup npm --prefix "$ROOT/src/frontend" run dev -- \
    --host "$BACKEND_HOST" --port "$FRONTEND_PORT" --strictPort >"$FRONTEND_LOG" 2>&1 &
  echo $! >"$FRONTEND_PID"
}

stop_one() { # $1=name $2=pidfile $3=port
  local name="$1" pf="$2" port="$3" acted=0 pid
  if [[ -f "$pf" ]]; then
    pid="$(cat "$pf" 2>/dev/null || true)"
    if [[ -n "${pid:-}" ]] && kill -0 "$pid" 2>/dev/null; then
      pkill -TERM -P "$pid" 2>/dev/null || true
      kill -TERM "$pid" 2>/dev/null || true
      acted=1
    fi
    rm -f "$pf"
  fi
  local pp; pp="$(port_pids "$port")"
  if [[ -n "$pp" ]]; then kill -TERM $pp 2>/dev/null || true; acted=1; fi
  sleep 1
  pp="$(port_pids "$port")"
  if [[ -n "$pp" ]]; then kill -KILL $pp 2>/dev/null || true; fi
  [[ "$acted" -eq 1 ]] && echo "stopped $name" || echo "$name not running"
  return 0
}

status() {
  local bp fp
  bp="$(port_pids "$BACKEND_PORT")"; fp="$(port_pids "$FRONTEND_PORT")"
  if [[ -n "$bp" ]] && curl -fsS -o /dev/null "http://$BACKEND_HOST:$BACKEND_PORT/api/benchmarking/experiments" 2>/dev/null; then
    echo "backend : RUNNING (:$BACKEND_PORT pid $bp)"
  elif [[ -n "$bp" ]]; then
    echo "backend : PORT OPEN but not answering (:$BACKEND_PORT pid $bp) — see $BACKEND_LOG"
  else
    echo "backend : stopped"
  fi
  if [[ -n "$fp" ]] && curl -fsS -o /dev/null "http://$BACKEND_HOST:$FRONTEND_PORT/" 2>/dev/null; then
    echo "frontend: RUNNING (:$FRONTEND_PORT pid $fp)"
  elif [[ -n "$fp" ]]; then
    echo "frontend: PORT OPEN but not answering (:$FRONTEND_PORT pid $fp) — see $FRONTEND_LOG"
  else
    echo "frontend: stopped"
  fi
}

case "${1:-}" in
  start)
    start_backend
    if wait_http "http://$BACKEND_HOST:$BACKEND_PORT/api/benchmarking/experiments" 40; then
      echo "backend ready"
    else
      echo "WARNING: backend did not answer in time; see $BACKEND_LOG"
    fi
    start_frontend
    if wait_http "http://$BACKEND_HOST:$FRONTEND_PORT/" 40; then
      echo ""
      echo "Workbench ready -> http://$BACKEND_HOST:$FRONTEND_PORT"
    else
      echo "WARNING: frontend did not answer in time; see $FRONTEND_LOG"
    fi
    ;;
  stop)
    stop_one frontend "$FRONTEND_PID" "$FRONTEND_PORT"
    stop_one backend "$BACKEND_PID" "$BACKEND_PORT"
    ;;
  restart)
    "$0" stop; "$0" start
    ;;
  status)
    status
    ;;
  logs)
    echo "== backend ($BACKEND_LOG) =="; tail -n 40 "$BACKEND_LOG" 2>/dev/null || echo "(none)"
    echo "== frontend ($FRONTEND_LOG) =="; tail -n 40 "$FRONTEND_LOG" 2>/dev/null || echo "(none)"
    ;;
  *)
    echo "Usage: scripts/app.sh {start|stop|restart|status|logs}"; exit 1
    ;;
esac
