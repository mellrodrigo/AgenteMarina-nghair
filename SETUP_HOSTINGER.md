# Guia de Setup da Marina no VPS Hostinger

Este guia passo a passo irá ajudá-lo a configurar e fazer deploy da Marina no seu VPS Hostinger.

## Pré-requisitos

- VPS Hostinger com Ubuntu 20.04 ou superior
- Acesso SSH ao servidor
- Domínio configurado (opcional, mas recomendado)
- Conta OpenAI com API key
- Evolution API configurada

## Passo 1: Conectar ao VPS via SSH

```bash
ssh root@seu-ip-vps
# ou
ssh seu-usuario@seu-ip-vps
```

## Passo 2: Atualizar o Sistema

```bash
sudo apt update
sudo apt upgrade -y
sudo apt install -y build-essential python3.11 python3.11-venv python3-pip git curl wget
```

## Passo 3: Clonar o Repositório

```bash
cd /home
git clone <seu-repositorio-marina> marina
cd marina
```

Ou, se preferir copiar manualmente:

```bash
mkdir -p /home/marina
cd /home/marina
# Copiar arquivos via SCP ou outro método
```

## Passo 4: Criar Ambiente Virtual

```bash
python3.11 -m venv venv
source venv/bin/activate
```

## Passo 5: Instalar Dependências

```bash
pip install --upgrade pip
pip install -r requirements.txt
```

## Passo 6: Configurar Variáveis de Ambiente

```bash
cp .env.example .env
nano .env
```

Edite o arquivo `.env` com suas configurações:

```env
# OpenAI
OPENAI_API_KEY=sk-seu-token-aqui

# Evolution API
EVOLUTION_API_URL=http://localhost:8080
EVOLUTION_API_KEY=sua-chave-evolution-aqui

# Trinks
TRINKS_EMAIL=mellrodrigo@gmail.com
TRINKS_PASSWORD=Rods2023$

# Database
DATABASE_URL=sqlite:///./data/marina.db
# Ou para PostgreSQL:
# DATABASE_URL=postgresql://usuario:senha@localhost/marina

# API
API_WEBHOOK_URL=https://seu-dominio.com/webhook/whatsapp
```

## Passo 7: Inicializar Banco de Dados

```bash
python3 -c "from app.models.database import criar_tabelas; criar_tabelas()"
```

## Passo 8: Testar Localmente (Opcional)

```bash
python3 test_marina.py
```

## Passo 9: Configurar Serviço Systemd

Criar arquivo `/etc/systemd/system/marina.service`:

```bash
sudo nano /etc/systemd/system/marina.service
```

Adicionar conteúdo:

```ini
[Unit]
Description=Marina AI Agent for NGHair
After=network.target

[Service]
Type=notify
User=www-data
WorkingDirectory=/home/marina
Environment="PATH=/home/marina/venv/bin"
EnvironmentFile=/home/marina/.env
ExecStart=/home/marina/venv/bin/python3 -m uvicorn app.main:app --host 0.0.0.0 --port 8000
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
```

## Passo 10: Iniciar o Serviço

```bash
sudo systemctl daemon-reload
sudo systemctl enable marina
sudo systemctl start marina
sudo systemctl status marina
```

## Passo 11: Configurar Nginx como Reverse Proxy

```bash
sudo apt install -y nginx
sudo nano /etc/nginx/sites-available/marina
```

Adicionar configuração:

```nginx
upstream marina_app {
    server 127.0.0.1:8000;
}

server {
    listen 80;
    server_name seu-dominio.com;

    # Redirecionar HTTP para HTTPS (depois de configurar SSL)
    # return 301 https://$server_name$request_uri;

    location / {
        proxy_pass http://marina_app;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_redirect off;
        
        # Timeouts para WebSocket
        proxy_connect_timeout 7d;
        proxy_send_timeout 7d;
        proxy_read_timeout 7d;
    }

    # Logs
    access_log /var/log/nginx/marina_access.log;
    error_log /var/log/nginx/marina_error.log;
}
```

Ativar site:

```bash
sudo ln -s /etc/nginx/sites-available/marina /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl restart nginx
```

## Passo 12: Configurar SSL com Let's Encrypt

```bash
sudo apt install -y certbot python3-certbot-nginx
sudo certbot certonly --nginx -d seu-dominio.com
```

Atualizar configuração Nginx para HTTPS:

```bash
sudo nano /etc/nginx/sites-available/marina
```

Adicionar bloco HTTPS:

```nginx
server {
    listen 443 ssl http2;
    server_name seu-dominio.com;

    ssl_certificate /etc/letsencrypt/live/seu-dominio.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/seu-dominio.com/privkey.pem;

    # ... resto da configuração
}

# Redirecionar HTTP para HTTPS
server {
    listen 80;
    server_name seu-dominio.com;
    return 301 https://$server_name$request_uri;
}
```

## Passo 13: Configurar Evolution API (Docker)

```bash
sudo apt install -y docker.io docker-compose

# Criar arquivo docker-compose.yml (já fornecido no projeto)
docker-compose up -d
```

## Passo 14: Configurar Webhook

Na Evolution API, configure o webhook para:

```
https://seu-dominio.com/webhook/whatsapp
```

## Passo 15: Monitorar Logs

```bash
# Logs do serviço Marina
sudo journalctl -u marina -f

# Logs do Nginx
sudo tail -f /var/log/nginx/marina_access.log
sudo tail -f /var/log/nginx/marina_error.log

# Logs da aplicação
tail -f /home/marina/logs/marina.log
```

## Passo 16: Configurar Backup Automático

```bash
# Criar script de backup
sudo nano /usr/local/bin/backup-marina.sh
```

```bash
#!/bin/bash
BACKUP_DIR="/backups/marina"
DATE=$(date +%Y%m%d_%H%M%S)

mkdir -p $BACKUP_DIR

# Backup do banco de dados
cp /home/marina/data/marina.db $BACKUP_DIR/marina_$DATE.db

# Backup do .env
cp /home/marina/.env $BACKUP_DIR/.env_$DATE

# Remover backups antigos (mais de 30 dias)
find $BACKUP_DIR -mtime +30 -delete

echo "Backup realizado: $DATE"
```

Tornar executável e agendar:

```bash
sudo chmod +x /usr/local/bin/backup-marina.sh
sudo crontab -e
```

Adicionar linha:

```
0 2 * * * /usr/local/bin/backup-marina.sh
```

## Troubleshooting

### Erro: "Connection refused"

Verificar se o serviço está rodando:

```bash
sudo systemctl status marina
sudo journalctl -u marina -n 50
```

### Erro: "Database locked"

Se usar SQLite com múltiplos workers, migrar para PostgreSQL:

```bash
# Instalar PostgreSQL
sudo apt install -y postgresql postgresql-contrib

# Criar banco
sudo -u postgres createdb marina
sudo -u postgres createuser marina
sudo -u postgres psql -c "ALTER USER marina WITH PASSWORD 'senha_segura';"

# Atualizar .env
DATABASE_URL=postgresql://marina:senha_segura@localhost/marina
```

### Erro: "OPENAI_API_KEY not found"

Verificar se a variável está no `.env`:

```bash
cat /home/marina/.env | grep OPENAI_API_KEY
```

### Evolution API não conecta

Verificar se está rodando:

```bash
docker ps
docker logs evolution-api
```

## Próximos Passos

1. Testar webhook do WhatsApp
2. Configurar automações de sincronização com Trinks
3. Configurar alertas e monitoramento
4. Implementar backup automático
5. Documentar procedimentos operacionais

## Suporte

Para dúvidas ou problemas, consulte:
- Logs da aplicação: `/home/marina/logs/marina.log`
- Documentação: `/home/marina/README.md`
- Issues do projeto

---

**Última atualização**: Maio 2026
