"""
Configurações da Marina - Agente de IA para NGHair
"""
import os
from dotenv import load_dotenv

load_dotenv()

# Configurações Gerais
DEBUG = os.getenv("DEBUG", "False").lower() == "true"
SECRET_KEY = os.getenv("SECRET_KEY", "sua-chave-secreta-aqui")

# Banco de Dados
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./data/marina.db")

# Trinks
TRINKS_EMAIL = os.getenv("TRINKS_EMAIL", "mellrodrigo@gmail.com")
TRINKS_PASSWORD = os.getenv("TRINKS_PASSWORD", "Rods2023$")
TRINKS_SYNC_INTERVAL = int(os.getenv("TRINKS_SYNC_INTERVAL", "3600"))  # 1 hora

# OpenAI
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4-1-mini")

# Evolution API / WhatsApp
EVOLUTION_API_URL = os.getenv("EVOLUTION_API_URL", "http://localhost:8080")
EVOLUTION_API_KEY = os.getenv("EVOLUTION_API_KEY")
WHATSAPP_INSTANCE_NAME = os.getenv("WHATSAPP_INSTANCE_NAME", "nghair")

# FastAPI
API_HOST = os.getenv("API_HOST", "0.0.0.0")
API_PORT = int(os.getenv("API_PORT", "8000"))
API_WEBHOOK_URL = os.getenv("API_WEBHOOK_URL", "http://localhost:8000/webhook/whatsapp")

# Logging
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
LOG_FILE = os.getenv("LOG_FILE", "logs/marina.log")

# Marina Persona
MARINA_NAME = "Marina"
MARINA_SALAO = "NGHair"
MARINA_TONE = "profissional e amigável"

# Configurações de Memória
MEMORY_RETENTION_DAYS = int(os.getenv("MEMORY_RETENTION_DAYS", "365"))
MAX_CONVERSATION_HISTORY = int(os.getenv("MAX_CONVERSATION_HISTORY", "20"))
