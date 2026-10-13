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
# WhatsApp é único — o cliente ESCOLHE o salão durante a conversa.
# A Marina pergunta qual unidade e armazena a escolha; o Trinks correto é usado por slug.
# Slugs: "campo-belo" (padrão) e "brooklin"

SALOES = {
    "campo-belo": {
        "nome": "NGHair Campo Belo",
        "slug": "campo-belo",
        "endereco": "Rua João Álvares Soares, 1292 - Campo Belo, São Paulo",
        "instagram": "@nghair",
        "trinks_url": "https://www.trinks.com/nghaircampobelo/framebusca",
        "trinks_api_key": os.getenv("TRINKS_API_KEY", TRINKS_API_KEY),
        "trinks_estabelecimento_id": os.getenv("TRINKS_ESTABELECIMENTO_ID_CAMPO_BELO", "20181"),
        "trinks_api_url": TRINKS_API_URL,
    },
    "brooklin": {
        "nome": "NGHair Brooklin",
        "slug": "brooklin",
        "endereco": "Rua Barão do Triunfo, 1455 - Brooklin, São Paulo",
        "instagram": "@nghair.brooklin",
        "trinks_url": "https://www.trinks.com/nghair-brooklin/framebusca",
        "trinks_api_key": os.getenv("TRINKS_API_KEY_BROOKLIN", TRINKS_API_KEY),
        "trinks_estabelecimento_id": os.getenv("TRINKS_ESTABELECIMENTO_ID_BROOKLIN", "281029"),
        "trinks_api_url": TRINKS_API_URL,
    },
}

# Salão padrão (usado até o cliente escolher)
SALAO_PADRAO = SALOES["campo-belo"]
