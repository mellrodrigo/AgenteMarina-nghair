# Marina - Agente de IA para NGHair

Marina é um agente inteligente de IA que atende clientes do salão NGHair via WhatsApp, realiza agendamentos, consulta serviços e aprende sobre preferências de cada cliente.

## Características

- ✅ **Atendimento via WhatsApp**: Responde mensagens em tempo real
- ✅ **Memória de Clientes**: Aprende sobre preferências e histórico
- ✅ **Agendamentos Inteligentes**: Sugere horários e profissionais
- ✅ **Integração com Trinks**: Sincroniza serviços, preços e agenda
- ✅ **Recomendações Personalizadas**: Baseadas em histórico
- ✅ **IA Avançada**: Powered by GPT-4

## Requisitos

- Python 3.9+
- VPS na Hostinger (ou servidor próprio)
- Conta OpenAI com API key
- Conta Evolution API (para WhatsApp)
- Banco de dados (SQLite local ou PostgreSQL)

## Instalação

### 1. Clonar o repositório

```bash
git clone <seu-repositorio>
cd marina
```

### 2. Criar ambiente virtual

```bash
python3 -m venv venv
source venv/bin/activate  # Linux/Mac
# ou
venv\Scripts\activate  # Windows
```

### 3. Instalar dependências

```bash
pip install -r requirements.txt
```

### 4. Configurar variáveis de ambiente

```bash
cp .env.example .env
# Editar .env com suas configurações
nano .env
```

**Variáveis importantes:**

```env
# OpenAI
OPENAI_API_KEY=sk-...

# Evolution API
EVOLUTION_API_URL=http://localhost:8080
EVOLUTION_API_KEY=sua-chave-aqui

# Trinks
TRINKS_EMAIL=mellrodrigo@gmail.com
TRINKS_PASSWORD=Rods2023$

# Database
DATABASE_URL=sqlite:///./data/marina.db
```

### 5. Inicializar banco de dados

```bash
python3 -c "from app.models.database import criar_tabelas; criar_tabelas()"
```

## Executar

### Desenvolvimento Local

```bash
python3 -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### Produção (VPS Hostinger)

#### Opção 1: Usando Systemd

Criar arquivo `/etc/systemd/system/marina.service`:

```ini
[Unit]
Description=Marina AI Agent for NGHair
After=network.target

[Service]
Type=notify
User=www-data
WorkingDirectory=/home/www-data/marina
Environment="PATH=/home/www-data/marina/venv/bin"
ExecStart=/home/www-data/marina/venv/bin/python3 -m uvicorn app.main:app --host 0.0.0.0 --port 8000
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

Depois:

```bash
sudo systemctl daemon-reload
sudo systemctl enable marina
sudo systemctl start marina
sudo systemctl status marina
```

#### Opção 2: Usando Gunicorn + Nginx

```bash
# Instalar Gunicorn
pip install gunicorn

# Executar com Gunicorn
gunicorn -w 4 -b 0.0.0.0:8000 app.main:app
```

Configurar Nginx como reverse proxy:

```nginx
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
```

## Integração com Evolution API

A Marina usa Evolution API para integração com WhatsApp. Você precisa:

1. **Instalar Evolution API** no seu servidor:

```bash
docker run -d \
  --name evolution-api \
  -p 8080:8080 \
  -e DB_CONNECTION=postgres \
  -e DB_HOST=localhost \
  -e DB_PORT=5432 \
  -e DB_DATABASE=evolution \
  -e DB_USERNAME=postgres \
  -e DB_PASSWORD=senha \
  atendai/evolution-api:latest
```

2. **Configurar webhook** na Evolution API para apontar para:

```
https://seu-dominio.com/webhook/whatsapp
```

3. **Obter API key** e adicionar ao `.env`

## Integração com Trinks

A Marina sincroniza automaticamente com o Trinks a cada 1 hora:

- Serviços e preços
- Profissionais disponíveis
- Agenda e horários
- Dados de clientes

Configurar em `.env`:

```env
TRINKS_EMAIL=seu-email@trinks.com
TRINKS_PASSWORD=sua-senha
TRINKS_SYNC_INTERVAL=3600  # 1 hora em segundos
```

## API Endpoints

### Health Check

```bash
GET /health
```

### Webhook WhatsApp

```bash
POST /webhook/whatsapp
```

### Clientes

```bash
# Listar clientes
GET /api/clientes

# Obter cliente
GET /api/clientes/{cliente_id}

# Estatísticas
GET /api/clientes/{cliente_id}/estatisticas

# Criar agendamento
POST /api/clientes/{cliente_id}/agendamento
```

## Estrutura do Projeto

```
marina/
├── app/
│   ├── models/
│   │   └── database.py          # Modelos SQLAlchemy
│   ├── schemas/
│   │   ├── cliente.py           # Schemas Pydantic
│   │   └── whatsapp.py
│   ├── services/
│   │   ├── ai_core.py           # Core de IA
│   │   ├── cliente_service.py   # Gerenciamento de clientes
│   │   └── trinks_scraper.py    # Integração Trinks
│   └── main.py                  # API FastAPI
├── data/                        # Banco de dados (SQLite)
├── logs/                        # Arquivos de log
├── config.py                    # Configurações
├── requirements.txt             # Dependências
├── .env.example                 # Exemplo de variáveis
└── README.md                    # Este arquivo
```

## Logs

Os logs são salvos em `logs/marina.log`. Para visualizar em tempo real:

```bash
tail -f logs/marina.log
```

## Troubleshooting

### Erro: "OPENAI_API_KEY not found"

Certifique-se de que a variável está configurada no `.env`:

```bash
export OPENAI_API_KEY=sk-...
```

### Erro: "Database locked"

Se usar SQLite em produção com múltiplos workers, considere migrar para PostgreSQL:

```env
DATABASE_URL=postgresql://user:password@localhost/marina
```

### Webhook não recebe mensagens

1. Verificar se Evolution API está rodando
2. Confirmar URL do webhook em `.env`
3. Testar webhook com curl:

```bash
curl -X POST http://localhost:8000/webhook/whatsapp \
  -H "Content-Type: application/json" \
  -d '{
    "event": "messages.upsert",
    "instance": "nghair",
    "data": {
      "direction": "in",
      "key": {"remoteJid": "5511999999999@s.whatsapp.net"},
      "message": {"conversation": "Olá Marina!"}
    }
  }'
```

## Próximos Passos

- [ ] Implementar scraping real do Trinks com Selenium
- [ ] Adicionar suporte a múltiplas mídias (imagens, documentos)
- [ ] Dashboard de administração
- [ ] Relatórios de atendimento
- [ ] Integração com CRM
- [ ] Testes automatizados

## Suporte

Para dúvidas ou problemas, entre em contato com o time de desenvolvimento.

## Licença

Proprietary - NGHair
