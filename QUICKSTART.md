# Marina - Quick Start Guide

Guia rápido para começar com Marina em 15 minutos.

---

## 1️⃣ Clonar o Repositório

```bash
git clone <seu-repositorio-marina>
cd marina
```

---

## 2️⃣ Configurar Ambiente

### Criar arquivo `.env`

```bash
cp .env.example .env
nano .env
```

Adicionar suas credenciais:

```env
OPENAI_API_KEY=sk-seu-token-aqui
EVOLUTION_API_URL=http://localhost:8080
EVOLUTION_API_KEY=sua-chave-aqui
TRINKS_EMAIL=seu-email@trinks.com
TRINKS_PASSWORD=sua-senha
```

---

## 3️⃣ Instalar Dependências

```bash
# Criar ambiente virtual
python3.11 -m venv venv
source venv/bin/activate

# Instalar dependências
pip install -r requirements.txt
```

---

## 4️⃣ Inicializar Banco de Dados

```bash
python3 -c "from app.models.database import criar_tabelas; criar_tabelas()"
```

---

## 5️⃣ Iniciar a Aplicação

### Desenvolvimento Local

```bash
python3 -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

A API estará disponível em: `http://localhost:8000`

### Produção (VPS Hostinger)

Seguir o guia completo em `SETUP_HOSTINGER.md`

---

## 6️⃣ Testar

```bash
# Executar testes
python3 test_marina.py

# Testar endpoint de health
curl http://localhost:8000/health

# Testar webhook
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

---

## 📚 Próximos Passos

1. **Ler a Documentação Completa**: `README.md`
2. **Configurar Evolution API**: `SETUP_HOSTINGER.md`
3. **Fazer Deploy**: `SETUP_HOSTINGER.md`
4. **Monitorar**: Verificar logs em `logs/marina.log`

---

## 🆘 Troubleshooting Rápido

### Erro: "OPENAI_API_KEY not found"
```bash
# Verificar se está no .env
cat .env | grep OPENAI_API_KEY

# Se não estiver, adicionar:
echo "OPENAI_API_KEY=sk-..." >> .env
```

### Erro: "Database locked"
```bash
# Remover banco de dados antigo
rm data/marina.db

# Recriar
python3 -c "from app.models.database import criar_tabelas; criar_tabelas()"
```

### Erro: "Connection refused"
```bash
# Verificar se a aplicação está rodando
curl http://localhost:8000/health

# Se não responder, reiniciar
systemctl restart marina  # Em produção
```

---

## 📞 Suporte

Para dúvidas ou problemas, consulte:
- 📖 Documentação completa: `README.md`
- 🔧 Setup detalhado: `SETUP_HOSTINGER.md`
- 🐛 Troubleshooting: `TROUBLESHOOTING.md`
- 📋 Checklist: `DEPLOYMENT_CHECKLIST.md`

---

**Pronto para começar? Boa sorte! 🚀**
