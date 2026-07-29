#!/bin/bash
# ============================================================
# MARINA — Instalação completa no VPS Hostinger NGHair
# Execute no terminal SSH do VPS como root
# ============================================================
set -e

GREEN='\033[0;32m'; YELLOW='\033[1;33m'; RED='\033[0;31m'; NC='\033[0m'
ok()   { echo -e "${GREEN}✔ $1${NC}"; }
step() { echo -e "${YELLOW}▶ $1${NC}"; }
err()  { echo -e "${RED}✘ $1${NC}"; }

DOMAIN="nghair.com.br"
EMAIL="mellrodrigo@gmail.com"
APP_DIR="/home/marina"
REPO="https://github.com/mellrodrigo/AgenteMarina-nghair.git"
BRANCH="claude/deploy-marina-agent-vps-GokzJ"

echo ""
echo -e "${GREEN}╔══════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║   Marina AI Agent — NGHair Setup VPS    ║${NC}"
echo -e "${GREEN}╚══════════════════════════════════════════╝${NC}"
echo ""

# ── 1. Sistema ────────────────────────────────────────────────
step "1/10 Atualizando sistema..."
export DEBIAN_FRONTEND=noninteractive
apt-get update -qq
apt-get upgrade -y -qq
apt-get install -y -qq \
    git curl wget nano htop ufw fail2ban \
    python3.11 python3.11-venv python3-pip \
    nginx certbot python3-certbot-nginx \
    docker.io docker-compose
ok "Sistema atualizado"

# ── 2. Docker ─────────────────────────────────────────────────
step "2/10 Iniciando Docker..."
systemctl enable docker --quiet
systemctl start docker
ok "Docker ativo"

# ── 3. Firewall ───────────────────────────────────────────────
step "3/10 Configurando firewall..."
ufw --force reset > /dev/null
ufw default deny incoming > /dev/null
ufw default allow outgoing > /dev/null
ufw allow ssh > /dev/null
ufw allow 80/tcp > /dev/null
ufw allow 443/tcp > /dev/null
ufw --force enable > /dev/null
ok "Firewall configurado (SSH + 80 + 443)"

# ── 4. Clonar repositório ─────────────────────────────────────
step "4/10 Clonando repositório..."
rm -rf "$APP_DIR"
git clone -b "$BRANCH" "$REPO" "$APP_DIR" --quiet
mkdir -p "$APP_DIR/data" "$APP_DIR/logs"
ok "Repositório clonado em $APP_DIR"

# ── 5. Python + gunicorn ──────────────────────────────────────
step "5/10 Instalando Python e dependências..."
python3.11 -m venv "$APP_DIR/venv"
"$APP_DIR/venv/bin/pip" install --upgrade pip --quiet
"$APP_DIR/venv/bin/pip" install -r "$APP_DIR/requirements.txt" --quiet
ok "Dependências instaladas"

# ── 6. Criar .env de produção ─────────────────────────────────
step "6/10 Criando arquivo .env..."
cat > "$APP_DIR/.env" <<'ENVEOF'
DEBUG=False
SECRET_KEY=e9e63a3c60a3b6244af18801c4e08d97a7bc5be2955a25fc7f3ed51f7ef03402

DATABASE_URL=sqlite:///./data/marina.db

TRINKS_API_KEY=akpcmh1qqz1cDXcidshh2N8Ow5XJ4Uu6cAettPA6
TRINKS_API_URL=https://api.trinks.com
TRINKS_SYNC_INTERVAL=3600

GEMINI_API_KEY=AIzaSyAjNKdBC4ewfXyyqNDzwcupHzvjvOXZ7WQ
GEMINI_MODEL=gemini-2.0-flash

EVOLUTION_API_URL=http://localhost:8080
EVOLUTION_API_KEY=1d0a8328a3cab91dea8f1276cbb95172
WHATSAPP_INSTANCE_NAME=nghair

API_HOST=0.0.0.0
API_PORT=8000
API_WEBHOOK_URL=https://nghair.com.br/webhook/whatsapp

LOG_LEVEL=INFO
LOG_FILE=logs/marina.log

MARINA_NAME=Marina
MARINA_SALAO=NGHair
MARINA_TONE=profissional e amigável

MEMORY_RETENTION_DAYS=365
MAX_CONVERSATION_HISTORY=20
ENVEOF
chmod 600 "$APP_DIR/.env"
ok ".env criado com permissões seguras"

# ── 7. Banco de dados ─────────────────────────────────────────
step "7/10 Inicializando banco de dados..."
cd "$APP_DIR"
"$APP_DIR/venv/bin/python3" -c "from app.models.database import criar_tabelas; criar_tabelas()"
ok "Banco SQLite inicializado"

# ── 8. Evolution API (Docker / WhatsApp) ──────────────────────
step "8/10 Iniciando Evolution API (WhatsApp)..."
cd "$APP_DIR"
# Injetar API key no docker-compose antes de subir
EVOL_KEY="1d0a8328a3cab91dea8f1276cbb95172"
WEBHOOK="https://nghair.com.br/webhook/whatsapp"
EVOLUTION_API_KEY="$EVOL_KEY" API_WEBHOOK_URL="$WEBHOOK" docker-compose up -d evolution-api
sleep 6

if docker inspect --format='{{.State.Status}}' evolution-api 2>/dev/null | grep -q "running"; then
    ok "Evolution API rodando (porta 8080)"
else
    err "Evolution API não iniciou — verifique: docker logs evolution-api"
fi

# ── 9. Systemd — Marina ───────────────────────────────────────
step "9/10 Criando serviço systemd da Marina..."
cat > /etc/systemd/system/marina.service <<SVCEOF
[Unit]
Description=Marina AI Agent — NGHair
After=network.target docker.service

[Service]
User=root
WorkingDirectory=$APP_DIR
EnvironmentFile=$APP_DIR/.env
ExecStart=$APP_DIR/venv/bin/gunicorn app.main:app \\
    --bind 127.0.0.1:8000 \\
    --workers 2 \\
    --threads 4 \\
    --timeout 120 \\
    --access-logfile $APP_DIR/logs/access.log \\
    --error-logfile $APP_DIR/logs/error.log \\
    --log-level info
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
SVCEOF

systemctl daemon-reload
systemctl enable marina --quiet
systemctl start marina
sleep 3

if systemctl is-active --quiet marina; then
    ok "Marina iniciada (porta 8000)"
else
    err "Marina não iniciou — veja: journalctl -u marina -n 30"
    journalctl -u marina -n 20 --no-pager
    exit 1
fi

# ── 10. Nginx + SSL ───────────────────────────────────────────
step "10/10 Configurando Nginx + SSL (Let's Encrypt)..."
# Config inicial HTTP para certbot funcionar
cat > /etc/nginx/sites-available/marina <<NGXEOF
server {
    listen 80;
    server_name $DOMAIN www.$DOMAIN;
    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        proxy_read_timeout 120;
    }
    access_log /var/log/nginx/marina_access.log;
    error_log  /var/log/nginx/marina_error.log;
}
NGXEOF

ln -sf /etc/nginx/sites-available/marina /etc/nginx/sites-enabled/marina
rm -f /etc/nginx/sites-enabled/default
nginx -t && systemctl restart nginx

# SSL
certbot --nginx -d "$DOMAIN" -d "www.$DOMAIN" \
    --non-interactive --agree-tos -m "$EMAIL" --redirect \
    && ok "SSL configurado com Let's Encrypt" \
    || echo -e "${YELLOW}  ⚠ SSL manual: certbot --nginx -d $DOMAIN${NC}"

# ── Resumo ────────────────────────────────────────────────────
echo ""
echo -e "${GREEN}╔══════════════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║   ✅  Marina instalada com sucesso!                  ║${NC}"
echo -e "${GREEN}╚══════════════════════════════════════════════════════╝${NC}"
echo ""
echo "  🌐 Health check:   curl https://$DOMAIN/health"
echo "  🔗 Trinks status:  curl https://$DOMAIN/trinks/status"
echo "  📊 Status geral:   curl https://$DOMAIN/status"
echo ""
echo "  ── WhatsApp (próximo passo) ──────────────────────────"
echo "  QR Code para conectar o WhatsApp:"
echo "  curl -s http://localhost:8080/instance/connect/nghair \\"
echo "       -H 'apikey: 1d0a8328a3cab91dea8f1276cbb95172'"
echo ""
echo "  ── Logs ──────────────────────────────────────────────"
echo "  journalctl -u marina -f"
echo "  docker logs -f evolution-api"
echo "  tail -f $APP_DIR/logs/marina.log"
echo ""
echo -e "${YELLOW}  ⚠ Troque a senha root: passwd root${NC}"
echo ""
