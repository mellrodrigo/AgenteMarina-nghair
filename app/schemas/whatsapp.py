"""
Schemas para mensagens WhatsApp
"""
from pydantic import BaseModel
from typing import Optional, Dict, Any
from datetime import datetime


class MensagemWhatsApp(BaseModel):
    """Schema para mensagem recebida do WhatsApp"""
    telefone: str
    mensagem: str
    timestamp: Optional[datetime] = None
    tipo: str = "texto"  # texto, imagem, documento, etc


class RespostaWhatsApp(BaseModel):
    """Schema para resposta a ser enviada ao WhatsApp"""
    telefone: str
    mensagem: str
    tipo: str = "texto"


class WebhookEvolutionAPI(BaseModel):
    """Schema para webhook da Evolution API"""
    event: str
    instance: str
    data: Dict[str, Any]


class MensagemProcessada(BaseModel):
    """Schema para mensagem processada internamente"""
    cliente_id: int
    telefone: str
    mensagem_usuario: str
    resposta_marina: str
    intencao: str
    contexto: Optional[Dict[str, Any]] = None
    timestamp: datetime
