# Marina - Guia de Troubleshooting

Soluções para problemas comuns ao usar Marina.

---

## 🔴 Problemas Críticos

### Aplicação não inicia

**Sintoma**: `systemctl status marina` mostra erro

**Solução**:

```bash
# Verificar logs detalhados
sudo journalctl -u marina -n 50

# Verificar se porta 8000 está em uso
sudo lsof -i :8000

# Matar processo em uso
sudo kill -9 <PID>

# Reiniciar serviço
sudo systemctl restart marina
```

### Erro: "Address already in use"

**Sintoma**: Porta 8000 já está em uso

**Solução**:

```bash
# Encontrar processo usando porta
sudo netstat -tlnp | grep 8000

# Matar processo
sudo kill -9 <PID>

# Ou usar porta diferente
python3 -m uvicorn app.main:app --port 8001
```

### Banco de dados corrompido

**Sintoma**: Erros ao acessar banco de dados

**Solução**:

```bash
# Backup do banco antigo
cp data/marina.db data/marina.db.backup

# Remover banco corrompido
rm data/marina.db

# Recriar banco
python3 -c "from app.models.database import criar_tabelas; criar_tabelas()"

# Restaurar dados (se backup disponível)
# ... restaurar de backup
```

---

## 🟡 Problemas de Configuração

### Erro: "OPENAI_API_KEY not found"

**Sintoma**: Aplicação não consegue acessar OpenAI

**Solução**:

```bash
# Verificar se .env existe
ls -la .env

# Verificar se variável está configurada
grep OPENAI_API_KEY .env

# Se não estiver, adicionar
echo "OPENAI_API_KEY=sk-seu-token" >> .env

# Recarregar variáveis
source .env

# Reiniciar aplicação
sudo systemctl restart marina
```

### Erro: "Evolution API connection refused"

**Sintoma**: Não consegue conectar com Evolution API

**Solução**:

```bash
# Verificar se Evolution API está rodando
docker ps | grep evolution

# Se não estiver, iniciar
docker-compose up -d evolution-api

# Verificar logs
docker logs evolution-api

# Testar conexão
curl http://localhost:8080/health

# Verificar URL configurada
grep EVOLUTION_API_URL .env
```

### Erro: "Trinks login failed"

**Sintoma**: Não consegue fazer login no Trinks

**Solução**:

```bash
# Verificar credenciais
grep TRINKS_EMAIL .env
grep TRINKS_PASSWORD .env

# Testar login manualmente
# Acessar https://www.trinks.com/login

# Se credenciais estiverem corretas, pode ser:
# - Captcha bloqueando
# - IP bloqueado
# - Conta suspensa

# Verificar logs
tail -f logs/marina.log | grep -i trinks
```

---

## 🟠 Problemas de Performance

### Resposta lenta do WhatsApp

**Sintoma**: Mensagens levam > 5 segundos para responder

**Solução**:

```bash
# Verificar uso de CPU
top -b -n 1 | head -20

# Verificar uso de memória
free -h

# Verificar latência de rede
ping -c 5 api.openai.com

# Se CPU alta, aumentar workers
# Editar /etc/systemd/system/marina.service
# Adicionar: --workers 4

# Se memória alta, verificar memory leaks
# Monitorar por 1 hora
watch -n 5 'ps aux | grep marina'
```

### Banco de dados lento

**Sintoma**: Queries levam muito tempo

**Solução**:

```bash
# Se usar SQLite, migrar para PostgreSQL
# Editar .env
DATABASE_URL=postgresql://user:pass@localhost/marina

# Criar índices
python3 << 'EOF'
from app.models.database import SessionLocal, engine, Base
from sqlalchemy import text

db = SessionLocal()
db.execute(text("CREATE INDEX idx_cliente_telefone ON clientes(telefone)"))
db.execute(text("CREATE INDEX idx_conversa_cliente ON conversas(cliente_id)"))
db.execute(text("CREATE INDEX idx_agendamento_cliente ON agendamentos(cliente_id)"))
db.commit()
EOF

# Verificar índices
sqlite3 data/marina.db ".indices"
```

---

## 🔵 Problemas de Webhook

### Webhook não recebe mensagens

**Sintoma**: Mensagens do WhatsApp não chegam

**Solução**:

```bash
# Verificar se webhook está configurado na Evolution API
curl http://localhost:8080/webhook/find/nghair

# Se não estiver, configurar
curl -X POST http://localhost:8080/webhook/set/nghair \
  -H "apikey: sua-chave" \
  -H "Content-Type: application/json" \
  -d '{
    "url": "https://seu-dominio.com/webhook/whatsapp",
    "events": ["MESSAGES_UPSERT"]
  }'

# Testar webhook manualmente
curl -X POST https://seu-dominio.com/webhook/whatsapp \
  -H "Content-Type: application/json" \
  -d '{
    "event": "messages.upsert",
    "instance": "nghair",
    "data": {"test": true}
  }'

# Verificar logs
tail -f logs/marina.log | grep webhook
```

### Erro 403 no webhook

**Sintoma**: Nginx retorna 403 Forbidden

**Solução**:

```bash
# Verificar permissões de arquivo
ls -la /home/marina/

# Verificar configuração do Nginx
sudo nginx -t

# Verificar logs do Nginx
sudo tail -f /var/log/nginx/marina_error.log

# Recarregar Nginx
sudo systemctl reload nginx
```

---

## 🟢 Problemas de Integração

### Trinks não sincroniza

**Sintoma**: Dados do Trinks não aparecem em Marina

**Solução**:

```bash
# Verificar se sincronização está agendada
grep TRINKS_SYNC_INTERVAL .env

# Forçar sincronização manual
python3 << 'EOF'
import asyncio
from app.services.trinks_scraper_real import trinks_scraper_real
from app.models.database import SessionLocal

db = SessionLocal()
asyncio.run(trinks_scraper_real.sincronizar_dados(db))
EOF

# Verificar logs
tail -f logs/marina.log | grep -i trinks

# Se erro de Selenium, verificar Chrome
which chromium-browser
which google-chrome
```

### Agendamentos não aparecem no Trinks

**Sintoma**: Agendamentos criados em Marina não aparecem no Trinks

**Nota**: Marina não sincroniza para Trinks (apenas lê). Para sincronizar, usar API do Trinks ou fazer manualmente.

---

## 📊 Monitoramento

### Verificar Status Geral

```bash
# Status do serviço
sudo systemctl status marina

# Logs recentes
sudo journalctl -u marina -n 100

# Uso de recursos
ps aux | grep marina

# Conexões de rede
sudo netstat -tlnp | grep 8000

# Disco
df -h

# Memória
free -h
```

### Criar Alerta de Erro

```bash
# Monitorar erros em tempo real
tail -f logs/marina.log | grep ERROR

# Contar erros por tipo
grep ERROR logs/marina.log | cut -d: -f3 | sort | uniq -c

# Alertar se muitos erros
grep ERROR logs/marina.log | wc -l
```

---

## 🔧 Limpeza e Manutenção

### Limpar Logs Antigos

```bash
# Remover logs com mais de 30 dias
find logs/ -name "*.log" -mtime +30 -delete

# Ou usar logrotate (recomendado)
sudo nano /etc/logrotate.d/marina
```

Adicionar:

```
/home/marina/logs/*.log {
    daily
    rotate 30
    compress
    delaycompress
    notifempty
    create 0640 www-data www-data
}
```

### Limpar Cache

```bash
# Limpar cache Python
find . -type d -name __pycache__ -exec rm -r {} +
find . -type f -name "*.pyc" -delete

# Limpar arquivos temporários
rm -rf /tmp/marina_*
```

### Atualizar Dependências

```bash
# Verificar atualizações
pip list --outdated

# Atualizar tudo (cuidado!)
pip install -U -r requirements.txt

# Testar após atualizar
python3 test_marina.py

# Reiniciar
sudo systemctl restart marina
```

---

## 📞 Escalação

Se nenhuma solução funcionar:

1. **Coletar informações**:
   ```bash
   # Criar relatório de diagnóstico
   echo "=== Status do Sistema ===" > diagnostico.txt
   systemctl status marina >> diagnostico.txt
   journalctl -u marina -n 100 >> diagnostico.txt
   ps aux | grep marina >> diagnostico.txt
   free -h >> diagnostico.txt
   df -h >> diagnostico.txt
   ```

2. **Contatar suporte** com:
   - Arquivo `diagnostico.txt`
   - Descrição do problema
   - Passos para reproduzir
   - Logs relevantes

---

**Última atualização**: Maio 2026  
**Versão**: 1.0.0
