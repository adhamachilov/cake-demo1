#!/usr/bin/env bash
# Run the bot in the background, independent of any terminal or editor session.
#   ./bot.sh start | stop | restart | status | logs
cd "$(dirname "$0")" || exit 1
PIDFILE=data/bot.pid
LOG=data/bot.log
PY=.venv/bin/python

running() { [ -f "$PIDFILE" ] && kill -0 "$(cat "$PIDFILE")" 2>/dev/null; }

case "$1" in
  start)
    if running; then echo "Already running (pid $(cat "$PIDFILE"))."; exit 0; fi
    mkdir -p data
    echo "----- $(date '+%F %T') start" >> "$LOG"
    nohup setsid "$PY" -m bot >> "$LOG" 2>&1 < /dev/null &
    sleep 1
    pgrep -n -f "$PY -m bot" > "$PIDFILE"
    echo "Started (pid $(cat "$PIDFILE")). Waiting for the Mini App address..."
    for _ in $(seq 1 40); do grep -q "is running" <(tail -n 30 "$LOG") && break; sleep 1; done
    tail -n 30 "$LOG" | grep -E "is running|online at|Tunnel via|ERROR|error" | tail -n 4
    ;;
  stop)
    if ! running; then echo "Not running."; rm -f "$PIDFILE"; exit 0; fi
    kill -INT "$(cat "$PIDFILE")"   # graceful: finishes sends, hands the menu button to the showcase
    for _ in $(seq 1 30); do running || break; sleep 1; done
    running && kill "$(cat "$PIDFILE")"
    rm -f "$PIDFILE"
    echo "Stopped."
    ;;
  restart) "$0" stop; "$0" start ;;
  status) if running; then echo "Running (pid $(cat "$PIDFILE"))."; else echo "Not running."; fi ;;
  logs) tail -n 50 -f "$LOG" ;;
  *) echo "Usage: ./bot.sh start | stop | restart | status | logs"; exit 1 ;;
esac
