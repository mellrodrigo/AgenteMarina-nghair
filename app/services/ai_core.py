"""
Core de IA da Marina usando Google Gemini
Versão síncrona compatível com Python 3.6+
"""
import logging
import json
from typing import Optional, Dict, Any, List, Tuple

import google.generativeai as genai

from config import GEMINI_API_KEY, GEMINI_MODEL, MARINA_NAME, MARINA_SALAO, MAX_CONVERSATION_HISTORY

logger = logging.getLogger(__name__)

genai.configure(api_key=GEMINI_API_KEY)


class AICoreMariana:
    """Core de IA para processar mensagens usando Google Gemini (síncrono)"""

    def __init__(self):
        self.model = genai.GenerativeModel(GEMINI_MODEL)
        self.marina_name = MARINA_NAME
        self.salao_name = MARINA_SALAO

    def _construir_prompt(self, mensagem, cliente_info, historico_conversas=None):
        nome_cliente = cliente_info.get("nome", "Cliente")
        historico_servicos = cliente_info.get("historico_servicos", [])
        preferencias = cliente_info.get("preferencias", {})

        historico_str = ", ".join(historico_servicos[-5:]) if historico_servicos else "nenhum"
        profissional_pref = preferencias.get("profissional_preferido", "qualquer")
        horario_pref = preferencias.get("horario_preferido", "qualquer")

        historico_text = ""
        if historico_conversas:
            historico_text = "\nHistorico de conversas recentes:\n"
            for conv in historico_conversas[-3:]:
                historico_text += "Cliente: {}\nMarina: {}\n".format(
                    conv.get('mensagem_usuario', ''),
                    conv.get('resposta_marina', '')
                )

        prompt = """Voce e a Marina, assistente de IA do salao de beleza {salao}.

SOBRE VOCE:
- Nome: {nome}
- Salao: {salao}
- Tom: Profissional, amigavel e acolhedora
- Objetivo: Ajudar clientes com agendamentos, servicos e recomendacoes

CLIENTE:
- Nome: {nome_cliente}
- Historico de servicos: {historico_str}
- Profissional preferido: {profissional_pref}
- Horario preferido: {horario_pref}

SERVICOS DISPONIVEIS:
- Corte Feminino: R$ 80,00 (45 min)
- Coloracao: R$ 150,00 (120 min)
- Escova Simples: R$ 60,00 (45 min)
- Escova Cabelo Longo: R$ 80,00 (60 min)
- Manicure: R$ 50,00 (45 min)
- Pedicure: R$ 60,00 (60 min)
- Luzes: R$ 120,00 (90 min)
- Hidratacao Loreal: R$ 100,00 (60 min)
- Depilacao: R$ 40,00 (30 min)

INSTRUCOES:
1. Seja educada e acolhedora
2. Use o nome do cliente quando apropriado
3. Lembre das preferencias e historico
4. Ofereça recomendacoes personalizadas
5. Respostas concisas (maximo 3 linhas)
6. Use emojis (maximo 2-3)
7. Responda em portugues brasileiro
{historico_text}

Mensagem do cliente: {mensagem}""".format(
            salao=self.salao_name,
            nome=self.marina_name,
            nome_cliente=nome_cliente,
            historico_str=historico_str,
            profissional_pref=profissional_pref,
            horario_pref=horario_pref,
            historico_text=historico_text,
            mensagem=mensagem
        )
        return prompt

    def processar_mensagem_sync(self, mensagem, cliente_info, historico_conversas=None):
        """Processa mensagem de forma síncrona (compatível com Python 3.6+)"""
        try:
            logger.info("Processando mensagem de %s com Gemini", cliente_info.get('nome'))
            prompt = self._construir_prompt(mensagem, cliente_info, historico_conversas)
            response = self.model.generate_content(prompt)
            resposta = response.text
            intencao = self._classificar_intencao(mensagem)
            logger.info("Resposta gerada | Intencao: %s", intencao)
            return resposta, intencao
        except Exception as e:
            logger.error("Erro ao processar mensagem: %s", str(e))
            return "Desculpe, tive um problema ao processar sua mensagem. Pode tentar novamente? 😊", "erro"

    def _classificar_intencao(self, mensagem):
        mensagem_lower = mensagem.lower()
        if any(p in mensagem_lower for p in ["agendar", "marcar", "horario", "hora"]):
            return "agendamento"
        elif any(p in mensagem_lower for p in ["preco", "valor", "custa", "quanto"]):
            return "consulta_preco"
        elif any(p in mensagem_lower for p in ["servico", "servicos", "o que voces fazem"]):
            return "consulta_servicos"
        elif any(p in mensagem_lower for p in ["cancelar", "desmarcar"]):
            return "cancelamento"
        elif any(p in mensagem_lower for p in ["oi", "ola", "opa", "e ai"]):
            return "saudacao"
        else:
            return "consulta_geral"

    def gerar_recomendacao(self, cliente_info):
        """Gera recomendacao personalizada"""
        try:
            historico = cliente_info.get("historico_servicos", [])
            nome = cliente_info.get("nome", "Cliente")
            if not historico:
                return "Que tal comecar com um corte e escova? 💇‍♀️"
            prompt = "Voce e a Marina do salao {}. Gere uma recomendacao breve e amigavel para {}. Historico: {}. Maximo 2 linhas, inclua 1 emoji.".format(
                self.salao_name, nome, ', '.join(historico[-3:])
            )
            response = self.model.generate_content(prompt)
            return response.text
        except Exception as e:
            logger.error("Erro ao gerar recomendacao: %s", str(e))
            return "Que tal agendar um servico conosco? 💇‍♀️"


# Instância global
ai_core = AICoreMariana()
