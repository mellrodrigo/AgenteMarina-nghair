"""
Core de IA da Marina — OpenAI GPT
Usa dados reais de serviços e profissionais sincronizados do Trinks
"""
import logging
import os
import time
from openai import OpenAI, RateLimitError

logger = logging.getLogger(__name__)

OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", "")
OPENAI_MODEL = os.environ.get("OPENAI_MODEL", "gpt-4o-mini")
MARINA_NAME = os.environ.get("MARINA_NAME", "Marina")
MARINA_SALAO = os.environ.get("MARINA_SALAO", "NGHair")

_client = OpenAI(api_key=OPENAI_API_KEY) if OPENAI_API_KEY else None

# Cache dos dados do Trinks (atualizado pelo sync)
_servicos_cache = []
_profissionais_cache = []


class AICoreMariana:

    def __init__(self):
        self.marina_name = MARINA_NAME
        self.salao_name = MARINA_SALAO

    # ── Atualização do contexto Trinks ────────────────────────

    def atualizar_contexto_trinks(self, db):
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
        if _servicos_cache:
            linhas = []
            for s in _servicos_cache:
                preco = "R${:.0f}".format(s["preco"]) if s["preco"] else "consultar"
                duracao = "{}min".format(s["duracao_minutos"]) if s["duracao_minutos"] else ""
                linhas.append("- {}: {} ({})".format(s["nome"], preco, duracao))
            return "\n".join(linhas)
        return (
            "- Corte Feminino: R$80 (45min)\n"
            "- Coloração: R$150 (120min)\n"
            "- Escova: R$60 (45min)\n"
            "- Manicure: R$50 (45min)\n"
            "- Pedicure: R$60 (60min)"
        )

    def _profissionais_para_texto(self):
        if _profissionais_cache:
            return ", ".join(_profissionais_cache)
        return "a equipe do salão"

    # ── Chamada OpenAI ────────────────────────────────────────

    def _chamar_gpt(self, system_prompt, user_message):
        global _client
        if not _client:
            _client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY", ""))

        for attempt in range(3):
            try:
                response = _client.chat.completions.create(
                    model=OPENAI_MODEL,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_message},
                    ],
                    temperature=0.7,
                    max_tokens=512,
                )
                return response.choices[0].message.content
            except RateLimitError:
                wait = 2 ** attempt
                logger.warning("OpenAI 429, aguardando %ds (tentativa %d/3)...", wait, attempt + 1)
                time.sleep(wait)
            except Exception as e:
                logger.error("Erro OpenAI API: %s", str(e))
                if attempt < 2:
                    time.sleep(2 ** attempt)
        return None

    # ── Prompt ────────────────────────────────────────────────

    def _construir_system_prompt(self, cliente_info, historico_conversas=None):
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
            "5. Para agendamentos, peça: serviço, profissional e data/horário preferidos"
            "{historico_text}"
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
        )

    # ── Fallback sem IA ───────────────────────────────────────

    def _resposta_fallback(self, mensagem, cliente_info):
        nome = cliente_info.get("nome", "")
        saudacao = "Olá{}! ".format(", " + nome if nome and nome != "Cliente" else "")
        m = mensagem.lower()

        if any(p in m for p in ["serviço", "serviços", "fazem", "oferecem", "tem"]):
            if _servicos_cache:
                top = _servicos_cache[:10]
                lista = "\n".join("• {}: R${:.0f}".format(s["nome"], s["preco"]) for s in top)
                return "{}Alguns dos nossos serviços 💇‍♀️:\n{}\n\nQuer agendar ou saber mais?".format(saudacao, lista)

        if any(p in m for p in ["preço", "valor", "custa", "quanto"]):
            if _servicos_cache:
                top = _servicos_cache[:8]
                lista = "\n".join("• {}: R${:.0f}".format(s["nome"], s["preco"]) for s in top)
                return "{}Nossos preços 💅:\n{}\n\nPosso agendar para você!".format(saudacao, lista)

        if any(p in m for p in ["agendar", "marcar", "horário", "hora", "vaga", "disponível"]):
            prof = self._profissionais_para_texto()
            return "{}Adoraria agendar para você! ✨ Temos: {}.\nQual serviço e data você prefere?".format(saudacao, prof)

        if any(p in m for p in ["oi", "olá", "opa", "bom dia", "boa tarde", "boa noite"]):
            return "{}Sou a Marina, assistente virtual do {} 💚 Como posso te ajudar hoje?".format(saudacao, self.salao_name)

        return "{}Sou a Marina, do {} 😊 Posso ajudar com serviços, preços e agendamentos. O que você precisa?".format(saudacao, self.salao_name)

    # ── Interface pública ─────────────────────────────────────

    def processar_mensagem_sync(self, mensagem, cliente_info, historico_conversas=None):
        try:
            system_prompt = self._construir_system_prompt(cliente_info, historico_conversas)
            resposta = self._chamar_gpt(system_prompt, mensagem)
            if not resposta:
                resposta = self._resposta_fallback(mensagem, cliente_info)
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
        elif any(p in m for p in ["cancelar", "desmarcar", "remarcar"]):
            return "cancelamento"
        elif any(p in m for p in ["oi", "olá", "opa", "bom dia", "boa tarde", "boa noite"]):
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
                "Gere uma recomendação curta (1-2 linhas) para {}. "
                "Histórico de serviços: {}. Serviços disponíveis: {}. Use 1 emoji."
            ).format(nome, ", ".join(historico[-3:]), self._servicos_para_texto())
            system = "Você é a {} do salão {}, assistente amigável.".format(self.marina_name, self.salao_name)
            return self._chamar_gpt(system, prompt) or "Que tal agendar um serviço? 💇‍♀️"
        except Exception as e:
            logger.error("Erro recomendação: %s", str(e))
            return "Que tal agendar um serviço conosco? 💇‍♀️"


ai_core = AICoreMariana()
