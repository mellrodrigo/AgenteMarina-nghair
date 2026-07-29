#!/bin/bash
# ============================================================
# Setup completo do VPS Hostinger para a Marina AI Agent
# Sistema: Ubuntu 22.04 LTS
# Executar como root: bash setup_vps.sh
# ============================================================

set -e

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
RED='\033[0;31m'
NC='\033[0m'

# ── Configurações — altere antes de executar ──────────────────
DOMAIN="${DOMAIN:-seu-dominio.com}"
EMAIL_CERTBOT="${EMAIL_CERTBOT:-seu-email@gmail.com}"
APP_DIR="/home/marina"
REPO_URL="${REPO_URL:-}"
# ─────────────────────────────────────────────────────────────

banner() {
    echo ""
    echo -e "${BLUE}══════════════════════════════════════════════════${NC}"
    echo -e "${BLUE}  $1${NC}"
    echo -e "${BLUE}══════════════════════════════════════════════════${NC}"
    echo ""
}

step() {
    echo -e "${YELLOW}▶ $1${NC}"
}

ok() {
    echo -e "${GREEN}✔ $1${NC}"
}

banner "Marina AI Agent — Setup VPS Hostinger"
echo "  Domínio: $DOMAIN"
echo "  App dir: $APP_DIR"
echo ""

# ── 1. Sistema ────────────────────────────────────────────────
banner "1/9 · Atualizando sistema"
apt update -qq && apt upgrade -y -qq
apt install -y -qq \
    build-essential git curl wget nano htop \
    python3.11 python3.11-venv python3-pip \
    nginx certbot python3-certbot-nginx \
    docker.io docker-compose \
    ufw fail2ban
ok "Sistema atualizado"

# ── 2. Firewall ───────────────────────────────────────────────
banner "2/9 · Configurando firewall (UFW)"
ufw --force reset
ufw default deny incoming
ufw default allow outgoing
ufw allow ssh
ufw allow 80/tcp
ufw allow 443/tcp
ufw --force enable
ok "Firewall configurado"

# ── 3. Docker ─────────────────────────────────────────────────
banner "3/9 · Configurando Docker"
systemctl enable docker
systemctl start docker
ok "Docker ativo"

# ── 4. Clonar / copiar aplicação ──────────────────────────────
banner "4/9 · Instalando aplicação Marina"
mkdir -p "$APP_DIR/data" "$APP_DIR/logs"

if [ -n "$REPO_URL" ]; then
    step "Clonando repositório..."
    git clone "$REPO_URL" "$APP_DIR"
else
    step "Copiando arquivos do diretório atual..."
    rsync -av --exclude='.git' --exclude='venv' --exclude='__pycache__' \
          --exclude='*.pyc' --exclude='data/*.db' \
          ./ "$APP_DIR/"
fi
ok "Arquivos instalados em $APP_DIR"

# ── 5. Python + dependências ──────────────────────────────────
banner "5/9 · Instalando dependências Python"
python3.11 -m venv "$APP_DIR/venv"
"$APP_DIR/venv/bin/pip" install --upgrade pip --quiet
"$APP_DIR/venv/bin/pip" install -r "$APP_DIR/requirements.txt" --quiet
"$APP_DIR/venv/bin/pip" install gunicorn --quiet
ok "Python e dependências instalados"

# ── 6. Arquivo .env ───────────────────────────────────────────
banner "6/9 · Configurando variáveis de ambiente"
if [ ! -f "$APP_DIR/.env" ]; then
    cp "$APP_DIR/.env.example" "$APP_DIR/.env"
    # Gerar SECRET_KEY automático
    SECRET=$(openssl rand -hex 32)
    sed -i "s/gere-com-openssl-rand-hex-32/$SECRET/" "$APP_DIR/.env"
    sed -i "s/seu-dominio.com/$DOMAIN/g" "$APP_DIR/.env"
    chmod 600 "$APP_DIR/.env"
    echo ""
    echo -e "${RED}  ⚠️  AÇÃO NECESSÁRIA: edite o arquivo .env com suas chaves de API${NC}"
    echo "  Execute: nano $APP_DIR/.env"
    echo ""
    echo "  Variáveis obrigatórias:"
    echo "    TRINKS_API_KEY   — token em trinks.com/MinhaArea/MeuCadastro"
    echo "    GEMINI_API_KEY   — chave do Google AI Studio"
    echo "    EVOLUTION_API_KEY — gerada no painel da Evolution API"
    echo ""
    read -p "  Pressione Enter quando terminar de editar o .env..."
fi

source "$APP_DIR/.env"
MISSING=()
[ -z "$GEMINI_API_KEY" ]     && MISSING+=("GEMINI_API_KEY")
[ -z "$TRINKS_API_KEY" ]     && MISSING+=("TRINKS_API_KEY")
[ -z "$EVOLUTION_API_KEY" ]  && MISSING+=("EVOLUTION_API_KEY")

if [ ${#MISSING[@]} -gt 0 ]; then
    echo -e "${RED}  ❌ Variáveis não configuradas: ${MISSING[*]}${NC}"
    echo "  Edite: nano $APP_DIR/.env"
    exit 1
fi
ok ".env configurado"

# ── 7. Banco de dados ─────────────────────────────────────────
banner "7/9 · Inicializando banco de dados"
cd "$APP_DIR"
"$APP_DIR/venv/bin/python3" -c "from app.models.database import criar_tabelas; criar_tabelas()"
ok "Banco de dados inicializado"

# ── 8. Evolution API (Docker) ─────────────────────────────────
banner "8/9 · Iniciando Evolution API (WhatsApp)"
cd "$APP_DIR"
# Atualizar webhook URL no docker-compose com o domínio real
sed -i "s|http://localhost:8000|https://$DOMAIN|g" docker-compose.yml
docker-compose up -d evolution-api
sleep 5

EVOL_STATUS=$(docker inspect --format='{{.State.Status}}' evolution-api 2>/dev/null || echo "error")
if [ "$EVOL_STATUS" = "running" ]; then
    ok "Evolution API rodando na porta 8080"
else
    echo -e "${RED}  ⚠️  Evolution API não iniciou — verifique: docker logs evolution-api${NC}"
fi

# ── 9. Marina + Nginx + SSL ───────────────────────────────────
banner "9/9 · Configurando Marina + Nginx + SSL"

# Serviço systemd da Marina
cat > /etc/systemd/system/marina.service <<EOF
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
EOF

# Nginx — configuração inicial HTTP (sem SSL, para o certbot funcionar)
cat > /etc/nginx/sites-available/marina <<EOF
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
EOF

ln -sf /etc/nginx/sites-available/marina /etc/nginx/sites-enabled/marina
rm -f /etc/nginx/sites-enabled/default
nginx -t && systemctl restart nginx

# SSL via Let's Encrypt
step "Obtendo certificado SSL para $DOMAIN..."
certbot --nginx -d "$DOMAIN" -d "www.$DOMAIN" \
    --non-interactive --agree-tos -m "$EMAIL_CERTBOT" \
    --redirect 2>/dev/null || {
    echo -e "${YELLOW}  ⚠️  SSL não configurado (certbot falhou). Configure manualmente depois.${NC}"
}

# Iniciar Marina
systemctl daemon-reload
systemctl enable marina
systemctl start marina

sleep 3
if systemctl is-active --quiet marina; then
    ok "Marina rodando!"
else
    echo -e "${RED}  ❌ Marina não iniciou — verificando logs:${NC}"
    journalctl -u marina -n 20 --no-pager
    exit 1
fi

# ── Resumo final ──────────────────────────────────────────────
banner "✅ Setup concluído!"
echo "  🌐 Marina:        https://$DOMAIN"
echo "  💊 Health:        https://$DOMAIN/health"
echo "  📊 Status:        https://$DOMAIN/status"
echo "  🔗 Trinks Status: https://$DOMAIN/trinks/status"
echo "  📱 Webhook URL:   https://$DOMAIN/webhook/whatsapp"
echo ""
echo "  Próximos passos:"
echo "  1. Configure o webhook na Evolution API:"
echo "     URL: https://$DOMAIN/webhook/whatsapp"
echo "  2. Escaneie o QR code do WhatsApp:"
echo "     curl http://localhost:8080/instance/connect/nghair -H 'apikey: \$EVOLUTION_API_KEY'"
echo "  3. Verifique a conexão Trinks:"
echo "     curl https://$DOMAIN/trinks/status"
echo ""
echo "  Comandos úteis:"
echo "    journalctl -u marina -f        # logs da Marina"
echo "    docker logs -f evolution-api   # logs do WhatsApp"
echo "    bash $APP_DIR/deploy.sh        # atualizar depois de git pull"
echo ""
