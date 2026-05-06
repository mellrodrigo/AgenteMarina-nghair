"""
API Principal da Marina
FastAPI application para o agente de IA do NGHair
"""
import logging
from fastapi import FastAPI, Depends, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from datetime import datetime
import json

# Configurações
from config import DEBUG, API_WEBHOOK_URL, LOG_LEVEL
from app.models.database import criar_tabelas, get_db
from app.schemas.whatsapp import MensagemWhatsApp, RespostaWhatsApp, WebhookEvolutionAPI
from app.services.cliente_service import cliente_service
from app.services.ai_core import ai_core
from app.services.evolution_api import evolution_api
from app.services.agendamento_service import agendamento_service

# Configurar logging
logging.basicConfig(
    level=getattr(logging, LOG_LEVEL),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Criar aplicação FastAPI
app = FastAPI(
    title="Marina - NGHair AI Agent",
    description="Agente de IA inteligente para o salão NGHair",
    version="1.0.0"
)

# Configurar CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Criar tabelas ao iniciar
@app.on_event("startup")
async def startup_event():
    """Executado ao iniciar a aplicação"""
    logger.info("Iniciando Marina...")
    criar_tabelas()
    logger.info("Banco de dados inicializado")


@app.get("/")
async def root():
    """Endpoint raiz"""
    return {
        "message": "Marina - NGHair AI Agent",
        "version": "1.0.0",
        "status": "online"
    }


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat()
    }


@app.post("/webhook/whatsapp")
async def webhook_whatsapp(
    webhook_data: WebhookEvolutionAPI,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """
    Webhook para receber mensagens do WhatsApp via Evolution API
    """
    try:
        logger.info(f"Webhook recebido: {webhook_data.event}")
        
        # Processar apenas eventos de mensagens
        if webhook_data.event != "messages.upsert":
            return {"status": "ok"}
        
        # Extrair dados da mensagem
        data = webhook_data.data
        
        # Verificar se é mensagem de entrada
        if data.get("direction") != "in":
            return {"status": "ok"}
        
        # Extrair informações
        telefone = data.get("key", {}).get("remoteJid", "").replace("@s.whatsapp.net", "")
        mensagem_texto = data.get("message", {}).get("conversation", "")
        
        if not telefone or not mensagem_texto:
            logger.warning("Dados incompletos na mensagem")
            return {"status": "ok"}
        
        logger.info(f"Mensagem recebida de {telefone}: {mensagem_texto[:50]}...")
        
        # Processar em background
        background_tasks.add_task(
            processar_mensagem_whatsapp,
            telefone,
            mensagem_texto,
            db
        )
        
        return {"status": "ok"}
        
    except Exception as e:
        logger.error(f"Erro no webhook: {str(e)}")
        return {"status": "error", "message": str(e)}


async def processar_mensagem_whatsapp(telefone: str, mensagem: str, db: Session):
    """
    Processa mensagem do WhatsApp em background
    """
    try:
        logger.info(f"Processando mensagem de {telefone}")
        
        # Obter ou criar cliente
        cliente = cliente_service.obter_ou_criar_cliente(db, telefone)
        
        # Obter contexto completo do cliente
        contexto_cliente = cliente_service.obter_info_cliente_completa(db, cliente.id)
        
        # Processar com IA
        resposta, intencao = await ai_core.processar_mensagem(
            mensagem,
            contexto_cliente,
            contexto_cliente.get("conversas_recentes", [])
        )
        
        # Salvar conversa
        cliente_service.salvar_conversa(
            db,
            cliente.id,
            mensagem,
            resposta,
            intencao,
            {"timestamp": datetime.utcnow().isoformat()}
        )
        
        # Atualizar memória se necessário
        if intencao in ["agendamento", "consulta_servicos", "consulta_preco"]:
            cliente_service.atualizar_memoria(
                db,
                cliente.id,
                f"interacao_{intencao}",
                mensagem,
                relevancia=0.8
            )
        
        # Enviar resposta via WhatsApp
        await enviar_resposta_whatsapp(telefone, resposta)
        
        logger.info(f"Resposta enviada para {telefone}")
        
    except Exception as e:
        logger.error(f"Erro ao processar mensagem: {str(e)}")


async def enviar_resposta_whatsapp(telefone: str, mensagem: str):
    """
    Envia resposta via WhatsApp usando Evolution API
    """
    try:
        # Remover caracteres especiais do número
        numero_limpo = telefone.replace("@s.whatsapp.net", "").replace("+", "")
        
        # Enviar via Evolution API
        sucesso = await evolution_api.enviar_mensagem(numero_limpo, mensagem)
        
        if sucesso:
            logger.info(f"Mensagem enviada com sucesso para {numero_limpo}")
        else:
            logger.error(f"Falha ao enviar mensagem para {numero_limpo}")
        
    except Exception as e:
        logger.error(f"Erro ao enviar resposta: {str(e)}")


@app.post("/api/clientes/{cliente_id}/agendamento")
async def criar_agendamento(
    cliente_id: int,
    data: str,
    servico: str,
    profissional: str,
    db: Session = Depends(get_db)
):
    """
    Cria um novo agendamento para o cliente
    """
    try:
        from app.models.database import Agendamento
        from datetime import datetime
        
        cliente = cliente_service.obter_cliente_por_id(db, cliente_id)
        if not cliente:
            raise HTTPException(status_code=404, detail="Cliente não encontrado")
        
        # Criar agendamento
        agendamento = Agendamento(
            cliente_id=cliente_id,
            data=datetime.fromisoformat(data),
            servico=servico,
            profissional=profissional,
            status="confirmado"
        )
        
        db.add(agendamento)
        db.commit()
        db.refresh(agendamento)
        
        logger.info(f"Agendamento criado para cliente {cliente_id}")
        
        return {
            "id": agendamento.id,
            "cliente_id": cliente_id,
            "data": agendamento.data.isoformat(),
            "servico": servico,
            "profissional": profissional,
            "status": "confirmado"
        }
        
    except Exception as e:
        logger.error(f"Erro ao criar agendamento: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/clientes/{cliente_id}")
async def obter_cliente(cliente_id: int, db: Session = Depends(get_db)):
    """Obtém informações do cliente"""
    cliente = cliente_service.obter_cliente_por_id(db, cliente_id)
    if not cliente:
        raise HTTPException(status_code=404, detail="Cliente não encontrado")
    
    return cliente_service.obter_info_cliente_completa(db, cliente_id)


@app.get("/api/clientes")
async def listar_clientes(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    """Lista clientes"""
    clientes = cliente_service.listar_clientes(db, skip, limit)
    return [
        {
            "id": c.id,
            "nome": c.nome,
            "telefone": c.telefone,
            "ultima_interacao": c.ultima_interacao.isoformat()
        }
        for c in clientes
    ]


@app.get("/api/clientes/{cliente_id}/estatisticas")
async def obter_estatisticas(cliente_id: int, db: Session = Depends(get_db)):
    """Obtém estatísticas do cliente"""
    return cliente_service.obter_estatisticas_cliente(db, cliente_id)


if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=DEBUG,
        log_level=LOG_LEVEL.lower()
    )
