"""
Configurações da Marina - Agente de IA para NGHair
Todas as credenciais devem ser definidas no arquivo .env (nunca hardcoded aqui)
"""
import os
from dotenv import load_dotenv

load_dotenv()

# Configurações Gerais
DEBUG = os.getenv("DEBUG", "False").lower() == "true"
SECRET_KEY = os.getenv("SECRET_KEY", "")

# Banco de Dados
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./data/marina.db")

# Trinks — valores legados / fallback (usado quando só há um salão configurado)
TRINKS_API_KEY = os.getenv("TRINKS_API_KEY", "")
TRINKS_API_URL = os.getenv("TRINKS_API_URL", "https://api.trinks.com")
TRINKS_ESTABELECIMENTO_ID = os.getenv("TRINKS_ESTABELECIMENTO_ID", "20181")
TRINKS_SYNC_INTERVAL = int(os.getenv("TRINKS_SYNC_INTERVAL", "3600"))

# OpenAI GPT
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")

# Evolution API / WhatsApp
EVOLUTION_API_URL = os.getenv("EVOLUTION_API_URL", "http://localhost:8080")
EVOLUTION_API_KEY = os.getenv("EVOLUTION_API_KEY", "")
WHATSAPP_INSTANCE_NAME = os.getenv("WHATSAPP_INSTANCE_NAME", "nghair")

# API
API_HOST = os.getenv("API_HOST", "0.0.0.0")
API_PORT = int(os.getenv("API_PORT", "8000"))
API_WEBHOOK_URL = os.getenv("API_WEBHOOK_URL", "")

# Logging
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
LOG_FILE = os.getenv("LOG_FILE", "logs/marina.log")

# Marina Persona
MARINA_NAME = os.getenv("MARINA_NAME", "Marina")
MARINA_SALAO = os.getenv("MARINA_SALAO", "NGHair")
MARINA_TONE = os.getenv("MARINA_TONE", "profissional e amigável")

# Configurações de Memória
MEMORY_RETENTION_DAYS = int(os.getenv("MEMORY_RETENTION_DAYS", "365"))
MAX_CONVERSATION_HISTORY = int(os.getenv("MAX_CONVERSATION_HISTORY", "20"))

# ── Multi-salão ──────────────────────────────────────────────────────────────
# Cada salão é identificado pelo nome da instância Evolution API (WHATSAPP_INSTANCE_NAME).
# Configure SALON_1_* e SALON_2_* no .env; o campo "instance" do webhook faz o roteamento.
# Se não configurado, usa os valores legados acima como salão padrão.

def _salon_cfg(prefix, default_nome, default_instance, default_trinks_id=None):
    return {
        "nome": os.getenv("{}_NOME".format(prefix), default_nome),
        "instance": os.getenv("{}_INSTANCE".format(prefix), default_instance),
        "trinks_api_key": os.getenv("{}_TRINKS_API_KEY".format(prefix), TRINKS_API_KEY),
        "trinks_estabelecimento_id": os.getenv(
            "{}_TRINKS_ESTABELECIMENTO_ID".format(prefix), default_trinks_id or TRINKS_ESTABELECIMENTO_ID
        ),
        "trinks_api_url": os.getenv("{}_TRINKS_API_URL".format(prefix), TRINKS_API_URL),
    }


# Salão 1 — Brooklin (instância padrão atual)
_s1 = _salon_cfg("SALON_1", "NGHair Brooklin", WHATSAPP_INSTANCE_NAME)
# Salão 2 — Campo Belo
_s2 = _salon_cfg("SALON_2", "NGHair Campo Belo", "")

# SALOES: mapeia instance_name (Evolution) → config do salão
# Instâncias vazias não são registradas
SALOES = {}
for _s in [_s1, _s2]:
    if _s["instance"]:
        SALOES[_s["instance"]] = _s

# Config padrão: primeiro salão configurado (ou fallback legado)
SALAO_PADRAO = _s1
