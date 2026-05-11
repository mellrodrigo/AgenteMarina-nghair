#!/bin/bash
# Script de deployment da Marina no VPS Hostinger
# Executar como root: bash deploy.sh
# Para setup inicial do VPS use: bash setup_vps.sh

set -e

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

APP_DIR="/home/marina"
VENV_DIR="$APP_DIR/venv"
SERVICE_NAME="marina"
REPO_URL="${REPO_URL:-}"

echo -e "${GREEN}╔══════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║   Marina AI Agent — Deploy NGHair        ║${NC}"
echo -e "${GREEN}╚══════════════════════════════════════════╝${NC}"
echo ""

# 1. Criar/atualizar diretório da aplicação
echo -e "${YELLOW}[1/8]${NC} Preparando diretório da aplicação..."
mkdir -p "$APP_DIR/data" "$APP_DIR/logs"

if [ -n "$REPO_URL" ]; then
    if [ -d "$APP_DIR/.git" ]; then
        echo "  Atualizando repositório..."
        git -C "$APP_DIR" pull origin main
    else
        echo "  Clonando repositório..."
        git clone "$REPO_URL" "$APP_DIR"
    fi
else
    echo "  Copiando arquivos do diretório atual..."
    rsync -av --exclude='.git' --exclude='venv' --exclude='__pycache__' \
          --exclude='*.pyc' --exclude='data/*.db' \
          ./ "$APP_DIR/"
fi

# 2. Criar ambiente virtual Python
echo -e "${YELLOW}[2/8]${NC} Criando ambiente virtual Python..."
python3 -m venv "$VENV_DIR"

# 3. Instalar dependências
echo -e "${YELLOW}[3/8]${NC} Instalando dependências Python..."
"$VENV_DIR/bin/pip" install --upgrade pip --quiet
"$VENV_DIR/bin/pip" install -r "$APP_DIR/requirements.txt" --quiet
"$VENV_DIR/bin/pip" install gunicorn --quiet

# 4. Verificar arquivo .env
echo -e "${YELLOW}[4/8]${NC} Verificando arquivo .env..."
if [ ! -f "$APP_DIR/.env" ]; then
    echo -e "${RED}  ATENÇÃO: Arquivo .env não encontrado!${NC}"
    echo "  Execute: cp $APP_DIR/.env.example $APP_DIR/.env && nano $APP_DIR/.env"
    exit 1
fi

# Verificar variáveis críticas
source "$APP_DIR/.env"
MISSING=()
[ -z "$GEMINI_API_KEY" ]     && MISSING+=("GEMINI_API_KEY")
[ -z "$TRINKS_API_KEY" ]     && MISSING+=("TRINKS_API_KEY")
[ -z "$EVOLUTION_API_KEY" ]  && MISSING+=("EVOLUTION_API_KEY")
[ -z "$API_WEBHOOK_URL" ]    && MISSING+=("API_WEBHOOK_URL")
[ -z "$SECRET_KEY" ]         && MISSING+=("SECRET_KEY")

if [ ${#MISSING[@]} -gt 0 ]; then
    echo -e "${RED}  ATENÇÃO: Variáveis obrigatórias não configuradas:${NC}"
    for v in "${MISSING[@]}"; do echo "    - $v"; done
    echo "  Edite o arquivo: nano $APP_DIR/.env"
    exit 1
fi

# 5. Inicializar banco de dados
echo -e "${YELLOW}[5/8]${NC} Inicializando banco de dados..."
cd "$APP_DIR"
"$VENV_DIR/bin/python3" -c "from app.models.database import criar_tabelas; criar_tabelas()"

# 6. Definir permissões
echo -e "${YELLOW}[6/8]${NC} Configurando permissões..."
chmod 600 "$APP_DIR/.env"
chmod -R 755 "$APP_DIR"

# 7. Criar serviço systemd (gunicorn + Flask)
echo -e "${YELLOW}[7/8]${NC} Configurando serviço systemd..."
cat > /etc/systemd/system/$SERVICE_NAME.service <<EOF
[Unit]
Description=Marina AI Agent — NGHair
After=network.target

[Service]
User=root
WorkingDirectory=$APP_DIR
EnvironmentFile=$APP_DIR/.env
ExecStart=$VENV_DIR/bin/gunicorn app.main:app \
    --bind 0.0.0.0:8000 \
    --workers 2 \
    --threads 4 \
    --timeout 120 \
    --access-logfile $APP_DIR/logs/access.log \
    --error-logfile $APP_DIR/logs/error.log \
    --log-level info
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
EOF

# 8. Iniciar serviço
echo -e "${YELLOW}[8/8]${NC} Iniciando serviço Marina..."
systemctl daemon-reload
systemctl enable $SERVICE_NAME
systemctl restart $SERVICE_NAME

sleep 3
if systemctl is-active --quiet $SERVICE_NAME; then
    echo ""
    echo -e "${GREEN}✅ Marina está rodando!${NC}"
    echo ""
    echo "  Health check:  curl http://localhost:8000/health"
    echo "  Logs:          journalctl -u marina -f"
    echo "  Status Trinks: curl http://localhost:8000/trinks/status"
    echo ""
else
    echo -e "${RED}❌ Falha ao iniciar Marina${NC}"
    journalctl -u $SERVICE_NAME -n 30 --no-pager
    exit 1
fi
