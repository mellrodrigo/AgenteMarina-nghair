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

# Trinks — API REST oficial
TRINKS_API_KEY = os.getenv("TRINKS_API_KEY", "")
TRINKS_API_URL = os.getenv("TRINKS_API_URL", "https://api.trinks.com")
TRINKS_SYNC_INTERVAL = int(os.getenv("TRINKS_SYNC_INTERVAL", "3600"))

# Google Gemini
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.0-flash")

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
