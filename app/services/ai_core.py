"""
Core de IA da Marina usando Google Gemini via API REST
Compatível com Python 3.6+ sem SDK
"""
import logging
import json
import requests
import os

logger = logging.getLogger(__name__)

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "AIzaSyAjNKdBC4ewfXyyqNDzwcupHzvjvOXZ7WQ")
GEMINI_URL = "https://generativelanguage.googleapis.com/v1/models/gemini-2.0-flash:generateContent?key={}".format(GEMINI_API_KEY)
MARINA_NAME = os.environ.get("MARINA_NAME", "Marina")
MARINA_SALAO = os.environ.get("MARINA_SALAO", "NGHair")


class AICoreMariana:
    """Core de IA para processar mensagens usando Google Gemini REST API"""

    def __init__(self):
        self.marina_name = MARINA_NAME
        self.salao_name = MARINA_SALAO

    def _chamar_gemini(self, prompt):
        """Chama a API do Gemini via HTTP"""
        try:
            payload = {
                "contents": [{"parts": [{"text": prompt}]}],
                "generationConfig": {
                    "temperature": 0.7,
                    "maxOutputTokens": 512
                }
            }
            resp = requests.post(GEMINI_URL, json=payload, timeout=30)
            resp.raise_for_status()
            data = resp.json()
            return data["candidates"][0]["content"]["parts"][0]["text"]
        except Exception as e:
            logger.error("Erro Gemini API: %s", str(e))
            return None

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
                    conv.get("mensagem_usuario", ""),
                    conv.get("resposta_marina", "")
                )

        return """Voce e a {nome}, assistente virtual do salao de beleza {salao}.

PERFIL:
- Tom: profissional, amigavel e acolhedora
- Objetivo: ajudar com agendamentos, servicos e recomendacoes

CLIENTE:
- Nome: {nome_cliente}
- Historico: {historico_str}
- Profissional preferido: {profissional_pref}
- Horario preferido: {horario_pref}

SERVICOS E PRECOS:
- Corte Feminino: R$80 (45min)
- Coloracao: R$150 (120min)
- Escova Simples: R$60 (45min)
- Escova Longa: R$80 (60min)
- Manicure: R$50 (45min)
- Pedicure: R$60 (60min)
- Luzes/Mechas: R$120 (90min)
- Hidratacao: R$100 (60min)
- Depilacao: R$40 (30min)

INSTRUCOES:
1. Responda em portugues brasileiro
2. Seja breve (maximo 3 linhas)
3. Use 1-2 emojis
4. Personalize usando o nome e historico do cliente
{historico_text}

Mensagem: {mensagem}""".format(
            nome=self.marina_name,
            salao=self.salao_name,
            nome_cliente=nome_cliente,
            historico_str=historico_str,
            profissional_pref=profissional_pref,
            horario_pref=horario_pref,
            historico_text=historico_text,
            mensagem=mensagem
        )

    def processar_mensagem_sync(self, mensagem, cliente_info, historico_conversas=None):
        """Processa mensagem de forma sincrona"""
        try:
            prompt = self._construir_prompt(mensagem, cliente_info, historico_conversas)
            resposta = self._chamar_gemini(prompt)
            if not resposta:
                resposta = "Ola! Sou a {}, do {}. Como posso te ajudar hoje? 😊".format(
                    self.marina_name, self.salao_name)
            intencao = self._classificar_intencao(mensagem)
            return resposta, intencao
        except Exception as e:
            logger.error("Erro ao processar: %s", str(e))
            return "Desculpe, tive um problema tecnico. Pode tentar novamente? 😊", "erro"

    def _classificar_intencao(self, mensagem):
        m = mensagem.lower()
        if any(p in m for p in ["agendar", "marcar", "horario", "hora", "disponivel"]):
            return "agendamento"
        elif any(p in m for p in ["preco", "valor", "custa", "quanto"]):
            return "consulta_preco"
        elif any(p in m for p in ["servico", "servicos", "fazem", "oferecem"]):
            return "consulta_servicos"
        elif any(p in m for p in ["cancelar", "desmarcar", "remarcar"]):
            return "cancelamento"
        elif any(p in m for p in ["oi", "ola", "opa", "bom dia", "boa tarde", "boa noite"]):
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
            prompt = "Voce e a {} do {}. Gere uma recomendacao curta (1-2 linhas) para {}. Historico: {}. Use 1 emoji.".format(
                self.marina_name, self.salao_name, nome, ", ".join(historico[-3:]))
            resposta = self._chamar_gemini(prompt)
            return resposta or "Que tal agendar um servico? 💇‍♀️"
        except Exception as e:
            logger.error("Erro recomendacao: %s", str(e))
            return "Que tal agendar um servico conosco? 💇‍♀️"


ai_core = AICoreMariana()
