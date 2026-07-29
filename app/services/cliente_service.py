"""
Servico de gerenciamento de clientes
Compativel com Python 3.6+ (sem f-strings, sem pydantic)
"""
import logging
import json
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy import desc

from app.models.database import Cliente, Conversa, Agendamento, MemoriaIA

logger = logging.getLogger(__name__)


class ClienteService:

    @staticmethod
    def buscar_ou_criar_cliente(db, telefone, nome=None):
        """Busca cliente pelo telefone ou cria um novo"""
        try:
            cliente = db.query(Cliente).filter(Cliente.telefone == telefone).first()
            if not cliente:
                cliente = Cliente(
                    telefone=telefone,
                    nome=nome or "Cliente",
                    data_criacao=datetime.utcnow(),
                    ultima_interacao=datetime.utcnow()
                )
                db.add(cliente)
                db.commit()
                db.refresh(cliente)
                logger.info("Novo cliente criado: %s", telefone)
            else:
                cliente.ultima_interacao = datetime.utcnow()
                db.commit()
            return cliente
        except Exception as e:
            logger.error("Erro ao buscar/criar cliente: %s", str(e))
            db.rollback()
            raise

    @staticmethod
    def buscar_cliente_por_telefone(db, telefone):
        return db.query(Cliente).filter(Cliente.telefone == telefone).first()

    @staticmethod
    def atualizar_cliente(db, cliente_id, **campos):
        """Atualiza campos do cliente (nome, profissional_preferido, etc.)"""
        try:
            cliente = db.query(Cliente).filter(Cliente.id == cliente_id).first()
            if not cliente:
                return False
            for campo, valor in campos.items():
                if hasattr(cliente, campo) and valor:
                    setattr(cliente, campo, valor)
            db.commit()
            logger.info("Cliente %s atualizado: %s", cliente_id, campos)
            return True
        except Exception as e:
            logger.error("Erro ao atualizar cliente %s: %s", cliente_id, str(e))
            db.rollback()
            return False

    @staticmethod
    def obter_contexto_cliente(db, cliente_id):
        """Retorna contexto completo do cliente para a IA"""
        try:
            cliente = db.query(Cliente).filter(Cliente.id == cliente_id).first()
            if not cliente:
                return {"nome": "Cliente", "historico_servicos": [], "preferencias": {}}

            conversas = db.query(Conversa)\
                .filter(Conversa.cliente_id == cliente_id)\
                .order_by(desc(Conversa.timestamp))\
                .limit(5).all()

            agendamentos = db.query(Agendamento)\
                .filter(Agendamento.cliente_id == cliente_id)\
                .order_by(desc(Agendamento.data))\
                .limit(10).all()

            memorias = db.query(MemoriaIA)\
                .filter(MemoriaIA.cliente_id == cliente_id)\
                .order_by(desc(MemoriaIA.relevancia))\
                .limit(10).all()

            historico_servicos = [ag.servico for ag in agendamentos if ag.servico]

            preferencias = {}
            if cliente.profissional_preferido:
                preferencias["profissional_preferido"] = cliente.profissional_preferido
            if cliente.servico_preferido:
                preferencias["servico_preferido"] = cliente.servico_preferido
            if cliente.horario_preferido:
                preferencias["horario_preferido"] = cliente.horario_preferido

            nome_real = cliente.nome and cliente.nome != "Cliente"
            is_primeira_vez = not nome_real and len(conversas) == 0

            return {
                "id": cliente.id,
                "nome": cliente.nome or "Cliente",
                "nome_conhecido": bool(nome_real),
                "is_primeira_vez": is_primeira_vez,
                "sexo": getattr(cliente, "sexo", None),
                "telefone": cliente.telefone,
                "historico_servicos": historico_servicos,
                "preferencias": preferencias,
                "total_visitas": len(agendamentos),
                "memorias": [{"tipo": m.tipo, "conteudo": m.conteudo} for m in memorias]
            }
        except Exception as e:
            logger.error("Erro ao obter contexto: %s", str(e))
            return {"nome": "Cliente", "historico_servicos": [], "preferencias": {}}

    @staticmethod
    def obter_historico_conversas(db, cliente_id, limite=5):
        """Retorna historico de conversas recentes"""
        try:
            conversas = db.query(Conversa)\
                .filter(Conversa.cliente_id == cliente_id)\
                .order_by(desc(Conversa.timestamp))\
                .limit(limite).all()
            return [
                {
                    "mensagem_usuario": c.mensagem_usuario,
                    "resposta_marina": c.resposta_marina,
                    "intencao": c.intencao
                }
                for c in reversed(conversas)
            ]
        except Exception as e:
            logger.error("Erro ao obter historico: %s", str(e))
            return []

    @staticmethod
    def salvar_conversa(db, cliente_id, mensagem_usuario, resposta_marina, intencao, contexto=None):
        """Salva conversa no historico"""
        try:
            conversa = Conversa(
                cliente_id=cliente_id,
                mensagem_usuario=mensagem_usuario,
                resposta_marina=resposta_marina,
                intencao=intencao,
                contexto=str(contexto) if contexto else None,
                timestamp=datetime.utcnow()
            )
            db.add(conversa)
            db.commit()
            return conversa
        except Exception as e:
            logger.error("Erro ao salvar conversa: %s", str(e))
            db.rollback()

    @staticmethod
    def listar_clientes(db, skip=0, limit=100):
        return db.query(Cliente)\
            .order_by(desc(Cliente.ultima_interacao))\
            .offset(skip).limit(limit).all()

    @staticmethod
    def atualizar_memoria(db, cliente_id, tipo, conteudo, relevancia=1.0):
        try:
            memoria = MemoriaIA(
                cliente_id=cliente_id,
                tipo=tipo,
                conteudo=conteudo,
                relevancia=relevancia,
                timestamp=datetime.utcnow()
            )
            db.add(memoria)
            db.commit()
            return memoria
        except Exception as e:
            logger.error("Erro ao salvar memoria: %s", str(e))
            db.rollback()


cliente_service = ClienteService()
