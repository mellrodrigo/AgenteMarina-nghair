#!/bin/bash
PID_FILE="$HOME/marina/marina.pid"
echo "========================================"
echo "  Status da Marina - NGHair"
echo "========================================"
if [ -f "$PID_FILE" ]; then
    PID=$(cat "$PID_FILE")
    if kill -0 "$PID" 2>/dev/null; then
        echo "STATUS: ONLINE (PID: $PID)"
    else
        echo "STATUS: OFFLINE (PID antigo: $PID)"
    fi
else
    echo "STATUS: OFFLINE"
fi
echo ""
echo "Ultimas linhas do log:"
tail -20 "$HOME/marina/logs/marina.log" 2>/dev/null || echo "Sem logs"
