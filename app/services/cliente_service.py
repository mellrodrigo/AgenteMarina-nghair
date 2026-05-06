"""
Serviço de gerenciamento de clientes
"""
import logging
from typing import Optional, List, Dict, Any
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy import desc

from app.models.database import Cliente, Conversa, MemoriaIA, Agendamento
from app.schemas.cliente import ClienteCreate, ClienteUpdate

logger = logging.getLogger(__name__)


class ClienteService:
    """Serviço para gerenciar clientes"""

    @staticmethod
    def obter_ou_criar_cliente(db: Session, telefone: str, nome: str = None) -> Cliente:
        """
        Obtém um cliente existente ou cria um novo
        """
        try:
            # Procurar cliente existente
            cliente = db.query(Cliente).filter(Cliente.telefone == telefone).first()
            
            if cliente:
                # Atualizar última interação
                cliente.ultima_interacao = datetime.utcnow()
                db.commit()
                logger.info(f"Cliente existente encontrado: {cliente.nome}")
                return cliente
            
            # Criar novo cliente
            if not nome:
                nome = f"Cliente {telefone}"
            
            novo_cliente = Cliente(
                nome=nome,
                telefone=telefone,
                data_criacao=datetime.utcnow(),
                ultima_interacao=datetime.utcnow()
            )
            
            db.add(novo_cliente)
            db.commit()
            db.refresh(novo_cliente)
            
            logger.info(f"Novo cliente criado: {novo_cliente.nome} ({telefone})")
            return novo_cliente
            
        except Exception as e:
            logger.error(f"Erro ao obter/criar cliente: {str(e)}")
            db.rollback()
            raise

    @staticmethod
    def obter_cliente_por_id(db: Session, cliente_id: int) -> Optional[Cliente]:
        """Obtém cliente por ID"""
        return db.query(Cliente).filter(Cliente.id == cliente_id).first()

    @staticmethod
    def obter_cliente_por_telefone(db: Session, telefone: str) -> Optional[Cliente]:
        """Obtém cliente por telefone"""
        return db.query(Cliente).filter(Cliente.telefone == telefone).first()

    @staticmethod
    def atualizar_cliente(db: Session, cliente_id: int, dados: ClienteUpdate) -> Optional[Cliente]:
        """Atualiza dados do cliente"""
        try:
            cliente = db.query(Cliente).filter(Cliente.id == cliente_id).first()
            
            if not cliente:
                return None
            
            # Atualizar apenas campos fornecidos
            for campo, valor in dados.dict(exclude_unset=True).items():
                setattr(cliente, campo, valor)
            
            cliente.ultima_interacao = datetime.utcnow()
            db.commit()
            db.refresh(cliente)
            
            logger.info(f"Cliente {cliente_id} atualizado")
            return cliente
            
        except Exception as e:
            logger.error(f"Erro ao atualizar cliente: {str(e)}")
            db.rollback()
            raise

    @staticmethod
    def obter_info_cliente_completa(db: Session, cliente_id: int) -> Dict[str, Any]:
        """
        Obtém informações completas do cliente para contexto de IA
        """
        try:
            cliente = db.query(Cliente).filter(Cliente.id == cliente_id).first()
            
            if not cliente:
                return {}
            
            # Obter histórico de conversas
            conversas = db.query(Conversa)\
                .filter(Conversa.cliente_id == cliente_id)\
                .order_by(desc(Conversa.timestamp))\
                .limit(10)\
                .all()
            
            # Obter agendamentos
            agendamentos = db.query(Agendamento)\
                .filter(Agendamento.cliente_id == cliente_id)\
                .order_by(desc(Agendamento.data))\
                .all()
            
            # Extrair histórico de serviços
            historico_servicos = [ag.servico for ag in agendamentos if ag.status == "realizado"]
            
            # Obter memórias
            memorias = db.query(MemoriaIA)\
                .filter(MemoriaIA.cliente_id == cliente_id)\
                .order_by(desc(MemoriaIA.relevancia))\
                .all()
            
            # Construir dicionário de contexto
            contexto = {
                "id": cliente.id,
                "nome": cliente.nome,
                "telefone": cliente.telefone,
                "email": cliente.email,
                "data_criacao": cliente.data_criacao.isoformat(),
                "ultima_interacao": cliente.ultima_interacao.isoformat(),
                "historico_servicos": historico_servicos,
                "preferencias": {
                    "profissional_preferido": cliente.profissional_preferido,
                    "servico_preferido": cliente.servico_preferido,
                    "horario_preferido": cliente.horario_preferido,
                },
                "notas": cliente.notas,
                "conversas_recentes": [
                    {
                        "mensagem_usuario": c.mensagem_usuario,
                        "resposta_marina": c.resposta_marina,
                        "intencao": c.intencao,
                        "timestamp": c.timestamp.isoformat()
                    }
                    for c in conversas
                ],
                "agendamentos_proximos": [
                    {
                        "data": ag.data.isoformat(),
                        "servico": ag.servico,
                        "profissional": ag.profissional,
                        "status": ag.status
                    }
                    for ag in agendamentos if ag.status == "confirmado"
                ],
                "memorias": [
                    {
                        "tipo": m.tipo,
                        "conteudo": m.conteudo,
                        "relevancia": m.relevancia
                    }
                    for m in memorias
                ]
            }
            
            return contexto
            
        except Exception as e:
            logger.error(f"Erro ao obter info completa do cliente: {str(e)}")
            return {}

    @staticmethod
    def salvar_conversa(
        db: Session,
        cliente_id: int,
        mensagem_usuario: str,
        resposta_marina: str,
        intencao: str,
        contexto: Dict[str, Any] = None
    ) -> Conversa:
        """Salva uma conversa no histórico"""
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
            db.refresh(conversa)
            
            logger.info(f"Conversa salva para cliente {cliente_id}")
            return conversa
            
        except Exception as e:
            logger.error(f"Erro ao salvar conversa: {str(e)}")
            db.rollback()
            raise

    @staticmethod
    def atualizar_memoria(
        db: Session,
        cliente_id: int,
        tipo: str,
        conteudo: str,
        relevancia: float = 1.0
    ) -> MemoriaIA:
        """Atualiza memória de aprendizado sobre o cliente"""
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
            db.refresh(memoria)
            
            logger.info(f"Memória atualizada para cliente {cliente_id}: {tipo}")
            return memoria
            
        except Exception as e:
            logger.error(f"Erro ao atualizar memória: {str(e)}")
            db.rollback()
            raise

    @staticmethod
    def listar_clientes(db: Session, skip: int = 0, limit: int = 100) -> List[Cliente]:
        """Lista clientes com paginação"""
        return db.query(Cliente)\
            .order_by(desc(Cliente.ultima_interacao))\
            .offset(skip)\
            .limit(limit)\
            .all()

    @staticmethod
    def obter_estatisticas_cliente(db: Session, cliente_id: int) -> Dict[str, Any]:
        """Obtém estatísticas do cliente"""
        try:
            cliente = db.query(Cliente).filter(Cliente.id == cliente_id).first()
            
            if not cliente:
                return {}
            
            total_conversas = db.query(Conversa)\
                .filter(Conversa.cliente_id == cliente_id)\
                .count()
            
            total_agendamentos = db.query(Agendamento)\
                .filter(Agendamento.cliente_id == cliente_id)\
                .count()
            
            agendamentos_realizados = db.query(Agendamento)\
                .filter(Agendamento.cliente_id == cliente_id, Agendamento.status == "realizado")\
                .count()
            
            return {
                "cliente_id": cliente_id,
                "nome": cliente.nome,
                "total_conversas": total_conversas,
                "total_agendamentos": total_agendamentos,
                "agendamentos_realizados": agendamentos_realizados,
                "dias_como_cliente": (datetime.utcnow() - cliente.data_criacao).days
            }
            
        except Exception as e:
            logger.error(f"Erro ao obter estatísticas: {str(e)}")
            return {}


# Instância global
cliente_service = ClienteService()
