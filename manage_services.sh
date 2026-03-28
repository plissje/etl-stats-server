#!/bin/bash

BASE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PID_FILE="$BASE_DIR/.services.pid"

start() {
    if [ -f "$PID_FILE" ]; then
        echo "Services appear to be running (PID file exists). Run 'stop' first."
        exit 1
    fi

    echo "Starting backend..."
    cd "$BASE_DIR/backend"
    if [ -d ".venv" ]; then
        source .venv/bin/activate
    fi
    nohup uvicorn app.main:app --reload --host 0.0.0.0 --port 8010 > backend.log 2>&1 &
    BACKEND_PID=$!
    echo $BACKEND_PID > "$PID_FILE"

    echo "Starting frontend..."
    cd "$BASE_DIR/frontend"
    nohup npm run dev -- --host --port 8080 > frontend.log 2>&1 &
    FRONTEND_PID=$!
    echo $FRONTEND_PID >> "$PID_FILE"

    echo "Services started!"
    echo "Backend logs: $BASE_DIR/backend/backend.log"
    echo "Frontend logs: $BASE_DIR/frontend/frontend.log"
}

stop() {
    if [ -f "$PID_FILE" ]; then
        echo "Stopping services..."
        while read pid; do
            # Send TERM signal gently
            kill -TERM "$pid" 2>/dev/null || true
        done < "$PID_FILE"
        rm -f "$PID_FILE"
    else
        echo "PID file not found. Attempting to kill by process name..."
    fi
    
    # Cleanup any lingering child processes like vite that don't die with their parent npm process
    pkill -f "uvicorn app.main:app" || true
    pkill -f "vite" || true
    
    echo "Services stopped."
}

case "$1" in
    start)
        start
        ;;
    stop)
        stop
        ;;
    restart)
        stop
        sleep 1
        start
        ;;
    *)
        echo "Usage: $0 {start|stop|restart}"
        exit 1
esac
