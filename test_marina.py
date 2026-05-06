"""
Testes básicos para Marina
Execute com: python test_marina.py
"""
import asyncio
import logging
from datetime import datetime

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def testar_ai_core():
    """Testa o core de IA"""
    from app.services.ai_core import ai_core
    
    logger.info("Testando AI Core...")
    
    cliente_info = {
        "nome": "Maria Silva",
        "telefone": "11999999999",
        "historico_servicos": ["Corte Feminino", "Escova Simples"],
        "preferencias": {
            "profissional_preferido": "Nilian",
            "horario_preferido": "14:00"
        }
    }
    
    resposta, intencao = await ai_core.processar_mensagem(
        "Oi Marina! Gostaria de agendar um corte",
        cliente_info
    )
    
    logger.info(f"Resposta: {resposta}")
    logger.info(f"Intenção: {intencao}")
    
    assert len(resposta) > 0, "Resposta vazia"
    assert intencao in ["agendamento", "consulta_geral"], f"Intenção inesperada: {intencao}"
    
    logger.info("✅ AI Core testado com sucesso!")


async def testar_formatadores():
    """Testa formatadores de mensagens"""
    from app.utils.formatadores import FormatadorMensagens, FormatadorDados
    
    logger.info("Testando Formatadores...")
    
    # Testar menu principal
    menu = FormatadorMensagens.formatar_menu_principal()
    assert "Olá" in menu, "Menu não contém saudação"
    
    # Testar serviços
    servicos = [
        {"nome": "Corte", "preco": 80.0, "duracao_minutos": 45},
        {"nome": "Escova", "preco": 60.0, "duracao_minutos": 45}
    ]
    msg_servicos = FormatadorMensagens.formatar_servicos(servicos)
    assert "Corte" in msg_servicos, "Serviço não formatado"
    
    # Testar formatação de moeda
    moeda = FormatadorDados.formatar_moeda(80.50)
    assert "R$" in moeda, "Moeda não formatada"
    
    logger.info("✅ Formatadores testados com sucesso!")


async def testar_banco_dados():
    """Testa banco de dados"""
    from app.models.database import criar_tabelas, SessionLocal, Cliente
    from datetime import datetime
    
    logger.info("Testando Banco de Dados...")
    
    # Criar tabelas
    criar_tabelas()
    
    # Criar cliente de teste
    db = SessionLocal()
    
    cliente = Cliente(
        nome="Cliente Teste",
        telefone="11988888888",
        email="teste@email.com",
        data_criacao=datetime.utcnow(),
        ultima_interacao=datetime.utcnow()
    )
    
    db.add(cliente)
    db.commit()
    db.refresh(cliente)
    
    # Verificar
    cliente_recuperado = db.query(Cliente).filter(Cliente.id == cliente.id).first()
    assert cliente_recuperado is not None, "Cliente não foi salvo"
    assert cliente_recuperado.nome == "Cliente Teste", "Nome do cliente incorreto"
    
    # Limpar
    db.delete(cliente_recuperado)
    db.commit()
    db.close()
    
    logger.info("✅ Banco de Dados testado com sucesso!")


async def testar_evolution_api():
    """Testa cliente Evolution API"""
    from app.services.evolution_api import evolution_api
    
    logger.info("Testando Evolution API Client...")
    
    # Verificar se consegue obter status
    status = await evolution_api.obter_status_conexao()
    logger.info(f"Status da conexão: {status}")
    
    logger.info("✅ Evolution API Client testado com sucesso!")


async def testar_agendamento_service():
    """Testa serviço de agendamento"""
    from app.services.agendamento_service import agendamento_service
    from app.models.database import criar_tabelas, SessionLocal
    
    logger.info("Testando Agendamento Service...")
    
    criar_tabelas()
    db = SessionLocal()
    
    # Testar obtenção de horários
    from datetime import datetime, timedelta
    data_teste = datetime.now() + timedelta(days=1)
    horarios = agendamento_service.obter_horarios_disponiveis(db, data_teste)
    
    assert len(horarios) > 0, "Nenhum horário disponível"
    logger.info(f"Horários disponíveis: {len(horarios)}")
    
    # Testar obtenção de profissionais
    profissionais = agendamento_service.obter_profissionais_disponiveis(db, data_teste)
    logger.info(f"Profissionais disponíveis: {len(profissionais)}")
    
    db.close()
    
    logger.info("✅ Agendamento Service testado com sucesso!")


async def executar_testes():
    """Executa todos os testes"""
    logger.info("=" * 50)
    logger.info("🧪 Iniciando testes da Marina...")
    logger.info("=" * 50)
    
    try:
        await testar_formatadores()
        await testar_banco_dados()
        await testar_agendamento_service()
        await testar_ai_core()
        await testar_evolution_api()
        
        logger.info("=" * 50)
        logger.info("✅ Todos os testes passaram com sucesso!")
        logger.info("=" * 50)
        
    except Exception as e:
        logger.error(f"❌ Erro durante os testes: {str(e)}")
        raise


if __name__ == "__main__":
    asyncio.run(executar_testes())
