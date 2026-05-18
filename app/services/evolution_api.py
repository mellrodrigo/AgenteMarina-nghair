"""
Servico de integracao com Evolution API para WhatsApp
Compativel com Python 3.6+ (usa requests em vez de httpx)
"""
import logging
import json
import requests
import os

logger = logging.getLogger(__name__)

EVOLUTION_API_URL = os.environ.get("EVOLUTION_API_URL", "http://localhost:8080")
EVOLUTION_API_KEY = os.environ.get("EVOLUTION_API_KEY", "")
WHATSAPP_INSTANCE_NAME = os.environ.get("WHATSAPP_INSTANCE_NAME", "nghair")


class EvolutionAPIClient:
    """Cliente para interagir com Evolution API"""

    def __init__(self):
        self.base_url = EVOLUTION_API_URL.rstrip("/")
        self.api_key = EVOLUTION_API_KEY

    def _headers(self):
        return {
            "Content-Type": "application/json",
            "apikey": self.api_key
        }

    def enviar_mensagem(self, instance, numero, mensagem):
        """Envia mensagem de texto via WhatsApp (Evolution API v2)"""
        try:
            url = "{}/message/sendText/{}".format(self.base_url, instance)
            payload = {
                "number": numero,
                "text": mensagem,
            }
            resp = requests.post(url, json=payload, headers=self._headers(), timeout=30)
            if resp.status_code in [200, 201]:
                logger.info("Mensagem enviada para %s", numero)
                return True
            else:
                logger.error("Erro ao enviar mensagem: %s %s", resp.status_code, resp.text[:200])
                return False
        except Exception as e:
            logger.error("Excecao ao enviar mensagem: %s", str(e))
            return False

    def criar_instancia(self, instance_name):
        """Cria uma nova instancia WhatsApp"""
        try:
            url = "{}/instance/create".format(self.base_url)
            payload = {
                "instanceName": instance_name,
                "token": "",
                "qrcode": True
            }
            resp = requests.post(url, json=payload, headers=self._headers(), timeout=30)
            return resp.json() if resp.status_code in [200, 201] else None
        except Exception as e:
            logger.error("Erro ao criar instancia: %s", str(e))
            return None

    def obter_qrcode(self, instance):
        """Obtem QR code para conectar WhatsApp"""
        try:
            url = "{}/instance/connect/{}".format(self.base_url, instance)
            resp = requests.get(url, headers=self._headers(), timeout=30)
            return resp.json() if resp.status_code == 200 else None
        except Exception as e:
            logger.error("Erro ao obter QR code: %s", str(e))
            return None

    def verificar_conexao(self, instance):
        """Verifica se a instancia esta conectada"""
        try:
            url = "{}/instance/connectionState/{}".format(self.base_url, instance)
            resp = requests.get(url, headers=self._headers(), timeout=10)
            if resp.status_code == 200:
                data = resp.json()
                return data.get("instance", {}).get("state") == "open"
            return False
        except Exception as e:
            logger.error("Erro ao verificar conexao: %s", str(e))
            return False

    def extrair_audio_base64(self, msg_data: dict):
        """Extrai bytes de áudio de uma mensagem WhatsApp.
        Tenta base64 direto no payload (WEBHOOK_GLOBAL_BASE64=true) e,
        como fallback, chama o endpoint /chat/getBase64FromMediaMessage.
        Retorna (bytes, mimetype) ou (None, None)."""
        import base64 as b64lib

        msg = msg_data.get("message", {})
        mimetype = "audio/ogg; codecs=opus"

        # Descobre o mimetype real do áudio
        for campo in ["audioMessage", "pttMessage"]:
            audio = msg.get(campo, {})
            if isinstance(audio, dict):
                mimetype = audio.get("mimetype", mimetype)
                # Caso WEBHOOK_GLOBAL_BASE64=true esteja ativo
                b64 = audio.get("base64", "")
                if b64:
                    try:
                        return b64lib.b64decode(b64), mimetype
                    except Exception as e:
                        logger.error("Erro ao decodificar base64 de áudio: %s", str(e))
                break

        # Fallback: pede ao Evolution API para baixar e descriptografar o áudio
        # O endpoint espera o objeto completo {key, message} do webhook
        instance = WHATSAPP_INSTANCE_NAME
        url = "{}/chat/getBase64FromMediaMessage/{}".format(self.base_url, instance)
        payload = {
            "message": {
                "key": msg_data.get("key", {}),
                "message": msg,
            },
            "convertToMp4": False,
        }
        try:
            logger.info("Tentando /chat/getBase64FromMediaMessage para áudio...")
            resp = requests.post(url, json=payload, headers=self._headers(), timeout=60)
            if resp.status_code == 200:
                data = resp.json()
                b64 = (data.get("base64") or
                       data.get("data", {}).get("base64", "") or
                       data.get("mediaData", {}).get("base64", ""))
                if b64:
                    return b64lib.b64decode(b64), mimetype
            logger.error("getBase64FromMediaMessage: %s %s", resp.status_code, resp.text[:300])
        except Exception as e:
            logger.error("Erro em getBase64FromMediaMessage: %s", str(e))

        return None, None

    def configurar_webhook(self, instance, webhook_url):
        """Configura webhook para receber mensagens"""
        try:
            url = "{}/webhook/set/{}".format(self.base_url, instance)
            payload = {
                "url": webhook_url,
                "webhook_by_events": False,
                "events": ["MESSAGES_UPSERT", "MESSAGES_UPDATE", "CONNECTION_UPDATE"]
            }
            resp = requests.post(url, json=payload, headers=self._headers(), timeout=30)
            if resp.status_code in [200, 201]:
                logger.info("Webhook configurado: %s", webhook_url)
                return True
            return False
        except Exception as e:
            logger.error("Erro ao configurar webhook: %s", str(e))
            return False


# Instancias globais
evolution_api = EvolutionAPIClient()
evolution_api_client = evolution_api
