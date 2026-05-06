"""
Schemas Pydantic para Cliente
"""
from pydantic import BaseModel, EmailStr
from datetime import datetime
from typing import Optional, List


class ClienteBase(BaseModel):
    """Schema base para Cliente"""
    nome: str
    telefone: str
    email: Optional[EmailStr] = None
    profissional_preferido: Optional[str] = None
    servico_preferido: Optional[str] = None
    horario_preferido: Optional[str] = None
    notas: Optional[str] = None


class ClienteCreate(ClienteBase):
    """Schema para criar Cliente"""
    pass


class ClienteUpdate(BaseModel):
    """Schema para atualizar Cliente"""
    nome: Optional[str] = None
    email: Optional[EmailStr] = None
    profissional_preferido: Optional[str] = None
    servico_preferido: Optional[str] = None
    horario_preferido: Optional[str] = None
    notas: Optional[str] = None


class ClienteResponse(ClienteBase):
    """Schema para resposta de Cliente"""
    id: int
    data_criacao: datetime
    ultima_interacao: datetime

    class Config:
        from_attributes = True


class ClienteComHistorico(ClienteResponse):
    """Schema de Cliente com histórico de conversas"""
    conversas: List["ConversaResponse"] = []
    agendamentos: List["AgendamentoResponse"] = []


class ConversaResponse(BaseModel):
    """Schema para resposta de Conversa"""
    id: int
    mensagem_usuario: str
    resposta_marina: str
    intencao: Optional[str]
    timestamp: datetime

    class Config:
        from_attributes = True


class AgendamentoResponse(BaseModel):
    """Schema para resposta de Agendamento"""
    id: int
    data: datetime
    servico: str
    profissional: str
    valor: Optional[float]
    status: str
    timestamp: datetime

    class Config:
        from_attributes = True
