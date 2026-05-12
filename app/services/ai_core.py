"""
Core de IA da Marina — Google Gemini REST API
Usa dados reais de serviços e profissionais sincronizados do Trinks
"""
import logging
import os
import requests

logger = logging.getLogger(__name__)

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")
GEMINI_MODEL = os.environ.get("GEMINI_MODEL", "gemini-2.0-flash")
GEMINI_URL = "https://generativelanguage.googleapis.com/v1/models/{}:generateContent?key={}".format(
    GEMINI_MODEL, GEMINI_API_KEY
)
MARINA_NAME = os.environ.get("MARINA_NAME", "Marina")
MARINA_SALAO = os.environ.get("MARINA_SALAO", "NGHair")

# Cache dos dados do Trinks (atualizado pelo sync)
_servicos_cache = []
_profissionais_cache = []


class AICoreMariana:

    def __init__(self):
        self.marina_name = MARINA_NAME
        self.salao_name = MARINA_SALAO

    # ── Atualização do contexto Trinks ────────────────────────

    def atualizar_contexto_trinks(self, db):
        """Atualiza o cache de serviços e profissionais do banco local"""
        global _servicos_cache, _profissionais_cache
        try:
            from app.models.database import Servico, Profissional
            servicos = db.query(Servico).filter(Servico.ativo == True).all()
            profissionais = db.query(Profissional).filter(Profissional.ativo == True).all()
            _servicos_cache = [
                {"nome": s.nome, "preco": s.preco, "duracao_minutos": s.duracao_minutos}
                for s in servicos
            ]
            _profissionais_cache = [p.nome for p in profissionais]
            logger.info("Cache IA atualizado: %d serviços, %d profissionais",
                        len(_servicos_cache), len(_profissionais_cache))
        except Exception as e:
            logger.error("Erro ao atualizar cache IA: %s", str(e))

    def _servicos_para_texto(self):
        """Formata serviços para o prompt. Usa dados do Trinks se disponíveis."""
        if _servicos_cache:
            linhas = []
            for s in _servicos_cache:
                preco = "R${:.0f}".format(s["preco"]) if s["preco"] else "consultar"
                duracao = "{}min".format(s["duracao_minutos"]) if s["duracao_minutos"] else ""
                linhas.append("- {}: {} ({})".format(s["nome"], preco, duracao))
            return "\n".join(linhas)
        # Fallback com dados padrão se o sync ainda não ocorreu
        return (
            "- Corte Feminino: R$80 (45min)\n"
            "- Coloração: R$150 (120min)\n"
            "- Escova Simples: R$60 (45min)\n"
            "- Escova Longa: R$80 (60min)\n"
            "- Manicure: R$50 (45min)\n"
            "- Pedicure: R$60 (60min)\n"
            "- Luzes/Mechas: R$120 (90min)\n"
            "- Hidratação: R$100 (60min)\n"
            "- Depilação: R$40 (30min)"
        )

    def _profissionais_para_texto(self):
        """Lista profissionais disponíveis"""
        if _profissionais_cache:
            return ", ".join(_profissionais_cache)
        return "a equipe do salão"

    # ── Chamada Gemini ────────────────────────────────────────

    def _chamar_gemini(self, prompt):
        try:
            payload = {
                "contents": [{"parts": [{"text": prompt}]}],
                "generationConfig": {"temperature": 0.7, "maxOutputTokens": 512}
            }
            resp = requests.post(GEMINI_URL, json=payload, timeout=30)
            resp.raise_for_status()
            return resp.json()["candidates"][0]["content"]["parts"][0]["text"]
        except Exception as e:
            logger.error("Erro Gemini API: %s", str(e))
            return None

    # ── Prompt ────────────────────────────────────────────────

    def _construir_prompt(self, mensagem, cliente_info, historico_conversas=None):
        nome_cliente = cliente_info.get("nome", "Cliente")
        historico_servicos = cliente_info.get("historico_servicos", [])
        preferencias = cliente_info.get("preferencias", {})

        historico_str = ", ".join(historico_servicos[-5:]) if historico_servicos else "nenhum"
        profissional_pref = preferencias.get("profissional_preferido", "qualquer")
        horario_pref = preferencias.get("horario_preferido", "qualquer")

        historico_text = ""
        if historico_conversas:
            historico_text = "\nHistórico recente:\n"
            for conv in historico_conversas[-3:]:
                historico_text += "Cliente: {}\nMarina: {}\n".format(
                    conv.get("mensagem_usuario", ""),
                    conv.get("resposta_marina", "")
                )

        return (
            "Você é a {nome}, assistente virtual do salão {salao}.\n\n"
            "PERFIL:\n"
            "- Tom: profissional, amigável e acolhedora\n"
            "- Objetivo: ajudar com agendamentos, serviços e recomendações\n\n"
            "CLIENTE:\n"
            "- Nome: {nome_cliente}\n"
            "- Histórico de serviços: {historico_str}\n"
            "- Profissional preferido: {profissional_pref}\n"
            "- Horário preferido: {horario_pref}\n\n"
            "SERVIÇOS E PREÇOS (atualizados do sistema):\n"
            "{servicos}\n\n"
            "PROFISSIONAIS DISPONÍVEIS:\n"
            "{profissionais}\n\n"
            "INSTRUÇÕES:\n"
            "1. Responda em português brasileiro\n"
            "2. Seja breve (máximo 3 linhas)\n"
            "3. Use 1-2 emojis\n"
            "4. Personalize usando nome e histórico do cliente\n"
            "5. Para agendamentos, peça: serviço, profissional e data/horário preferidos\n"
            "{historico_text}\n"
            "Mensagem do cliente: {mensagem}"
        ).format(
            nome=self.marina_name,
            salao=self.salao_name,
            nome_cliente=nome_cliente,
            historico_str=historico_str,
            profissional_pref=profissional_pref,
            horario_pref=horario_pref,
            servicos=self._servicos_para_texto(),
            profissionais=self._profissionais_para_texto(),
            historico_text=historico_text,
            mensagem=mensagem
        )

    # ── Interface pública ─────────────────────────────────────

    def processar_mensagem_sync(self, mensagem, cliente_info, historico_conversas=None):
        try:
            prompt = self._construir_prompt(mensagem, cliente_info, historico_conversas)
            resposta = self._chamar_gemini(prompt)
            if not resposta:
                resposta = "Olá! Sou a {}, do {}. Como posso te ajudar hoje? 😊".format(
                    self.marina_name, self.salao_name)
            intencao = self._classificar_intencao(mensagem)
            return resposta, intencao
        except Exception as e:
            logger.error("Erro ao processar: %s", str(e))
            return "Desculpe, tive um problema técnico. Pode tentar novamente? 😊", "erro"

    def _classificar_intencao(self, mensagem):
        m = mensagem.lower()
        if any(p in m for p in ["agendar", "marcar", "horário", "hora", "disponível", "vaga"]):
            return "agendamento"
        elif any(p in m for p in ["preço", "valor", "custa", "quanto"]):
            return "consulta_preco"
        elif any(p in m for p in ["serviço", "serviços", "fazem", "oferecem"]):
            return "consulta_servicos"
        elif any(p in m for p in ["cancelar", "desmarcar", "remarcar", "cancelamento"]):
            return "cancelamento"
        elif any(p in m for p in ["oi", "olá", "opa", "bom dia", "boa tarde", "boa noite", "tudo bem"]):
            return "saudacao"
        else:
            return "consulta_geral"

    def gerar_recomendacao(self, cliente_info):
        try:
            historico = cliente_info.get("historico_servicos", [])
            nome = cliente_info.get("nome", "Cliente")
            if not historico:
                return "Que tal começar com um corte e escova? 💇‍♀️"
            prompt = (
                "Você é a {} do {}. Gere uma recomendação curta (1-2 linhas) para {}. "
                "Histórico de serviços: {}. Serviços disponíveis: {}. Use 1 emoji."
            ).format(
                self.marina_name, self.salao_name, nome,
                ", ".join(historico[-3:]),
                self._servicos_para_texto()
            )
            return self._chamar_gemini(prompt) or "Que tal agendar um serviço? 💇‍♀️"
        except Exception as e:
            logger.error("Erro recomendação: %s", str(e))
            return "Que tal agendar um serviço conosco? 💇‍♀️"


ai_core = AICoreMariana()
