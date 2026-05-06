"""
Serviço de gerenciamento de agendamentos
"""
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import and_, desc

from app.models.database import Agendamento, Servico, Profissional, Cliente

logger = logging.getLogger(__name__)


class AgendamentoService:
    """Serviço para gerenciar agendamentos"""

    @staticmethod
    def obter_horarios_disponiveis(
        db: Session,
        data: datetime,
        profissional_id: Optional[int] = None,
        duracao_minutos: int = 45
    ) -> List[str]:
        """
        Obtém horários disponíveis para uma data
        """
        try:
            horarios_disponiveis = []
            
            # Horários de funcionamento do salão
            hora_abertura = 8
            hora_fechamento = 19
            intervalo_minutos = 15
            
            # Gerar todos os horários possíveis
            horario_atual = datetime(data.year, data.month, data.day, hora_abertura, 0)
            horario_fechamento = datetime(data.year, data.month, data.day, hora_fechamento, 0)
            
            while horario_atual < horario_fechamento:
                horario_fim = horario_atual + timedelta(minutes=duracao_minutos)
                
                # Verificar se há conflito com agendamentos existentes
                conflito = db.query(Agendamento).filter(
                    and_(
                        Agendamento.data >= horario_atual,
                        Agendamento.data < horario_fim,
                        Agendamento.status == "confirmado"
                    )
                ).first()
                
                if not conflito:
                    horarios_disponiveis.append(horario_atual.strftime("%H:%M"))
                
                horario_atual += timedelta(minutes=intervalo_minutos)
            
            logger.info(f"Encontrados {len(horarios_disponiveis)} horários disponíveis")
            return horarios_disponiveis
            
        except Exception as e:
            logger.error(f"Erro ao obter horários: {str(e)}")
            return []

    @staticmethod
    def obter_profissionais_disponiveis(
        db: Session,
        data: datetime,
        servico_id: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        Obtém profissionais disponíveis para uma data
        """
        try:
            profissionais = db.query(Profissional)\
                .filter(Profissional.ativo == True)\
                .all()
            
            profissionais_disponiveis = []
            
            for prof in profissionais:
                # Verificar se profissional tem agendamentos nesse dia
                agendamentos_dia = db.query(Agendamento)\
                    .filter(
                        and_(
                            Agendamento.profissional == prof.nome,
                            Agendamento.data >= datetime(data.year, data.month, data.day),
                            Agendamento.data < datetime(data.year, data.month, data.day) + timedelta(days=1),
                            Agendamento.status == "confirmado"
                        )
                    ).count()
                
                profissionais_disponiveis.append({
                    "id": prof.id,
                    "nome": prof.nome,
                    "cargo": prof.cargo,
                    "agendamentos_hoje": agendamentos_dia
                })
            
            logger.info(f"Encontrados {len(profissionais_disponiveis)} profissionais disponíveis")
            return profissionais_disponiveis
            
        except Exception as e:
            logger.error(f"Erro ao obter profissionais: {str(e)}")
            return []

    @staticmethod
    def criar_agendamento(
        db: Session,
        cliente_id: int,
        data: datetime,
        servico: str,
        profissional: str,
        valor: Optional[float] = None
    ) -> Optional[Agendamento]:
        """
        Cria um novo agendamento
        """
        try:
            agendamento = Agendamento(
                cliente_id=cliente_id,
                data=data,
                servico=servico,
                profissional=profissional,
                valor=valor,
                status="confirmado",
                data_criacao=datetime.utcnow(),
                data_atualizacao=datetime.utcnow()
            )
            
            db.add(agendamento)
            db.commit()
            db.refresh(agendamento)
            
            logger.info(f"Agendamento criado: {agendamento.id}")
            return agendamento
            
        except Exception as e:
            logger.error(f"Erro ao criar agendamento: {str(e)}")
            db.rollback()
            return None

    @staticmethod
    def cancelar_agendamento(db: Session, agendamento_id: int) -> bool:
        """
        Cancela um agendamento
        """
        try:
            agendamento = db.query(Agendamento)\
                .filter(Agendamento.id == agendamento_id)\
                .first()
            
            if not agendamento:
                return False
            
            agendamento.status = "cancelado"
            agendamento.data_atualizacao = datetime.utcnow()
            
            db.commit()
            logger.info(f"Agendamento {agendamento_id} cancelado")
            return True
            
        except Exception as e:
            logger.error(f"Erro ao cancelar agendamento: {str(e)}")
            db.rollback()
            return False

    @staticmethod
    def obter_agendamentos_cliente(
        db: Session,
        cliente_id: int,
        apenas_futuros: bool = True
    ) -> List[Agendamento]:
        """
        Obtém agendamentos do cliente
        """
        try:
            query = db.query(Agendamento)\
                .filter(Agendamento.cliente_id == cliente_id)
            
            if apenas_futuros:
                query = query.filter(Agendamento.data >= datetime.utcnow())
            
            agendamentos = query.order_by(Agendamento.data).all()
            
            return agendamentos
            
        except Exception as e:
            logger.error(f"Erro ao obter agendamentos: {str(e)}")
            return []

    @staticmethod
    def obter_proximos_agendamentos(
        db: Session,
        cliente_id: int,
        dias: int = 7
    ) -> List[Dict[str, Any]]:
        """
        Obtém próximos agendamentos do cliente
        """
        try:
            data_inicio = datetime.utcnow()
            data_fim = data_inicio + timedelta(days=dias)
            
            agendamentos = db.query(Agendamento)\
                .filter(
                    and_(
                        Agendamento.cliente_id == cliente_id,
                        Agendamento.data >= data_inicio,
                        Agendamento.data <= data_fim,
                        Agendamento.status == "confirmado"
                    )
                ).order_by(Agendamento.data).all()
            
            return [
                {
                    "id": ag.id,
                    "data": ag.data.isoformat(),
                    "servico": ag.servico,
                    "profissional": ag.profissional,
                    "valor": ag.valor,
                    "status": ag.status
                }
                for ag in agendamentos
            ]
            
        except Exception as e:
            logger.error(f"Erro ao obter próximos agendamentos: {str(e)}")
            return []

    @staticmethod
    def sugerir_agendamento(
        db: Session,
        cliente_id: int,
        dias_futuros: int = 7
    ) -> Optional[Dict[str, Any]]:
        """
        Sugere um agendamento para o cliente baseado em histórico
        """
        try:
            cliente = db.query(Cliente).filter(Cliente.id == cliente_id).first()
            
            if not cliente:
                return None
            
            # Obter último serviço realizado
            ultimo_agendamento = db.query(Agendamento)\
                .filter(
                    and_(
                        Agendamento.cliente_id == cliente_id,
                        Agendamento.status == "realizado"
                    )
                ).order_by(desc(Agendamento.data)).first()
            
            if not ultimo_agendamento:
                # Sugerir serviço padrão
                servico_sugerido = "Corte Feminino"
            else:
                # Sugerir próximo serviço baseado no histórico
                servico_sugerido = ultimo_agendamento.servico
            
            # Obter profissional preferido
            profissional = cliente.profissional_preferido or "Qualquer profissional"
            
            # Obter próximo horário disponível
            data_sugerida = datetime.now() + timedelta(days=2)
            horarios = AgendamentoService.obter_horarios_disponiveis(db, data_sugerida)
            
            if not horarios:
                return None
            
            horario_sugerido = horarios[0]
            
            return {
                "data": data_sugerida.strftime("%d/%m/%Y"),
                "horario": horario_sugerido,
                "servico": servico_sugerido,
                "profissional": profissional
            }
            
        except Exception as e:
            logger.error(f"Erro ao sugerir agendamento: {str(e)}")
            return None

    @staticmethod
    def obter_servicos_disponiveis(db: Session) -> List[Dict[str, Any]]:
        """
        Obtém lista de serviços disponíveis
        """
        try:
            servicos = db.query(Servico)\
                .filter(Servico.ativo == True)\
                .order_by(Servico.categoria)\
                .all()
            
            return [
                {
                    "id": s.id,
                    "nome": s.nome,
                    "categoria": s.categoria,
                    "preco": s.preco,
                    "duracao_minutos": s.duracao_minutos,
                    "descricao": s.descricao
                }
                for s in servicos
            ]
            
        except Exception as e:
            logger.error(f"Erro ao obter serviços: {str(e)}")
            return []

    @staticmethod
    def formatar_agendamento_para_whatsapp(agendamento: Dict[str, Any]) -> str:
        """
        Formata agendamento para exibição no WhatsApp
        """
        return f"""
📅 *Seu Agendamento*

📆 Data: {agendamento.get('data')}
🕐 Hora: {agendamento.get('horario')}
✂️ Serviço: {agendamento.get('servico')}
👩‍💼 Profissional: {agendamento.get('profissional')}
💰 Valor: R$ {agendamento.get('valor', 'A confirmar')}

Confirma este agendamento? 👍
        """


# Instância global
agendamento_service = AgendamentoService()
