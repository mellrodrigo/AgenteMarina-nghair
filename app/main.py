"""
Marina — Agente de IA para NGHair
Flask + Gunicorn
"""
import logging
import os
import sys
import threading
import schedule
import time
from datetime import datetime
from flask import Flask, request, jsonify

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.models.database import SessionLocal, criar_tabelas
from app.services.cliente_service import cliente_service
from app.services.ai_core import ai_core
from app.services.evolution_api import evolution_api_client
from app.services.trinks_api import trinks_api
from config import WHATSAPP_INSTANCE_NAME, TRINKS_SYNC_INTERVAL

os.makedirs("logs", exist_ok=True)
os.makedirs("data", exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/marina.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

app = Flask(__name__)
criar_tabelas()


# ── Sync Trinks automático ────────────────────────────────────

def _executar_sync():
    db = SessionLocal()
    try:
        logger.info("Sync automático Trinks iniciado...")
        ok = trinks_api.sincronizar_dados(db)
        if ok:
            # Atualiza o prompt da IA com os novos dados
            ai_core.atualizar_contexto_trinks(db)
            logger.info("Sync Trinks concluído e IA atualizada")
        else:
            logger.warning("Sync Trinks falhou")
    except Exception as e:
        logger.error("Erro no sync Trinks: %s", str(e))
    finally:
        db.close()


def _loop_agendador():
    """Loop do scheduler em thread separada"""
    intervalo_horas = max(1, TRINKS_SYNC_INTERVAL // 3600)
    schedule.every(intervalo_horas).hours.do(_executar_sync)
    logger.info("Agendador Trinks: sync a cada %dh", intervalo_horas)
    while True:
        schedule.run_pending()
        time.sleep(60)


def _iniciar_sync_background():
    """Sync inicial + inicia loop agendado"""
    # Sync imediato na inicialização
    threading.Thread(target=_executar_sync, daemon=True).start()
    # Loop de sync periódico
    threading.Thread(target=_loop_agendador, daemon=True).start()


_iniciar_sync_background()
logger.info("Marina iniciada!")


# ── Health ────────────────────────────────────────────────────

@app.route('/health', methods=['GET'])
def health_check():
    return jsonify({
        "status": "ok",
        "agente": "Marina",
        "salao": "NGHair",
        "versao": "2.1.0",
        "timestamp": datetime.now().isoformat()
    })


# ── Webhook WhatsApp ──────────────────────────────────────────

@app.route('/webhook/whatsapp', methods=['POST'])
def webhook_whatsapp():
    try:
        data = request.get_json(force=True, silent=True)
        if not data:
            return jsonify({"status": "ok"}), 200

        logger.info("Webhook recebido: %s", str(data)[:200])

        event = data.get('event', '')
        if event not in ['messages.upsert', 'MESSAGES_UPSERT']:
            return jsonify({"status": "ok"}), 200

        msg_data = data.get('data', {})
        if msg_data.get('direction') == 'out':
            return jsonify({"status": "ok"}), 200

        key = msg_data.get('key', {})
        remote_jid = key.get('remoteJid', '')

        if '@g.us' in remote_jid:
            return jsonify({"status": "ok"}), 200

        telefone = remote_jid.replace('@s.whatsapp.net', '').replace('@c.us', '')

        message = msg_data.get('message', {})
        texto = (
            message.get('conversation') or
            message.get('extendedTextMessage', {}).get('text') or
            message.get('imageMessage', {}).get('caption') or ''
        )

        if not texto or not telefone:
            return jsonify({"status": "ok"}), 200

        logger.info("Mensagem de %s: %s", telefone, texto[:100])

        threading.Thread(
            target=processar_mensagem_background,
            args=(telefone, texto, remote_jid),
            daemon=True
        ).start()

        return jsonify({"status": "ok"}), 200

    except Exception as e:
        logger.error("Erro no webhook: %s", str(e))
        return jsonify({"status": "error"}), 500


def processar_mensagem_background(telefone, texto, remote_jid):
    db = SessionLocal()
    try:
        cliente = cliente_service.buscar_ou_criar_cliente(db, telefone)
        contexto = cliente_service.obter_contexto_cliente(db, cliente.id)
        historico = cliente_service.obter_historico_conversas(db, cliente.id, limite=5)

        resposta, intencao = ai_core.processar_mensagem_sync(
            mensagem=texto,
            cliente_info=contexto,
            historico_conversas=historico
        )

        cliente_service.salvar_conversa(
            db=db,
            cliente_id=cliente.id,
            mensagem_usuario=texto,
            resposta_marina=resposta,
            intencao=intencao
        )

        evolution_api_client.enviar_mensagem(
            instance=WHATSAPP_INSTANCE_NAME,
            numero=remote_jid,
            mensagem=resposta
        )

        logger.info("Resposta enviada para %s", telefone)

    except Exception as e:
        logger.error("Erro ao processar mensagem de %s: %s", telefone, str(e))
        try:
            evolution_api_client.enviar_mensagem(
                instance=WHATSAPP_INSTANCE_NAME,
                numero=remote_jid,
                mensagem="Desculpe, tive um probleminha técnico. Pode tentar novamente? 😊"
            )
        except Exception:
            pass
    finally:
        db.close()


# ── Clientes ──────────────────────────────────────────────────

@app.route('/clientes', methods=['GET'])
def listar_clientes():
    db = SessionLocal()
    try:
        clientes = cliente_service.listar_clientes(db)
        return jsonify({
            "total": len(clientes),
            "clientes": [{"id": c.id, "nome": c.nome, "telefone": c.telefone} for c in clientes]
        })
    finally:
        db.close()


# ── Status ────────────────────────────────────────────────────

@app.route('/status', methods=['GET'])
def status():
    db = SessionLocal()
    try:
        total = len(cliente_service.listar_clientes(db))
        return jsonify({
            "status": "online",
            "agente": "Marina",
            "salao": "NGHair",
            "total_clientes": total,
            "timestamp": datetime.now().isoformat()
        })
    finally:
        db.close()


# ── Trinks API ────────────────────────────────────────────────

@app.route('/trinks/status', methods=['GET'])
def trinks_status():
    resultado = trinks_api.testar_conexao()
    ultima = trinks_api.ultima_sincronizacao
    return jsonify({
        "trinks_api": resultado,
        "ultima_sincronizacao": ultima.isoformat() if ultima else None,
        "timestamp": datetime.now().isoformat()
    }), 200 if resultado["ok"] else 503


@app.route('/trinks/sync', methods=['POST'])
def trinks_sync():
    db = SessionLocal()
    try:
        logger.info("Sync manual Trinks via API")
        sucesso = trinks_api.sincronizar_dados(db)
        if sucesso:
            ai_core.atualizar_contexto_trinks(db)
            return jsonify({
                "status": "ok",
                "mensagem": "Sincronização concluída",
                "ultima_sincronizacao": trinks_api.ultima_sincronizacao.isoformat()
            })
        return jsonify({"status": "erro", "mensagem": "Falha na sincronização — veja os logs"}), 500
    finally:
        db.close()


@app.route('/trinks/servicos', methods=['GET'])
def trinks_servicos():
    """Lista serviços do banco local (sincronizados do Trinks)"""
    db = SessionLocal()
    try:
        from app.models.database import Servico
        servicos = db.query(Servico).filter(Servico.ativo == True).all()
        return jsonify({
            "total": len(servicos),
            "fonte": "banco_local_trinks",
            "ultima_sincronizacao": trinks_api.ultima_sincronizacao.isoformat() if trinks_api.ultima_sincronizacao else None,
            "servicos": [
                {
                    "nome": s.nome,
                    "categoria": s.categoria,
                    "preco": s.preco,
                    "duracao_minutos": s.duracao_minutos
                } for s in servicos
            ]
        })
    finally:
        db.close()


@app.route('/trinks/profissionais', methods=['GET'])
def trinks_profissionais():
    """Lista profissionais do banco local (sincronizados do Trinks)"""
    db = SessionLocal()
    try:
        from app.models.database import Profissional
        profissionais = db.query(Profissional).filter(Profissional.ativo == True).all()
        return jsonify({
            "total": len(profissionais),
            "profissionais": [{"nome": p.nome, "cargo": p.cargo} for p in profissionais]
        })
    finally:
        db.close()


@app.route('/trinks/agendamentos', methods=['GET'])
def trinks_agendamentos():
    """Lista agendamentos direto da API Trinks (tempo real)"""
    from datetime import timedelta
    hoje = datetime.now().strftime("%Y-%m-%d")
    em_30_dias = (datetime.now() + timedelta(days=30)).strftime("%Y-%m-%d")
    agendamentos = trinks_api.listar_agendamentos(data_inicio=hoje, data_fim=em_30_dias)
    return jsonify({"total": len(agendamentos), "agendamentos": agendamentos})


@app.route('/trinks/agendamentos', methods=['POST'])
def criar_agendamento_trinks():
    """Cria agendamento diretamente no Trinks"""
    payload = request.get_json(force=True, silent=True)
    if not payload:
        return jsonify({"erro": "Payload inválido"}), 400
    resultado = trinks_api.criar_agendamento(payload)
    if resultado:
        return jsonify({"status": "ok", "agendamento": resultado}), 201
    return jsonify({"status": "erro", "mensagem": "Falha ao criar agendamento no Trinks"}), 500


@app.route('/trinks/debug', methods=['GET'])
def trinks_debug():
    """Retorna resposta bruta da API Trinks para diagnóstico de mapeamento"""
    import requests as req
    from config import TRINKS_API_KEY, TRINKS_API_URL
    headers = {
        "Authorization": "ApiKey {}".format(TRINKS_API_KEY),
        "Accept": "application/json"
    }
    resultado = {}
    for endpoint in ["/v1/servicos", "/v1/profissionais", "/v1/agendamentos"]:
        try:
            r = req.get("{}{}".format(TRINKS_API_URL, endpoint), headers=headers, timeout=15)
            resultado[endpoint] = {
                "status_code": r.status_code,
                "body": r.json() if r.ok else r.text[:500]
            }
        except Exception as e:
            resultado[endpoint] = {"erro": str(e)}
    return jsonify(resultado)


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8000))
    logger.info("Iniciando Marina na porta %d...", port)
    app.run(host='0.0.0.0', port=port, debug=False, threaded=True)
