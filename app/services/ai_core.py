"""
Core de IA da Marina — OpenAI GPT com function calling para agendamentos Trinks
"""
import json
import logging
import os
import time
from datetime import datetime
from openai import OpenAI, RateLimitError

logger = logging.getLogger(__name__)

OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", "")
OPENAI_MODEL = os.environ.get("OPENAI_MODEL", "gpt-4o-mini")
MARINA_NAME = os.environ.get("MARINA_NAME", "Marina")
MARINA_SALAO = os.environ.get("MARINA_SALAO", "NGHair")

_client = OpenAI(api_key=OPENAI_API_KEY) if OPENAI_API_KEY else None

_servicos_cache = []     # [{id_local, nome, preco, duracao_minutos}]
_profissionais_cache = []  # [nome]

# ── Ferramentas (function calling) ───────────────────────────

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "salvar_dados_cliente",
            "description": (
                "Salva ou atualiza dados do cliente no sistema. "
                "Use assim que o cliente informar o nome, profissional preferido ou horário preferido."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "nome": {
                        "type": "string",
                        "description": "Nome completo do cliente"
                    },
                    "profissional_preferido": {
                        "type": "string",
                        "description": "Nome do profissional preferido"
                    },
                    "servico_preferido": {
                        "type": "string",
                        "description": "Serviço que o cliente costuma fazer"
                    },
                    "horario_preferido": {
                        "type": "string",
                        "description": "Horário preferido (ex: manhã, tarde, 14h)"
                    }
                },
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "verificar_disponibilidade",
            "description": (
                "Verifica horários disponíveis no Trinks para agendamento. "
                "Use quando o cliente pedir horários ou quiser saber quando pode vir."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "data": {
                        "type": "string",
                        "description": "Data no formato YYYY-MM-DD (ex: 2024-06-15)"
                    },
                    "servico_nome": {
                        "type": "string",
                        "description": "Nome do serviço desejado (ex: Corte Feminino)"
                    },
                    "profissional_nome": {
                        "type": "string",
                        "description": "Nome do profissional preferido (opcional)"
                    }
                },
                "required": ["data"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "criar_agendamento",
            "description": (
                "Cria o agendamento real no sistema Trinks. "
                "Use SOMENTE quando o cliente já confirmou: nome completo, serviço, data e horário. "
                "Pergunte TODOS os dados antes de chamar esta função, inclusive o nome completo do cliente."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "cliente_nome": {
                        "type": "string",
                        "description": "Nome completo do cliente (obrigatório, pergunte antes de agendar)"
                    },
                    "servico_nome": {
                        "type": "string",
                        "description": "Nome exato do serviço (ex: Corte Feminino)"
                    },
                    "profissional_nome": {
                        "type": "string",
                        "description": "Nome do profissional (deixe vazio se não tiver preferência)"
                    },
                    "data_hora": {
                        "type": "string",
                        "description": "Data e hora no formato YYYY-MM-DD HH:MM (ex: 2024-06-15 10:00)"
                    }
                },
                "required": ["cliente_nome", "servico_nome", "data_hora"]
            }
        }
    }
]


class AICoreMariana:

    def __init__(self):
        self.marina_name = MARINA_NAME
        self.salao_name = MARINA_SALAO

    # ── Transcrição de áudio ──────────────────────────────────

    def transcrever_audio(self, audio_bytes: bytes, mimetype: str = "audio/ogg") -> str:
        """Transcreve áudio WhatsApp para texto usando OpenAI Whisper."""
        import tempfile, os
        global _client
        if not _client:
            _client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY", ""))

        ext = "ogg"
        if "mp4" in mimetype or "mp4a" in mimetype:
            ext = "mp4"
        elif "mpeg" in mimetype or "mp3" in mimetype:
            ext = "mp3"
        elif "webm" in mimetype:
            ext = "webm"

        try:
            with tempfile.NamedTemporaryFile(suffix=".{}".format(ext), delete=False) as tmp:
                tmp.write(audio_bytes)
                tmp_path = tmp.name

            with open(tmp_path, "rb") as f:
                result = _client.audio.transcriptions.create(
                    model="whisper-1",
                    file=f,
                    language="pt",
                )
            os.unlink(tmp_path)
            texto = result.text.strip()
            logger.info("Whisper transcrição: %s", texto[:100])
            return texto
        except Exception as e:
            logger.error("Erro Whisper: %s", str(e))
            try:
                os.unlink(tmp_path)
            except Exception:
                pass
            return ""

    # ── Cache Trinks ──────────────────────────────────────────

    def atualizar_contexto_trinks(self, db):
        global _servicos_cache, _profissionais_cache
        try:
            from app.models.database import Servico, Profissional
            servicos = db.query(Servico).filter(Servico.ativo == True).all()
            profissionais = db.query(Profissional).filter(Profissional.ativo == True).all()
            _servicos_cache = [
                {"id": s.id, "nome": s.nome, "preco": s.preco, "duracao_minutos": s.duracao_minutos}
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
            for s in _servicos_cache[:30]:
                preco = "R${:.0f}".format(s["preco"]) if s["preco"] else "consultar"
                duracao = "{}min".format(s["duracao_minutos"]) if s["duracao_minutos"] else ""
                linhas.append("- {}: {} ({})".format(s["nome"], preco, duracao))
            return "\n".join(linhas)
        return "- Corte Feminino: R$80 (45min)\n- Coloração: R$150 (120min)\n- Escova: R$60 (45min)"

    def _profissionais_para_texto(self):
        if _profissionais_cache:
            return ", ".join(_profissionais_cache)
        return "a equipe do salão"

    # ── OpenAI ────────────────────────────────────────────────

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

    def _chamar_gpt_com_tools(self, messages, db, telefone, cliente_info):
        """Chama GPT com function calling; executa tools e retorna resposta final."""
        global _client
        if not _client:
            _client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY", ""))

        for attempt in range(3):
            try:
                response = _client.chat.completions.create(
                    model=OPENAI_MODEL,
                    messages=messages,
                    tools=TOOLS,
                    tool_choice="auto",
                    temperature=0.7,
                    max_tokens=512,
                )
                msg = response.choices[0].message

                if not msg.tool_calls:
                    return msg.content

                # Executa cada tool call
                messages = list(messages) + [msg]
                for tc in msg.tool_calls:
                    args = json.loads(tc.function.arguments)
                    resultado = self._executar_tool(tc.function.name, args, db, telefone, cliente_info)
                    messages.append({
                        "role": "tool",
                        "tool_call_id": tc.id,
                        "content": json.dumps(resultado, ensure_ascii=False),
                    })

                # Resposta final após tools
                final = _client.chat.completions.create(
                    model=OPENAI_MODEL,
                    messages=messages,
                    temperature=0.7,
                    max_tokens=512,
                )
                return final.choices[0].message.content

            except RateLimitError:
                wait = 2 ** attempt
                logger.warning("OpenAI 429, aguardando %ds...", wait)
                time.sleep(wait)
            except Exception as e:
                logger.error("Erro OpenAI tools: %s", str(e))
                if attempt < 2:
                    time.sleep(2 ** attempt)
        return None

    # ── Execução das tools ────────────────────────────────────

    def _executar_tool(self, nome, args, db, telefone, cliente_info):
        if nome == "salvar_dados_cliente":
            return self._tool_salvar_dados_cliente(args, db, cliente_info)
        elif nome == "verificar_disponibilidade":
            return self._tool_disponibilidade(args)
        elif nome == "criar_agendamento":
            return self._tool_criar_agendamento(args, telefone, cliente_info)
        return {"erro": "Ferramenta desconhecida: {}".format(nome)}

    def _tool_salvar_dados_cliente(self, args, db, cliente_info):
        from app.services.cliente_service import cliente_service
        cliente_id = cliente_info.get("id")
        if not cliente_id:
            return {"erro": "Cliente não identificado"}
        campos = {k: v for k, v in args.items() if v}
        ok = cliente_service.atualizar_cliente(db, cliente_id, **campos)
        if ok:
            if "nome" in campos:
                cliente_info["nome"] = campos["nome"]
                cliente_info["nome_conhecido"] = True
            return {"sucesso": True, "dados_salvos": campos}
        return {"erro": "Não foi possível salvar os dados"}

    def _tool_disponibilidade(self, args):
        from app.services.trinks_api import trinks_api
        data = args.get("data", "")
        servico_nome = args.get("servico_nome", "")
        profissional_nome = args.get("profissional_nome", "")

        # Busca IDs reais no Trinks
        servico_id = None
        profissional_id = None

        if servico_nome or profissional_nome:
            try:
                if servico_nome:
                    servicos = trinks_api.listar_servicos()
                    for s in servicos:
                        if servico_nome.lower() in s["nome"].lower():
                            servico_id = s["id"]
                            break

                if profissional_nome:
                    profissionais = trinks_api.listar_profissionais()
                    for p in profissionais:
                        if profissional_nome.lower() in p["nome"].lower():
                            profissional_id = p["id"]
                            break
            except Exception as e:
                logger.error("Erro buscando IDs Trinks: %s", str(e))

        horarios = trinks_api.horarios_disponiveis(data, servico_id, profissional_id)

        if horarios:
            return {
                "disponivel": True,
                "data": data,
                "horarios_disponiveis": horarios[:8],
                "profissional": profissional_nome or "qualquer profissional",
                "servico": servico_nome,
            }
        return {
            "disponivel": False,
            "data": data,
            "mensagem": "Sem horários disponíveis para esta data. Tente outra data.",
        }

    def _tool_criar_agendamento(self, args, telefone, cliente_info):
        from app.services.trinks_api import trinks_api
        from app.services.evolution_api import evolution_api_client
        from config import TRINKS_ESTABELECIMENTO_ID, WHATSAPP_INSTANCE_NAME

        def _debug(msg):
            """Envia mensagem de status no WhatsApp durante o fluxo (modo dev)."""
            logger.info("[DEBUG-AGENDAMENTO] %s", msg)
            try:
                evolution_api_client.enviar_mensagem(
                    instance=WHATSAPP_INSTANCE_NAME,
                    numero=telefone,
                    mensagem="🔧 *[DEV]* " + msg,
                )
            except Exception:
                pass

        servico_nome = args.get("servico_nome", "")
        profissional_nome = args.get("profissional_nome", "")
        data_hora = args.get("data_hora", "")

        # 1. Valida data/hora
        try:
            dt = datetime.strptime(data_hora, "%Y-%m-%d %H:%M")
            data_hora_iso = dt.isoformat()
        except ValueError:
            return {"erro": "Formato de data/hora inválido. Use YYYY-MM-DD HH:MM"}

        # 2. Busca serviço
        servico_id = None
        duracao_minutos = 60
        try:
            servicos = trinks_api.listar_servicos()
            for s in servicos:
                if servico_nome.lower() in s["nome"].lower():
                    servico_id = s["id"]
                    servico_nome = s["nome"]
                    duracao_minutos = int(s.get("duracao_minutos") or 60)
                    break
        except Exception as e:
            logger.error("Erro buscando serviço: %s", str(e))

        if not servico_id:
            _debug("❌ Serviço não encontrado: '{}'".format(servico_nome))
            return {"erro": "Serviço '{}' não encontrado no sistema.".format(servico_nome)}
        _debug("✅ Serviço: {} | id={} | duração={}min".format(servico_nome, servico_id, duracao_minutos))

        # 3. Busca profissional
        profissional_id = None
        try:
            if profissional_nome:
                profissionais = trinks_api.listar_profissionais()
                for p in profissionais:
                    if profissional_nome.lower() in p["nome"].lower():
                        profissional_id = p["id"]
                        profissional_nome = p["nome"]
                        break
        except Exception as e:
            logger.error("Erro buscando profissional: %s", str(e))

        if profissional_nome and not profissional_id:
            _debug("⚠️ Profissional '{}' não encontrado — agendando sem profissional fixo".format(profissional_nome))
        elif profissional_id:
            _debug("✅ Profissional: {} | id={}".format(profissional_nome, profissional_id))

        # 4. Verifica conflito de horário
        data_apenas = dt.strftime("%Y-%m-%d")
        hora_desejada = dt.strftime("%H:%M")
        try:
            agendamentos_dia = trinks_api.listar_agendamentos(data_inicio=data_apenas, data_fim=data_apenas)
            conflitos = []
            for ag in agendamentos_dia:
                if profissional_id and ag.get("profissional_id") != profissional_id:
                    continue
                ag_hora = ag.get("data_hora", "")
                if ag_hora and hora_desejada in ag_hora:
                    conflitos.append(ag)

            if conflitos:
                c = conflitos[0]
                _debug("⚠️ Conflito: {} já tem agendamento às {} com {} (id={})".format(
                    profissional_nome or "profissional", hora_desejada,
                    c.get("cliente", "?"), c.get("id", "?")))
                return {
                    "erro": "Já existe um agendamento às {} para {}. Escolha outro horário.".format(
                        hora_desejada, profissional_nome or "esse profissional")
                }
            _debug("✅ Horário {} livre em {}".format(hora_desejada, data_apenas))
        except Exception as e:
            logger.warning("Erro ao verificar conflitos: %s", str(e))
            _debug("⚠️ Não foi possível verificar conflitos — prosseguindo")

        # 5. Busca ou cria cliente no Trinks
        nome_cliente = args.get("cliente_nome") or cliente_info.get("nome", "")
        if not nome_cliente or nome_cliente.strip().lower() in ("cliente", ""):
            return {"erro": "Preciso do nome completo do cliente para criar o agendamento."}

        tel_cliente = telefone or ""
        cliente_id = None
        try:
            cliente_id = trinks_api.buscar_ou_criar_cliente(nome_cliente, tel_cliente)
        except Exception as e:
            logger.warning("Erro ao buscar/criar cliente Trinks: %s", str(e))

        if not cliente_id:
            _debug("❌ Não foi possível registrar cliente '{}' no Trinks".format(nome_cliente))
            return {"erro": "Não foi possível registrar o cliente no sistema."}
        _debug("✅ Cliente: {} | id={}".format(nome_cliente, cliente_id))

        # 6. Cria agendamento
        payload = {
            "estabelecimentoId": int(TRINKS_ESTABELECIMENTO_ID),
            "clienteId": cliente_id,
            "dataHora": data_hora_iso,
            "servicos": [{"servicoId": servico_id, "duracaoEmMinutos": duracao_minutos}],
            "observacao": "",
        }
        if profissional_id:
            payload["profissionalId"] = profissional_id

        logger.info("Criando agendamento Trinks: %s", payload)
        _debug("📤 Enviando agendamento: clienteId={} | servicoId={} | dataHora={}".format(
            cliente_id, servico_id, data_hora_iso))

        resultado = trinks_api.criar_agendamento(payload)

        if resultado:
            ag_id = resultado.get("id", "")
            _debug("✅ Agendamento criado! id={}".format(ag_id))
            return {
                "sucesso": True,
                "agendamento_id": ag_id,
                "servico": servico_nome,
                "profissional": profissional_nome or "a definir pelo salão",
                "data_hora": data_hora,
                "cliente": nome_cliente,
                "mensagem": "Agendamento criado com sucesso no sistema!",
            }

        _debug("❌ Falha ao criar agendamento — veja os logs do servidor")
        return {"erro": "Falha ao criar agendamento no Trinks. Tente novamente ou ligue para o salão."}

    # ── Prompt ────────────────────────────────────────────────

    def _construir_system_prompt(self, cliente_info, historico_conversas=None):
        nome_cliente = cliente_info.get("nome", "Cliente")
        nome_conhecido = cliente_info.get("nome_conhecido", False)
        is_primeira_vez = cliente_info.get("is_primeira_vez", False)
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

        data_hoje = datetime.now().strftime("%d/%m/%Y")

        if is_primeira_vez:
            saudacao_instrucao = (
                "PRIMEIRA CONVERSA: apresente-se brevemente e pergunte o nome do cliente. "
                "Assim que ele informar, use salvar_dados_cliente para salvar."
            )
        elif nome_conhecido:
            saudacao_instrucao = (
                "CLIENTE CONHECIDO: use o nome '{}' para cumprimentar e personalizar todas as respostas."
            ).format(nome_cliente)
        else:
            saudacao_instrucao = (
                "NOME DESCONHECIDO: pergunte o nome do cliente na primeira oportunidade natural e salve com salvar_dados_cliente."
            )

        return (
            "Você é a {nome}, assistente virtual do salão {salao}. Hoje é {data_hoje}.\n\n"
            "PERFIL:\n"
            "- Tom: profissional, amigável e acolhedora\n"
            "- Objetivo: ajudar com agendamentos reais via sistema, serviços e recomendações\n\n"
            "CLIENTE:\n"
            "- Nome: {nome_cliente}\n"
            "- Histórico de serviços: {historico_str}\n"
            "- Profissional preferido: {profissional_pref}\n"
            "- Horário preferido: {horario_pref}\n\n"
            "SAUDAÇÃO: {saudacao_instrucao}\n\n"
            "SERVIÇOS E PREÇOS (atualizados do sistema):\n"
            "{servicos}\n\n"
            "PROFISSIONAIS DISPONÍVEIS:\n"
            "{profissionais}\n\n"
            "INSTRUÇÕES:\n"
            "1. Responda em português brasileiro\n"
            "2. Seja breve (máximo 3 linhas por mensagem)\n"
            "3. Use 1-2 emojis\n"
            "4. Sempre use o nome do cliente quando conhecido\n"
            "5. Para agendar: (1) pergunte serviço desejado e data preferida, "
            "(2) use verificar_disponibilidade para mostrar horários reais, "
            "(3) confirme serviço + data + horário com o cliente, "
            "(4) use criar_agendamento para registrar no sistema\n"
            "6. Após criar agendamento com sucesso, confirme os detalhes para o cliente"
            "{historico_text}"
        ).format(
            nome=self.marina_name,
            salao=self.salao_name,
            data_hoje=data_hoje,
            nome_cliente=nome_cliente,
            historico_str=historico_str,
            profissional_pref=profissional_pref,
            horario_pref=horario_pref,
            saudacao_instrucao=saudacao_instrucao,
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

    def processar_mensagem_sync(self, mensagem, cliente_info, historico_conversas=None,
                                 db=None, telefone=None):
        try:
            system_prompt = self._construir_system_prompt(cliente_info, historico_conversas)
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": mensagem},
            ]

            resposta = self._chamar_gpt_com_tools(messages, db, telefone, cliente_info)

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
