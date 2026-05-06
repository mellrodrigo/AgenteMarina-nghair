#!/bin/bash

# Script de deployment da Marina no VPS Hostinger
# Executar como: bash deploy.sh

set -e

echo "🚀 Iniciando deployment da Marina..."

# Cores para output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Configurações
APP_DIR="/home/www-data/marina"
VENV_DIR="$APP_DIR/venv"
SERVICE_NAME="marina"
USER="www-data"

# 1. Criar diretório da aplicação
echo -e "${YELLOW}[1/8]${NC} Criando diretório da aplicação..."
sudo mkdir -p $APP_DIR
sudo chown -R $USER:$USER $APP_DIR

# 2. Clonar repositório (ou copiar arquivos)
echo -e "${YELLOW}[2/8]${NC} Copiando arquivos da aplicação..."
# Se estiver usando git:
# cd $APP_DIR
# sudo -u $USER git clone <seu-repo> .
# Ou copiar manualmente:
# sudo cp -r marina/* $APP_DIR/

# 3. Criar ambiente virtual
echo -e "${YELLOW}[3/8]${NC} Criando ambiente virtual..."
sudo -u $USER python3 -m venv $VENV_DIR

# 4. Instalar dependências
echo -e "${YELLOW}[4/8]${NC} Instalando dependências..."
sudo -u $USER $VENV_DIR/bin/pip install --upgrade pip
sudo -u $USER $VENV_DIR/bin/pip install -r $APP_DIR/requirements.txt

# 5. Configurar arquivo .env
echo -e "${YELLOW}[5/8]${NC} Configurando arquivo .env..."
if [ ! -f "$APP_DIR/.env" ]; then
    echo "⚠️  Arquivo .env não encontrado!"
    echo "Por favor, crie o arquivo .env com as configurações necessárias:"
    echo "  cp $APP_DIR/.env.example $APP_DIR/.env"
    echo "  nano $APP_DIR/.env"
    exit 1
fi

# 6. Inicializar banco de dados
echo -e "${YELLOW}[6/8]${NC} Inicializando banco de dados..."
cd $APP_DIR
sudo -u $USER $VENV_DIR/bin/python3 -c "from app.models.database import criar_tabelas; criar_tabelas()"

# 7. Criar serviço systemd
echo -e "${YELLOW}[7/8]${NC} Criando serviço systemd..."
sudo tee /etc/systemd/system/$SERVICE_NAME.service > /dev/null <<EOF
[Unit]
Description=Marina AI Agent for NGHair
After=network.target

[Service]
Type=notify
User=$USER
WorkingDirectory=$APP_DIR
Environment="PATH=$VENV_DIR/bin"
EnvironmentFile=$APP_DIR/.env
ExecStart=$VENV_DIR/bin/python3 -m uvicorn app.main:app --host 0.0.0.0 --port 8000
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
EOF

# 8. Iniciar serviço
echo -e "${YELLOW}[8/8]${NC} Iniciando serviço..."
sudo systemctl daemon-reload
sudo systemctl enable $SERVICE_NAME
sudo systemctl start $SERVICE_NAME

# Verificar status
sleep 2
if sudo systemctl is-active --quiet $SERVICE_NAME; then
    echo -e "${GREEN}✅ Marina iniciada com sucesso!${NC}"
    echo ""
    echo "Status do serviço:"
    sudo systemctl status $SERVICE_NAME --no-pager
    echo ""
    echo "Para visualizar logs:"
    echo "  sudo journalctl -u $SERVICE_NAME -f"
else
    echo "❌ Erro ao iniciar Marina"
    sudo systemctl status $SERVICE_NAME --no-pager
    exit 1
fi

# Configurar Nginx (opcional)
echo ""
echo -e "${YELLOW}Próximos passos:${NC}"
echo "1. Configurar Nginx como reverse proxy"
echo "2. Configurar SSL com Let's Encrypt"
echo "3. Configurar Evolution API"
echo "4. Testar webhook do WhatsApp"
echo ""
echo "Exemplo de configuração Nginx:"
echo ""
cat << 'NGINX'
server {
    listen 80;
    server_name seu-dominio.com;
    
    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
NGINX

echo ""
echo -e "${GREEN}Deployment concluído! 🎉${NC}"
