#!/bin/bash
PID_FILE="$HOME/marina/marina.pid"
if [ -f "$PID_FILE" ]; then
    PID=$(cat "$PID_FILE")
    if kill -0 "$PID" 2>/dev/null; then
        kill "$PID" && rm -f "$PID_FILE" && echo "Marina parada (PID: $PID)"
    else
        rm -f "$PID_FILE" && echo "Marina nao estava rodando"
    fi
else
    echo "Arquivo PID nao encontrado"
fi
