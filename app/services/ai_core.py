"""
Core de IA da Marina
Responsável por processar mensagens e gerar respostas personalizadas
"""
import logging
import json
from typing import Optional, Dict, Any, List
from datetime import datetime
from sqlalchemy.orm import Session
from openai import OpenAI

# Configurações
from config import OPENAI_API_KEY, OPENAI_MODEL, MARINA_NAME, MARINA_SALAO, MAX_CONVERSATION_HISTORY

logger = logging.getLogger(__name__)

# Inicializar cliente OpenAI
client = OpenAI(api_key=OPENAI_API_KEY)


class AICoreMariana:
    """Core de IA para processar mensagens e gerar respostas"""

    def __init__(self):
        self.model = OPENAI_MODEL
        self.marina_name = MARINA_NAME
        self.salao_name = MARINA_SALAO

    def _construir_prompt_sistema(self, cliente_info: Dict[str, Any]) -> str:
        """
        Constrói o prompt do sistema com contexto do cliente
        """
        nome_cliente = cliente_info.get("nome", "Cliente")
        historico_servicos = cliente_info.get("historico_servicos", [])
        preferencias = cliente_info.get("preferencias", {})
        
        historico_str = ", ".join(historico_servicos[-5:]) if historico_servicos else "nenhum"
        profissional_pref = preferencias.get("profissional_preferido", "qualquer")
        horario_pref = preferencias.get("horario_preferido", "qualquer")
        
        prompt = f"""Você é a Marina, uma agente de IA amigável e profissional do salão {self.salao_name}.

INFORMAÇÕES SOBRE VOCÊ:
- Nome: {self.marina_name}
- Salão: {self.salao_name}
- Tone: Profissional, amigável, acolhedora
- Objetivo: Ajudar clientes com agendamentos, consultas de serviços e recomendações personalizadas

INFORMAÇÕES SOBRE O CLIENTE:
- Nome: {nome_cliente}
- Histórico de serviços: {historico_str}
- Profissional preferido: {profissional_pref}
- Horário preferido: {horario_pref}

INSTRUÇÕES:
1. Sempre seja educada e acolhedora
2. Use o nome do cliente quando apropriado
3. Lembre-se das preferências e histórico do cliente
4. Ofereça recomendações personalizadas baseadas no histórico
5. Seja proativa em sugerir serviços
6. Mantenha respostas concisas e claras
7. Use emojis apropriados (máximo 2-3 por mensagem)
8. Se não souber algo, seja honesta e ofereça ajuda

SERVIÇOS DISPONÍVEIS:
- Corte Feminino: R$ 80,00 (45 min)
- Coloração: R$ 150,00 (120 min)
- Escova Simples: R$ 60,00 (45 min)
- Escova Cabelo Longo: R$ 80,00 (60 min)
- Manicure: R$ 50,00 (45 min)
- Pedicure: R$ 60,00 (60 min)
- Luzes: R$ 120,00 (90 min)
- Hidratação Loreal: R$ 100,00 (60 min)
- Depilação: R$ 40,00 (30 min)

Responda sempre em português brasileiro, de forma natural e conversacional."""
        
        return prompt

    async def processar_mensagem(
        self,
        mensagem: str,
        cliente_info: Dict[str, Any],
        historico_conversas: List[Dict[str, str]] = None
    ) -> tuple[str, str]:
        """
        Processa uma mensagem e retorna resposta + intenção
        
        Returns:
            (resposta, intenção)
        """
        try:
            logger.info(f"Processando mensagem de {cliente_info.get('nome')}")
            
            # Construir histórico de conversas
            messages = []
            
            if historico_conversas:
                for conv in historico_conversas[-MAX_CONVERSATION_HISTORY:]:
                    messages.append({
                        "role": "user",
                        "content": conv.get("mensagem_usuario", "")
                    })
                    messages.append({
                        "role": "assistant",
                        "content": conv.get("resposta_marina", "")
                    })
            
            # Adicionar mensagem atual
            messages.append({
                "role": "user",
                "content": mensagem
            })
            
            # Chamar OpenAI
            response = client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": self._construir_prompt_sistema(cliente_info)
                    }
                ] + messages,
                temperature=0.7,
                max_tokens=500,
                top_p=0.9
            )
            
            resposta = response.choices[0].message.content
            
            # Classificar intenção
            intencao = await self._classificar_intencao(mensagem)
            
            logger.info(f"Resposta gerada com intenção: {intencao}")
            return resposta, intencao
            
        except Exception as e:
            logger.error(f"Erro ao processar mensagem: {str(e)}")
            return "Desculpe, tive um problema ao processar sua mensagem. Pode tentar novamente?", "erro"

    async def _classificar_intencao(self, mensagem: str) -> str:
        """
        Classifica a intenção da mensagem do usuário
        """
        try:
            # Palavras-chave para classificação simples
            mensagem_lower = mensagem.lower()
            
            if any(palavra in mensagem_lower for palavra in ["agendar", "marcar", "horário", "hora"]):
                return "agendamento"
            elif any(palavra in mensagem_lower for palavra in ["preço", "valor", "custa", "quanto"]):
                return "consulta_preco"
            elif any(palavra in mensagem_lower for palavra in ["serviço", "serviços", "o que vocês fazem"]):
                return "consulta_servicos"
            elif any(palavra in mensagem_lower for palavra in ["profissional", "profissionais", "quem faz"]):
                return "consulta_profissionais"
            elif any(palavra in mensagem_lower for palavra in ["cancelar", "desmarcar"]):
                return "cancelamento"
            elif any(palavra in mensagem_lower for palavra in ["oi", "olá", "opa", "e aí"]):
                return "saudacao"
            else:
                return "consulta_geral"
                
        except Exception as e:
            logger.error(f"Erro ao classificar intenção: {str(e)}")
            return "desconhecida"

    async def gerar_recomendacao(self, cliente_info: Dict[str, Any]) -> str:
        """
        Gera uma recomendação personalizada para o cliente
        """
        try:
            historico = cliente_info.get("historico_servicos", [])
            
            if not historico:
                return "Que tal começar com um corte e escova? 💇‍♀️"
            
            # Lógica simples de recomendação
            ultimo_servico = historico[-1] if historico else None
            
            recomendacoes = {
                "Corte Feminino": "Que tal uma hidratação para manter o cabelo brilhante? ✨",
                "Coloração": "Que tal um corte para realçar a cor? 💇‍♀️",
                "Escova Simples": "Que tal fazer uma coloração para um visual novo? 🎨",
                "Manicure": "Que tal complementar com uma pedicure? 💅",
                "Pedicure": "Que tal uma manicure para ficar perfeita? 💅",
            }
            
            return recomendacoes.get(ultimo_servico, "Que tal agendar um serviço conosco? 💇‍♀️")
            
        except Exception as e:
            logger.error(f"Erro ao gerar recomendação: {str(e)}")
            return "Que tal agendar um serviço conosco? 💇‍♀️"


# Instância global
ai_core = AICoreMariana()
