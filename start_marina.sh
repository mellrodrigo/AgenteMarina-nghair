#!/bin/bash
MARINA_DIR="$HOME/marina"
LOG_FILE="$MARINA_DIR/logs/marina.log"
PID_FILE="$MARINA_DIR/marina.pid"
PORT=5000

echo "========================================"
echo "  Marina - NGHair AI Agent"
echo "========================================"

if [ -f "$PID_FILE" ]; then
    PID=$(cat "$PID_FILE")
    if kill -0 "$PID" 2>/dev/null; then
        echo "Marina ja esta rodando (PID: $PID)"
        exit 0
    fi
fi

cd "$MARINA_DIR" || exit 1
source venv/bin/activate
mkdir -p data logs

echo "Iniciando Marina na porta $PORT..."
nohup gunicorn \
    --bind "0.0.0.0:$PORT" \
    --workers 2 \
    --threads 4 \
    --timeout 120 \
    --log-level info \
    --access-logfile "$MARINA_DIR/logs/access.log" \
    --error-logfile "$MARINA_DIR/logs/error.log" \
    "app.main:app" >> "$LOG_FILE" 2>&1 &

echo $! > "$PID_FILE"
sleep 2

if kill -0 "$(cat $PID_FILE)" 2>/dev/null; then
    echo "Marina iniciada! PID: $(cat $PID_FILE) | Porta: $PORT"
else
    echo "Falha ao iniciar. Verifique: tail -20 $LOG_FILE"
fi
