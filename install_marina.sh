#!/bin/bash
set -e
MARINA_DIR="$HOME/marina"
echo "========================================"
echo "  Instalando Marina - NGHair"
echo "========================================"

mkdir -p "$MARINA_DIR/data" "$MARINA_DIR/logs"

if [ -d "$MARINA_DIR/.git" ]; then
    echo "Atualizando repositorio..."
    cd "$MARINA_DIR" && git pull origin main
else
    echo "Clonando repositorio..."
    git clone https://github.com/mellrodrigo/AgenteMarina-nghair.git "$MARINA_DIR"
    cd "$MARINA_DIR"
fi

echo "Criando ambiente virtual Python..."
python3 -m venv venv
source venv/bin/activate

echo "Instalando dependencias..."
pip install --upgrade pip setuptools wheel -q
pip install -r requirements.txt -q

if [ ! -f ".env" ]; then
    cp .env.example .env
    echo "ATENCAO: Edite o .env com suas configuracoes: nano $MARINA_DIR/.env"
fi

echo "Inicializando banco de dados..."
python3 -c "from app.models.database import criar_tabelas; criar_tabelas(); print('OK')"

chmod +x start_marina.sh stop_marina.sh status_marina.sh

echo ""
echo "========================================"
echo "Instalacao concluida!"
echo "Proximos passos:"
echo "1. nano $MARINA_DIR/.env"
echo "2. bash $MARINA_DIR/start_marina.sh"
echo "========================================"
