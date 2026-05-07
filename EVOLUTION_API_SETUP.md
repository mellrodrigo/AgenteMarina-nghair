# Guia de Instalação da Evolution API no VPS Hostinger

A **Evolution API** é o componente responsável por conectar a Marina ao WhatsApp.
Como o servidor não tem Docker nem Node.js nativos, recomendamos usar um serviço externo
de Evolution API hospedado na nuvem.

---

## Opção 1 (Recomendada): Evolution API na Nuvem (Gratuita)

Use o **Railway** ou **Render** para hospedar a Evolution API gratuitamente:

### Passo 1 — Deploy no Railway

1. Acesse https://railway.app e crie uma conta gratuita
2. Clique em **"New Project" → "Deploy from GitHub Repo"**
3. Use o repositório oficial: `EvolutionAPI/evolution-api`
4. Configure as variáveis de ambiente:
   ```
   AUTHENTICATION_TYPE=apikey
   AUTHENTICATION_API_KEY=marina-nghair-2024
   ```
5. Após o deploy, copie a URL gerada (ex: `https://evolution-api-xxx.railway.app`)

### Passo 2 — Atualizar .env da Marina

No seu VPS, edite o arquivo `/home/u733743267/marina/.env`:
```bash
nano /home/u733743267/marina/.env
```

Atualize as variáveis:
```env
EVOLUTION_API_URL=https://evolution-api-xxx.railway.app
EVOLUTION_API_KEY=marina-nghair-2024
WHATSAPP_INSTANCE_NAME=nghair
API_WEBHOOK_URL=http://185.239.210.92:5000/webhook/whatsapp
```

### Passo 3 — Conectar WhatsApp

1. Acesse o painel da Evolution API:
   `https://evolution-api-xxx.railway.app/manager`

2. Crie uma instância chamada `nghair`

3. Escaneie o QR Code com o WhatsApp do NGHair

4. Configure o webhook apontando para:
   `http://185.239.210.92:5000/webhook/whatsapp`

---

## Opção 2: Instalar Node.js e Evolution API no VPS

Se preferir instalar no próprio VPS (requer permissão de root):

```bash
# Instalar Node.js 18
curl -fsSL https://rpm.nodesource.com/setup_18.x | sudo bash -
sudo yum install -y nodejs

# Instalar Evolution API
npm install -g @evolution-api/evolution-api

# Iniciar
evolution-api start
```

> **Atenção**: Este servidor usa CloudLinux com restrições. Pode não ser possível
> instalar pacotes de sistema sem contato com o suporte da Hostinger.

---

## Opção 3: Usar WhatsApp Business API Oficial (Meta)

Para uso profissional e em escala:

1. Acesse https://business.facebook.com
2. Configure o WhatsApp Business API
3. Obtenha o token de acesso
4. Atualize o `.env` com as credenciais da Meta API

---

## Status Atual da Marina

| Componente | Status | Observação |
|-----------|--------|------------|
| Backend Marina | ✅ ONLINE | Porta 5000, PID ativo |
| Banco de Dados | ✅ Funcionando | SQLite em data/marina.db |
| Gemini 2.0 Flash | ✅ Configurado | API v1, modelo atualizado |
| WhatsApp (Evolution API) | ⏳ Pendente | Instalar conforme este guia |
| Crontab Watchdog | ⚠️ Limitado | Servidor sem crontab nativo |

---

## Reiniciar a Marina Manualmente

Se a Marina cair, reconecte via SSH e execute:

```bash
cd /home/u733743267/marina
export PATH=/home/u733743267/.local/bin:$PATH
export PYTHONPATH=/home/u733743267/marina
nohup /home/u733743267/.local/bin/gunicorn \
    --bind 0.0.0.0:5000 \
    --workers 2 \
    --threads 4 \
    --timeout 120 \
    --pythonpath /home/u733743267/marina \
    app.main:app >> logs/marina.log 2>&1 &
echo $! > marina.pid
echo "Marina iniciada! PID: $(cat marina.pid)"
```

---

## Testar a Marina

```bash
# Health check
curl http://localhost:5000/health

# Listar clientes
curl http://localhost:5000/clientes

# Simular mensagem WhatsApp
curl -X POST http://localhost:5000/webhook/whatsapp \
    -H "Content-Type: application/json" \
    -d '{"event":"messages.upsert","data":{"key":{"remoteJid":"5511999999999@s.whatsapp.net"},"direction":"in","message":{"conversation":"Oi, quero agendar"}}}'
```

---

## Suporte

- **Repositório**: https://github.com/mellrodrigo/AgenteMarina-nghair
- **Evolution API Docs**: https://doc.evolution-api.com
- **Gemini API**: https://ai.google.dev
