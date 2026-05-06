"""
Serviço de integração com Evolution API para WhatsApp
"""
import logging
import httpx
import json
from typing import Optional, Dict, Any
from datetime import datetime

from config import EVOLUTION_API_URL, EVOLUTION_API_KEY, WHATSAPP_INSTANCE_NAME

logger = logging.getLogger(__name__)


class EvolutionAPIClient:
    """Cliente para interagir com Evolution API"""

    def __init__(self):
        self.base_url = EVOLUTION_API_URL.rstrip("/")
        self.api_key = EVOLUTION_API_KEY
        self.instance_name = WHATSAPP_INSTANCE_NAME
        self.timeout = 30

    def _get_headers(self) -> Dict[str, str]:
        """Retorna headers padrão para requisições"""
        return {
            "apikey": self.api_key,
            "Content-Type": "application/json"
        }

    async def criar_instancia(self) -> bool:
        """
        Cria uma nova instância do WhatsApp
        """
        try:
            logger.info(f"Criando instância {self.instance_name}...")
            
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    f"{self.base_url}/instance/create",
                    headers=self._get_headers(),
                    json={
                        "instanceName": self.instance_name,
                        "qrcode": True
                    }
                )
                
                if response.status_code in [200, 201]:
                    logger.info(f"Instância {self.instance_name} criada com sucesso")
                    return True
                else:
                    logger.error(f"Erro ao criar instância: {response.text}")
                    return False
                    
        except Exception as e:
            logger.error(f"Erro ao criar instância: {str(e)}")
            return False

    async def obter_qrcode(self) -> Optional[str]:
        """
        Obtém QR code para conectar WhatsApp
        """
        try:
            logger.info(f"Obtendo QR code para {self.instance_name}...")
            
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(
                    f"{self.base_url}/instance/qrcode/{self.instance_name}",
                    headers=self._get_headers()
                )
                
                if response.status_code == 200:
                    data = response.json()
                    qrcode = data.get("qrcode")
                    logger.info("QR code obtido com sucesso")
                    return qrcode
                else:
                    logger.error(f"Erro ao obter QR code: {response.text}")
                    return None
                    
        except Exception as e:
            logger.error(f"Erro ao obter QR code: {str(e)}")
            return None

    async def obter_status_conexao(self) -> Dict[str, Any]:
        """
        Obtém status da conexão WhatsApp
        """
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(
                    f"{self.base_url}/instance/connectionState/{self.instance_name}",
                    headers=self._get_headers()
                )
                
                if response.status_code == 200:
                    return response.json()
                else:
                    logger.error(f"Erro ao obter status: {response.text}")
                    return {"state": "error"}
                    
        except Exception as e:
            logger.error(f"Erro ao obter status: {str(e)}")
            return {"state": "error"}

    async def enviar_mensagem(self, numero: str, mensagem: str) -> bool:
        """
        Envia mensagem de texto via WhatsApp
        
        Args:
            numero: Número do WhatsApp (com código do país, sem +)
            mensagem: Texto da mensagem
        """
        try:
            # Garantir que o número está no formato correto
            if not numero.endswith("@s.whatsapp.net"):
                numero = f"{numero}@s.whatsapp.net"
            
            logger.info(f"Enviando mensagem para {numero}")
            
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    f"{self.base_url}/message/sendText/{self.instance_name}",
                    headers=self._get_headers(),
                    json={
                        "number": numero,
                        "text": mensagem
                    }
                )
                
                if response.status_code in [200, 201]:
                    logger.info(f"Mensagem enviada com sucesso para {numero}")
                    return True
                else:
                    logger.error(f"Erro ao enviar mensagem: {response.text}")
                    return False
                    
        except Exception as e:
            logger.error(f"Erro ao enviar mensagem: {str(e)}")
            return False

    async def enviar_mensagem_com_midia(
        self,
        numero: str,
        url_midia: str,
        tipo_midia: str = "image",
        caption: Optional[str] = None
    ) -> bool:
        """
        Envia mensagem com mídia (imagem, vídeo, documento)
        
        Args:
            numero: Número do WhatsApp
            url_midia: URL da mídia
            tipo_midia: "image", "video", "document"
            caption: Legenda (opcional)
        """
        try:
            if not numero.endswith("@s.whatsapp.net"):
                numero = f"{numero}@s.whatsapp.net"
            
            logger.info(f"Enviando {tipo_midia} para {numero}")
            
            endpoint_map = {
                "image": "sendImage",
                "video": "sendVideo",
                "document": "sendDocument",
                "audio": "sendAudio"
            }
            
            endpoint = endpoint_map.get(tipo_midia, "sendImage")
            
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    f"{self.base_url}/message/{endpoint}/{self.instance_name}",
                    headers=self._get_headers(),
                    json={
                        "number": numero,
                        "mediaUrl": url_midia,
                        "caption": caption or ""
                    }
                )
                
                if response.status_code in [200, 201]:
                    logger.info(f"{tipo_midia.capitalize()} enviado com sucesso")
                    return True
                else:
                    logger.error(f"Erro ao enviar {tipo_midia}: {response.text}")
                    return False
                    
        except Exception as e:
            logger.error(f"Erro ao enviar {tipo_midia}: {str(e)}")
            return False

    async def enviar_botoes(
        self,
        numero: str,
        titulo: str,
        corpo: str,
        botoes: list,
        rodape: Optional[str] = None
    ) -> bool:
        """
        Envia mensagem com botões interativos
        
        Args:
            numero: Número do WhatsApp
            titulo: Título da mensagem
            corpo: Corpo da mensagem
            botoes: Lista de botões [{"id": "1", "title": "Opção 1"}, ...]
            rodape: Rodapé (opcional)
        """
        try:
            if not numero.endswith("@s.whatsapp.net"):
                numero = f"{numero}@s.whatsapp.net"
            
            logger.info(f"Enviando mensagem com botões para {numero}")
            
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    f"{self.base_url}/message/sendButtons/{self.instance_name}",
                    headers=self._get_headers(),
                    json={
                        "number": numero,
                        "title": titulo,
                        "description": corpo,
                        "buttons": botoes,
                        "footer": rodape or ""
                    }
                )
                
                if response.status_code in [200, 201]:
                    logger.info("Mensagem com botões enviada com sucesso")
                    return True
                else:
                    logger.error(f"Erro ao enviar botões: {response.text}")
                    return False
                    
        except Exception as e:
            logger.error(f"Erro ao enviar botões: {str(e)}")
            return False

    async def enviar_lista(
        self,
        numero: str,
        titulo: str,
        corpo: str,
        botao_titulo: str,
        secoes: list,
        rodape: Optional[str] = None
    ) -> bool:
        """
        Envia mensagem com lista de opções
        
        Args:
            numero: Número do WhatsApp
            titulo: Título da mensagem
            corpo: Corpo da mensagem
            botao_titulo: Título do botão
            secoes: Lista de seções com opções
            rodape: Rodapé (opcional)
        """
        try:
            if not numero.endswith("@s.whatsapp.net"):
                numero = f"{numero}@s.whatsapp.net"
            
            logger.info(f"Enviando lista para {numero}")
            
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    f"{self.base_url}/message/sendList/{self.instance_name}",
                    headers=self._get_headers(),
                    json={
                        "number": numero,
                        "title": titulo,
                        "description": corpo,
                        "buttonText": botao_titulo,
                        "sections": secoes,
                        "footer": rodape or ""
                    }
                )
                
                if response.status_code in [200, 201]:
                    logger.info("Lista enviada com sucesso")
                    return True
                else:
                    logger.error(f"Erro ao enviar lista: {response.text}")
                    return False
                    
        except Exception as e:
            logger.error(f"Erro ao enviar lista: {str(e)}")
            return False

    async def configurar_webhook(self, url_webhook: str) -> bool:
        """
        Configura webhook para receber mensagens
        
        Args:
            url_webhook: URL completa do webhook
        """
        try:
            logger.info(f"Configurando webhook: {url_webhook}")
            
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    f"{self.base_url}/webhook/set/{self.instance_name}",
                    headers=self._get_headers(),
                    json={
                        "url": url_webhook,
                        "events": [
                            "QRCODE_UPDATED",
                            "MESSAGES_UPSERT",
                            "MESSAGES_UPDATE",
                            "SEND_MESSAGE",
                            "CONTACTS_SET",
                            "PRESENCE_UPDATE",
                            "CHATS_SET",
                            "CHATS_UPSERT",
                            "CHATS_UPDATE",
                            "CHATS_DELETE",
                            "GROUPS_UPSERT",
                            "GROUP_UPDATE",
                            "GROUP_PARTICIPANTS_UPDATE",
                            "CONNECTION_UPDATE",
                            "CALL"
                        ]
                    }
                )
                
                if response.status_code in [200, 201]:
                    logger.info("Webhook configurado com sucesso")
                    return True
                else:
                    logger.error(f"Erro ao configurar webhook: {response.text}")
                    return False
                    
        except Exception as e:
            logger.error(f"Erro ao configurar webhook: {str(e)}")
            return False

    async def obter_chats(self) -> list:
        """Obtém lista de chats"""
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(
                    f"{self.base_url}/chat/findAll/{self.instance_name}",
                    headers=self._get_headers()
                )
                
                if response.status_code == 200:
                    return response.json()
                else:
                    logger.error(f"Erro ao obter chats: {response.text}")
                    return []
                    
        except Exception as e:
            logger.error(f"Erro ao obter chats: {str(e)}")
            return []

    async def obter_contatos(self) -> list:
        """Obtém lista de contatos"""
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(
                    f"{self.base_url}/contact/findAll/{self.instance_name}",
                    headers=self._get_headers()
                )
                
                if response.status_code == 200:
                    return response.json()
                else:
                    logger.error(f"Erro ao obter contatos: {response.text}")
                    return []
                    
        except Exception as e:
            logger.error(f"Erro ao obter contatos: {str(e)}")
            return []


# Instância global
evolution_api = EvolutionAPIClient()
