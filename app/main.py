"""
Marina - Agente de IA para NGHair
Versão adaptada para hospedagem compartilhada Hostinger (Flask + Python 3.6+)
"""
import logging
import json
import os
import sys
import threading
from datetime import datetime
from flask import Flask, request, jsonify

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.models.database import SessionLocal, criar_tabelas
from app.services.cliente_service import cliente_service
from app.services.ai_core import ai_core
from app.services.evolution_api import evolution_api_client
from config import WHATSAPP_INSTANCE_NAME

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('marina.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

app = Flask(__name__)
criar_tabelas()
logger.info("Marina iniciada com sucesso!")


@app.route('/health', methods=['GET'])
def health_check():
    return jsonify({
        "status": "ok",
        "agente": "Marina",
        "salao": "NGHair",
        "versao": "1.0.0",
        "timestamp": datetime.now().isoformat()
    })


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
        direction = msg_data.get('direction', '')
        if direction == 'out':
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

        t = threading.Thread(
            target=processar_mensagem_background,
            args=(telefone, texto, remote_jid)
        )
        t.daemon = True
        t.start()

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
                mensagem="Desculpe, tive um problema tecnico. Pode tentar novamente? 😊"
            )
        except Exception:
            pass
    finally:
        db.close()


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


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    logger.info("Iniciando Marina na porta %d...", port)
    app.run(host='0.0.0.0', port=port, debug=False, threaded=True)
