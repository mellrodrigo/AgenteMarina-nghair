"""
Core de IA da Marina — OpenAI GPT com function calling para agendamentos Trinks
"""
import json
import logging
import os
import time
from datetime import datetime
from zoneinfo import ZoneInfo
from openai import OpenAI, RateLimitError

logger = logging.getLogger(__name__)

TZ_SP = ZoneInfo("America/Sao_Paulo")

def _agora_sp():
    """Retorna datetime atual no fuso de São Paulo."""
    return datetime.now(TZ_SP)

OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", "")
OPENAI_MODEL = os.environ.get("OPENAI_MODEL", "gpt-4o-mini")
MARINA_NAME = os.environ.get("MARINA_NAME", "Marina")
MARINA_SALAO = os.environ.get("MARINA_SALAO", "NGHair")

_client = OpenAI(api_key=OPENAI_API_KEY) if OPENAI_API_KEY else None

_servicos_cache = []     # [{id_local, nome, preco, duracao_minutos}]
_profissionais_cache = []  # [nome]

# ── Ferramentas (function calling) ──────────────────────────────

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
                    "nome": {"type": "string", "description": "Nome completo do cliente"},
                    "profissional_preferido": {"type": "string", "description": "Nome do profissional preferido"},
                    "servico_preferido": {"type": "string", "description": "Serviço que o cliente costuma fazer"},
                    "horario_preferido": {"type": "string", "description": "Horário preferido (ex: manhã, tarde, 14h)"},
                    "sexo": {"type": "string", "enum": ["M", "F"], "description": "Sexo do cliente: M ou F"},
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
                "Verifica horários disponíveis no Trinks. "
                "Use SOMENTE quando o cliente NÃO souber o horário e pedir sugestões (ex: 'que horas tem?', 'qual horário disponível?'). "
                "NÃO use quando o cliente já informou um horário específico — vá direto para criar_agendamento."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "data": {"type": "string", "description": "Data no formato YYYY-MM-DD (ex: 2024-06-15)"},
                    "servico_nome": {"type": "string", "description": "Nome do serviço desejado"},
                    "profissional_nome": {"type": "string", "description": "Nome do profissional preferido (opcional)"},
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
                "Pergunte TODOS os dados antes de chamar, inclusive o nome completo do cliente."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "cliente_nome": {"type": "string", "description": "Nome completo do cliente (obrigatório)"},
                    "servico_nome": {"type": "string", "description": "Nome exato do serviço (ex: Corte Feminino)"},
                    "profissional_nome": {"type": "string", "description": "Nome do profissional"},
                    "data_hora": {"type": "string", "description": "Data e hora no formato YYYY-MM-DD HH:MM"},
                    "cliente_trinks_id": {"type": "integer", "description": "ID do cliente no Trinks (após seleção múltipla)"},
                },
                "required": ["cliente_nome", "servico_nome", "profissional_nome", "data_hora"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "listar_agendamentos_cliente",
            "description": (
                "Lista os agendamentos futuros do cliente no Trinks. "
                "Use quando o cliente quiser ver seus agendamentos ou quando precisar cancelar e o ID não estiver no histórico da conversa."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "cliente_nome": {"type": "string", "description": "Nome do cliente para buscar no Trinks"},
                },
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "cancelar_agendamento",
            "description": (
                "Cancela um agendamento existente no Trinks pelo ID real do agendamento. "
                "Use SOMENTE após o cliente confirmar. "
                "IMPORTANTE: agendamento_id é o campo 'id' retornado por listar_agendamentos_cliente — NUNCA use o número de ordem da lista (1, 2, 3)."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "agendamento_id": {"type": "integer", "description": "ID real do agendamento no Trinks (campo 'id', ex: 496402642) — NÃO é o índice da lista"},
                    "motivo": {"type": "string", "description": "Motivo do cancelamento (opcional)"},
                },
                "required": ["agendamento_id"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "validar_dados_cliente",
            "description": (
                "Busca os dados cadastrais do cliente no Trinks (nome, telefone, email, CPF, gênero) "
                "e os apresenta para confirmação antes de criar um agendamento. "
                "Chame SEMPRE antes de criar_agendamento."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "cliente_nome": {"type": "string", "description": "Nome do cliente para buscar no Trinks"},
                },
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "atualizar_dados_cliente",
            "description": (
                "Atualiza os dados cadastrais do cliente no Trinks via PUT. "
                "Use quando o cliente informar que algum dado está incorreto."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "nome": {"type": "string", "description": "Nome completo"},
                    "email": {"type": "string", "description": "E-mail"},
                    "cpf": {"type": "string", "description": "CPF (somente números)"},
                    "genero": {"type": "string", "description": "Gênero: Masculino ou Feminino"},
                },
                "required": []
            }
        }
    },
]


class AICoreMariana:

    def __init__(self):
        self.marina_name = MARINA_NAME
        self.salao_name = MARINA_SALAO

    # ── Transcrição de áudio ──────────────────────────────

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

    # ── Cache Trinks ─────────────────────────────────────────

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
            linhas = ["- {}".format(s["nome"]) for s in _servicos_cache[:30]]
            return "\n".join(linhas)
        return "- Corte Feminino\n- Corte Masculino\n- Coloração\n- Escova\n- Manicure\n- Pedicure"

    def _servico_preco(self, nome_servico):
        """Retorna preço de um serviço específico."""
        nome_lower = nome_servico.lower()
        for s in _servicos_cache:
            if nome_lower in s["nome"].lower():
                return "R${:.0f}".format(s["preco"]) if s["preco"] else "consultar"
        return "consultar"

    def _profissionais_para_texto(self):
        if _profissionais_cache:
            return ", ".join(_profissionais_cache)
        return "a equipe do salão"

    # ── OpenAI ──────────────────────────────────────────

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
        """Chama GPT com function calling; executa tools em loop até resposta final."""
        global _client
        if not _client:
            _client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY", ""))

        messages = list(messages)
        max_rodadas = 6  # evita loop infinito

        for rodada in range(max_rodadas):
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
                    break
                except RateLimitError:
                    wait = 2 ** attempt
                    logger.warning("OpenAI 429, aguardando %ds...", wait)
                    time.sleep(wait)
                except Exception as e:
                    logger.error("Erro OpenAI tools: %s", str(e))
                    if attempt < 2:
                        time.sleep(2 ** attempt)
                    else:
                        return None
            else:
                return None

            msg = response.choices[0].message

            if not msg.tool_calls:
                return msg.content

            messages.append(msg)
            for tc in msg.tool_calls:
                try:
                    args = json.loads(tc.function.arguments)
                except Exception:
                    args = {}
                resultado = self._executar_tool(tc.function.name, args, db, telefone, cliente_info)
                messages.append({
                    "role": "tool",
                    "tool_call_id": tc.id,
                    "content": json.dumps(resultado, ensure_ascii=False),
                })

        logger.warning("_chamar_gpt_com_tools: máximo de rodadas atingido")
        return None

    # ── Execução das tools ────────────────────────────────────

    def _executar_tool(self, nome, args, db, telefone, cliente_info):
        if nome == "salvar_dados_cliente":
            return self._tool_salvar_dados_cliente(args, db, cliente_info)
        elif nome == "verificar_disponibilidade":
            return self._tool_disponibilidade(args)
        elif nome == "criar_agendamento":
            return self._tool_criar_agendamento(args, telefone, cliente_info)
        elif nome == "listar_agendamentos_cliente":
            return self._tool_listar_agendamentos_cliente(args, telefone, cliente_info)
        elif nome == "cancelar_agendamento":
            return self._tool_cancelar_agendamento(args, telefone)
        elif nome == "validar_dados_cliente":
            return self._tool_validar_dados_cliente(args, telefone, cliente_info)
        elif nome == "atualizar_dados_cliente":
            return self._tool_atualizar_dados_cliente(args, telefone, cliente_info)
        return {"erro": "Ferramenta desconhecida: {}".format(nome)}

    def _tool_validar_dados_cliente(self, args, telefone, cliente_info):
        from app.services.trinks_api import trinks_api
        nome_cliente = args.get("cliente_nome") or cliente_info.get("nome", "")
        tel_cliente = telefone or ""

        cliente_id = None
        cliente_trinks = None
        try:
            candidatos = trinks_api.buscar_candidatos_cliente(nome_cliente, tel_cliente)
            if candidatos:
                cliente_id = candidatos[0].get("id")
                cliente_info["_trinks_id"] = cliente_id
                # Busca por ID para obter dados completos incluindo telefone
                cliente_trinks = trinks_api.buscar_cliente_por_id(cliente_id) or candidatos[0]
        except Exception as e:
            logger.warning("Erro ao buscar cliente para validação: %s", str(e))

        if not cliente_trinks:
            return {"erro": "Não foi possível localizar o cadastro do cliente no Trinks."}

        # Propaga sexo/gênero para cliente_info para que o system prompt saiba
        sexo_trinks = cliente_trinks.get("sexo") or cliente_trinks.get("genero", "")
        if sexo_trinks and not cliente_info.get("sexo"):
            cliente_info["sexo"] = sexo_trinks

        def _fmt_tel(obj):
            # API retorna telefone como lista de strings: ["11976820026"]
            fones = obj.get("telefone", [])
            if not fones:
                return "não informado"
            num = fones[0]  # ex: "11976820026"
            digits = "".join(filter(str.isdigit, num))
            if len(digits) >= 10:
                ddd = digits[:2]
                resto = digits[2:]
                return "({}) {}-{}".format(ddd, resto[:5], resto[5:])
            return num

        def _fmt_genero(g):
            return {"M": "Masculino", "F": "Feminino"}.get(g, g or "não informado")

        tel_fmt = _fmt_tel(cliente_trinks)
        genero_fmt = _fmt_genero(cliente_trinks.get("genero") or cliente_trinks.get("sexo", ""))

        return {
            "cliente_id": cliente_id,
            "nome": cliente_trinks.get("nome", ""),
            "email": cliente_trinks.get("email", "") or "não informado",
            "cpf": cliente_trinks.get("cpf", "") or "não informado",
            "genero": genero_fmt,
            "telefone": tel_fmt,
            "mensagem": (
                "Seus dados cadastrados 📋:\n"
                "• Nome: {}\n• Telefone: {}\n• E-mail: {}\n• CPF: {}\n• Gênero: {}\n\n"
                "Deseja atualizar alguma informação?"
            ).format(
                cliente_trinks.get("nome", ""),
                tel_fmt,
                cliente_trinks.get("email", "") or "não informado",
                cliente_trinks.get("cpf", "") or "não informado",
                genero_fmt,
            ),
        }

    def _tool_atualizar_dados_cliente(self, args, telefone, cliente_info):
        from app.services.trinks_api import trinks_api
        from datetime import datetime

        cliente_id = cliente_info.get("_trinks_id")
        if not cliente_id:
            nome_cliente = cliente_info.get("nome", "")
            try:
                candidatos = trinks_api.buscar_candidatos_cliente(nome_cliente, telefone or "")
                if candidatos:
                    cliente_id = candidatos[0].get("id")
                    cliente_info["_trinks_id"] = cliente_id
            except Exception as e:
                logger.warning("Erro ao buscar cliente para atualização: %s", str(e))

        if not cliente_id:
            return {"erro": "Não foi possível localizar o cliente para atualização."}

        agora = _agora_sp().strftime("%Y-%m-%d %H:%M")
        payload = {"observacoes": "Data de atualização: {}".format(agora)}
        if args.get("nome"):
            payload["nome"] = args["nome"]
        if args.get("email"):
            payload["email"] = args["email"]
        if args.get("cpf"):
            payload["cpf"] = "".join(filter(str.isdigit, args["cpf"]))
        if args.get("genero"):
            payload["genero"] = args["genero"]

        ok = trinks_api.atualizar_cliente(cliente_id, payload)
        if ok:
            campos = [k for k in ("nome", "email", "cpf", "genero") if k in payload]
            return {
                "sucesso": True,
                "campos_atualizados": campos,
                "data_atualizacao": agora,
                "mensagem": "Cadastro atualizado com sucesso em {}!".format(agora),
            }
        return {"erro": "Não foi possível atualizar o cadastro. Tente novamente."}

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
        from config import WHATSAPP_INSTANCE_NAME

        def _debug(msg):
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

        # 2. Busca serviço — ajusta corte pelo sexo do cliente
        sexo = cliente_info.get("sexo", "")
        palavras_corte = ["corte", "cabelo"]
        eh_corte = any(p in servico_nome.lower() for p in palavras_corte)
        if eh_corte and sexo == "M" and "masculino" not in servico_nome.lower() and "feminino" not in servico_nome.lower():
            servico_nome = "Corte Masculino"
        elif eh_corte and sexo == "F" and "feminino" not in servico_nome.lower() and "masculino" not in servico_nome.lower():
            servico_nome = "Corte Feminino"

        servico_id = None
        duracao_minutos = 60
        valor_servico = 0.0
        try:
            servicos = trinks_api.listar_servicos()
            for s in servicos:
                if servico_nome.lower() in s["nome"].lower():
                    servico_id = s["id"]
                    servico_nome = s["nome"]
                    duracao_minutos = int(s.get("duracao_minutos") or 60)
                    valor_servico = float(s.get("preco") or 0)
                    break
        except Exception as e:
            logger.error("Erro buscando serviço: %s", str(e))

        if not servico_id:
            _debug("❌ Serviço não encontrado: '{}'".format(servico_nome))
            return {"erro": "Serviço '{}' não encontrado no sistema.".format(servico_nome)}

        _debug("✅ Serviço: {} | id={} | duração={}min | valor=R${:.0f}".format(
            servico_nome, servico_id, duracao_minutos, valor_servico))

        # 3. Busca profissionais filtrados pelo serviço (Trinks) ou fallback geral
        profissional_id = None
        try:
            # Tenta buscar apenas profissionais que atendem este serviço
            profissionais_servico = trinks_api.listar_profissionais_por_servico(servico_id)
            profissionais = profissionais_servico if profissionais_servico else trinks_api.listar_profissionais()
            _debug("👥 {} profissionais para serviço {} (filtrado={})".format(
                len(profissionais), servico_nome, bool(profissionais_servico)))
        except Exception as e:
            logger.error("Erro buscando profissionais: %s", str(e))
            profissionais = []

        if profissional_nome:
            busca = profissional_nome.strip().lower()
            partes = [p for p in busca.split() if len(p) > 2]
            for p in profissionais:
                nome_apelido = p.get("nome", "").strip().lower()
                nome_completo = p.get("nome_completo", "").strip().lower()
                if (busca in nome_apelido or busca in nome_completo or
                        nome_apelido in busca or
                        any(parte in nome_completo for parte in partes) or
                        any(parte in nome_apelido for parte in partes)):
                    profissional_id = p["id"]
                    profissional_nome = p["nome_completo"] or p["nome"]
                    break

        if not profissional_id:
            lista = "\n".join("{}⃣ {}".format(i+1, p["nome_completo"] or p["nome"])
                              for i, p in enumerate(profissionais))
            _debug("⚠️ Profissional '{}' não encontrado — listando {} disponíveis".format(
                profissional_nome, len(profissionais)))
            return {
                "erro": "Qual profissional você prefere para {}?\n\n{}".format(servico_nome, lista),
            }

        # 5. Busca ou cria cliente no Trinks
        nome_cliente = args.get("cliente_nome") or cliente_info.get("nome", "")
        if not nome_cliente or nome_cliente.strip().lower() in ("cliente", ""):
            return {"erro": "Preciso do nome completo do cliente para criar o agendamento."}

        tel_cliente = telefone or ""
        cliente_id = args.get("cliente_trinks_id")

        if not cliente_id:
            try:
                candidatos = trinks_api.buscar_candidatos_cliente(nome_cliente, tel_cliente)
            except Exception as e:
                logger.warning("Erro ao buscar candidatos: %s", str(e))
                candidatos = []

            if len(candidatos) == 0:
                try:
                    novo = trinks_api.criar_cliente(nome_cliente, tel_cliente)
                    cliente_id = novo.get("id") if novo else None
                except Exception as e:
                    logger.warning("Erro ao criar cliente: %s", str(e))
                if not cliente_id:
                    _debug("❌ Não foi possível registrar cliente '{}'".format(nome_cliente))
                    return {"erro": "Não foi possível registrar o cliente no sistema."}
                _debug("✅ Cliente novo: {} | id={}".format(nome_cliente, cliente_id))
            elif len(candidatos) == 1:
                cliente_id = candidatos[0].get("id")
                _debug("✅ Cliente: {} | id={}".format(candidatos[0].get("nome"), cliente_id))
            else:
                linhas = ["Encontrei {} cadastros 🔍 Qual é o seu?\n".format(len(candidatos))]
                for i, c in enumerate(candidatos, 1):
                    fones = c.get("telefones", [])
                    tel_fmt = ""
                    if fones:
                        t = fones[0]
                        tel_fmt = " – ({}) {}-{}".format(
                            t.get("ddd", ""), t.get("telefone", "")[:5], t.get("telefone", "")[5:])
                    linhas.append("{}⃣ {}{}".format(i, c.get("nome", "?"), tel_fmt))
                linhas.append("\nResponda com o número correspondente.")
                _debug("🔍 {} candidatos — aguardando seleção".format(len(candidatos)))
                return {
                    "aguardando_selecao": True,
                    "candidatos": [{"indice": i+1, "id": c.get("id"), "nome": c.get("nome")}
                                   for i, c in enumerate(candidatos)],
                    "mensagem_usuario": "\n".join(linhas),
                }

        # 6. Cria agendamento com payload correto da API Trinks
        payload = {
            "servicoId": servico_id,
            "clienteId": cliente_id,
            "profissionalId": profissional_id,
            "dataHoraInicio": data_hora_iso,
            "duracaoEmMinutos": duracao_minutos,
            "valor": valor_servico,
            "observacoes": "Agendado por Marina AI",
            "confirmado": True,
        }

        logger.info("Criando agendamento Trinks: %s", payload)
        _debug("📤 servicoId={} | clienteId={} | profId={} | dataHoraInicio={} | {}min | R${:.0f}".format(
            servico_id, cliente_id, profissional_id, data_hora_iso, duracao_minutos, valor_servico))

        resultado = trinks_api.criar_agendamento(payload)

        if resultado and resultado.get("id"):
            ag_id = resultado["id"]
            _debug("✅ Agendamento criado! id={}".format(ag_id))
            return {
                "sucesso": True,
                "agendamento_id": ag_id,
                "servico": servico_nome,
                "profissional": profissional_nome,
                "data_hora": data_hora,
                "cliente": nome_cliente,
                "mensagem": "Agendamento criado com sucesso! ID: {}".format(ag_id),
            }

        _debug("❌ Falha ao criar agendamento — API não retornou ID")
        return {"erro": "Falha ao criar agendamento no Trinks. Tente novamente ou ligue para o salão."}

    def _tool_listar_agendamentos_cliente(self, args, telefone, cliente_info):
        from app.services.trinks_api import trinks_api
        from datetime import timedelta

        nome_cliente = args.get("cliente_nome") or cliente_info.get("nome", "")
        tel_cliente = telefone or ""

        cliente_id = None
        try:
            candidatos = trinks_api.buscar_candidatos_cliente(nome_cliente, tel_cliente)
            if candidatos:
                cliente_id = candidatos[0].get("id")
        except Exception as e:
            logger.warning("Erro ao buscar cliente para listar agendamentos: %s", str(e))

        hoje = _agora_sp().strftime("%Y-%m-%d")
        em_60_dias = (_agora_sp() + timedelta(days=60)).strftime("%Y-%m-%d")
        try:
            todos = trinks_api.listar_agendamentos(data_inicio=hoje, data_fim=em_60_dias)
        except Exception as e:
            logger.error("Erro ao listar agendamentos: %s", str(e))
            return {"erro": "Não foi possível buscar seus agendamentos."}

        if cliente_id:
            agendamentos = [ag for ag in todos if ag.get("cliente_id") == cliente_id]
        else:
            agendamentos = todos[:10]

        if not agendamentos:
            return {"agendamentos": [], "mensagem": "Nenhum agendamento futuro encontrado."}

        itens = []
        for ag in agendamentos[:5]:
            data_hora_raw = ag.get("data_hora", "")
            try:
                dt = datetime.fromisoformat(data_hora_raw.replace("Z", "+00:00"))
                data_fmt = dt.strftime("%d/%m/%Y às %H:%M")
            except Exception:
                data_fmt = data_hora_raw
            itens.append({
                "id": ag.get("id"),
                "servico": ag.get("servico", ""),
                "profissional": ag.get("profissional", ""),
                "data_hora": data_fmt,
                "status": ag.get("status", ""),
            })

        return {"agendamentos": itens, "total": len(itens)}

    def _tool_cancelar_agendamento(self, args, telefone):
        from app.services.trinks_api import trinks_api
        from app.services.evolution_api import evolution_api_client
        from config import WHATSAPP_INSTANCE_NAME

        def _debug(msg):
            logger.info("[DEBUG-CANCELAMENTO] %s", msg)
            try:
                evolution_api_client.enviar_mensagem(
                    instance=WHATSAPP_INSTANCE_NAME,
                    numero=telefone,
                    mensagem="🔧 *[DEV]* " + msg,
                )
            except Exception:
                pass

        agendamento_id = args.get("agendamento_id")
        if not agendamento_id:
            return {"erro": "ID do agendamento é obrigatório para cancelar."}

        motivo = args.get("motivo", "")
        _debug("📤 Cancelando agendamento id={}".format(agendamento_id))
        resultado = trinks_api.cancelar_agendamento(agendamento_id, motivo=motivo)

        if resultado is True:
            _debug("✅ Agendamento {} cancelado!".format(agendamento_id))
            return {
                "sucesso": True,
                "agendamento_id": agendamento_id,
                "mensagem": "Agendamento ID {} cancelado com sucesso!".format(agendamento_id),
            }

        _debug("❌ Falha ao cancelar agendamento id={}".format(agendamento_id))
        return {"erro": "Não foi possível cancelar o agendamento. Tente novamente ou ligue para o salão."}

    # ── Prompt ──────────────────────────────────────────

    def _construir_system_prompt(self, cliente_info):
        nome_cliente = cliente_info.get("nome", "Cliente")
        nome_conhecido = cliente_info.get("nome_conhecido", False)
        is_primeira_vez = cliente_info.get("is_primeira_vez", False)
        historico_servicos = cliente_info.get("historico_servicos", [])
        preferencias = cliente_info.get("preferencias", {})

        historico_str = ", ".join(historico_servicos[-5:]) if historico_servicos else "nenhum"
        profissional_pref = preferencias.get("profissional_preferido", "qualquer")
        horario_pref = preferencias.get("horario_preferido", "qualquer")
        sexo = cliente_info.get("sexo", "")
        sexo_str = {"M": "Masculino", "F": "Feminino"}.get(sexo, "Não informado")
        agora_sp = _agora_sp()
        data_hoje = agora_sp.strftime("%d/%m/%Y %H:%M")

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
            "- Sexo: {sexo_str}\n"
            "- Histórico de serviços: {historico_str}\n"
            "- Profissional preferido: {profissional_pref}\n"
            "- Horário preferido: {horario_pref}\n\n"
            "SAUDAÇÃO: {saudacao_instrucao}\n\n"
            "SERVIÇOS DISPONÍVEIS (todos podem ser agendados):\n"
            "{servicos}\n\n"
            "PROFISSIONAIS DISPONÍVEIS:\n"
            "{profissionais}\n\n"
            "INSTRUÇÕES:\n"
            "1. Responda em português brasileiro\n"
            "2. Seja breve (máximo 3 linhas por mensagem)\n"
            "3. Use 1-2 emojis\n"
            "4. Sempre use o nome do cliente quando conhecido\n"
            "5. Sexo do cliente: {sexo_str}. Se já conhecido, NUNCA pergunte masculino/feminino — "
            "use diretamente 'Corte Masculino' ou 'Corte Feminino'. Só pergunte se sexo for 'Não informado'.\n"
            "5b. SERVIÇOS: TODOS os serviços da lista acima estão disponíveis e podem ser agendados. "
            "NUNCA diga que não temos um serviço se ele está na lista. "
            "Ao falar de serviços, cite apenas os nomes — NUNCA liste preços em bloco. "
            "Informe o preço SOMENTE quando o cliente perguntar o valor de um serviço específico (ex: 'quanto custa o corte?').\n"
            "6. Para agendar: (1) pergunte serviço, profissional e data/hora, "
            "(2) chame validar_dados_cliente para mostrar os dados cadastrais do cliente e pedir confirmação, "
            "(3) se o cliente disser que algum dado está errado, peça a correção e chame atualizar_dados_cliente, "
            "(4) após confirmação dos dados, chame criar_agendamento. "
            "NÃO chame verificar_disponibilidade se o cliente já informou o horário — "
            "use verificar_disponibilidade SOMENTE se o cliente pedir sugestões de horário. "
            "Se o cliente quiser MÚLTIPLOS serviços (ex: cabelo + manicure), chame criar_agendamento "
            "uma vez para cada serviço — cada um pode ter profissional diferente.\n"
            "7. Se profissional não especificado, pergunte qual prefere. Profissionais: {profissionais_lista}\n"
            "8. CONFIRMAÇÃO OBRIGATÓRIA: após criar_agendamento, SEMPRE informe o ID retornado pela API. "
            "Exemplo: 'Agendado com sucesso! ✅ ID: 123456 | Serviço: X | Profissional: Y | Data: Z'. "
            "SEM ID DA API = NÃO CONFIRME O AGENDAMENTO. Se não receber ID, informe que houve falha.\n"
            "9. CRÍTICO: quando o cliente confirmar (disser sim/ok/pode/confirmo), chame criar_agendamento "
            "IMEDIATAMENTE usando os dados do histórico. NUNCA diga que agendou sem ter chamado a função.\n"
            "10. CANCELAMENTO — fluxo obrigatório:\n"
            "   a) PRIMEIRO verifique o histórico desta conversa: se já mencionamos um ID de agendamento do Trinks, use-o diretamente em cancelar_agendamento.\n"
            "   b) Se NÃO houver ID no histórico, chame listar_agendamentos_cliente.\n"
            "   c) Apresente a lista numerada assim: '1️⃣ Corte | Nilian | 20/05 às 14h (ID: 496402642)'\n"
            "   d) Peça para o cliente escolher pelo número (1, 2, 3...).\n"
            "   e) CRÍTICO: o campo agendamento_id em cancelar_agendamento deve ser o 'id' do agendamento retornado pela função listar_agendamentos_cliente — NUNCA use o número da lista (1, 2, 3) como ID.\n"
            "   f) Após cancelar, confirme: 'Agendamento ID 496402642 cancelado com sucesso! ✅'\n"
            "11. NUNCA invente IDs ou confirme operações sem retorno sucesso=True da função."
        ).format(
            nome=self.marina_name,
            salao=self.salao_name,
            data_hoje=data_hoje,
            nome_cliente=nome_cliente,
            sexo_str=sexo_str,
            historico_str=historico_str,
            profissional_pref=profissional_pref,
            horario_pref=horario_pref,
            saudacao_instrucao=saudacao_instrucao,
            servicos=self._servicos_para_texto(),
            profissionais=self._profissionais_para_texto(),
            profissionais_lista=self._profissionais_para_texto(),
        )

    # ── Fallback sem IA ────────────────────────────────────────

    def _resposta_fallback(self, mensagem, cliente_info):
        nome = cliente_info.get("nome", "")
        saudacao = "Olá{}! ".format(", " + nome if nome and nome != "Cliente" else "")
        m = mensagem.lower()

        if any(p in m for p in ["serviço", "serviços", "fazem", "oferecem", "tem"]):
            if _servicos_cache:
                top = _servicos_cache[:10]
                lista = "\n".join("• {}".format(s["nome"]) for s in top)
                return "{}Nossos serviços 💇‍♀️:\n{}\n\nQuer agendar ou saber mais?".format(saudacao, lista)

        if any(p in m for p in ["preço", "valor", "custa", "quanto"]):
            servico_mencionado = next(
                (s for s in _servicos_cache if s["nome"].lower() in m), None
            ) if _servicos_cache else None
            if servico_mencionado:
                return "{}O {} custa R${:.0f} 💅 Quer agendar?".format(
                    saudacao, servico_mencionado["nome"], servico_mencionado["preco"])
            return "{}Me diga qual serviço você quer saber o valor 😊".format(saudacao)

        if any(p in m for p in ["agendar", "marcar", "horário", "hora", "vaga", "disponível"]):
            prof = self._profissionais_para_texto()
            return "{}Adoraria agendar para você! ✨ Temos: {}.\nQual serviço e data você prefere?".format(saudacao, prof)

        if any(p in m for p in ["oi", "olá", "opa", "bom dia", "boa tarde", "boa noite"]):
            return "{}Sou a Marina, assistente virtual do {} 💚 Como posso te ajudar hoje?".format(saudacao, self.salao_name)

        return "{}Sou a Marina, do {} 😊 Posso ajudar com serviços, preços e agendamentos. O que você precisa?".format(saudacao, self.salao_name)

    # ── Interface pública ───────────────────────────────────────

    def _e_confirmacao(self, mensagem, historico_conversas):
        """Detecta se a mensagem é uma confirmação de agendamento pendente."""
        palavras_confirmacao = ["sim", "pode", "ok", "isso", "confirmo", "confirma", "quero", "tá", "ta", "bom", "certo"]
        m = mensagem.strip().lower()
        if not any(p in m for p in palavras_confirmacao):
            return False
        if historico_conversas:
            ultima = historico_conversas[-1].get("resposta_marina", "").lower()
            indicadores = ["confirma", "posso agendar", "reservar", "quer confirmar", "confirmo", "agendo"]
            return any(ind in ultima for ind in indicadores)
        return False

    def _extrair_ids_agendamento(self, historico_conversas):
        """Extrai IDs de agendamentos mencionados nas respostas da Marina no histórico."""
        import re
        ids = []
        if not historico_conversas:
            return ids
        for conv in historico_conversas:
            resposta = conv.get("resposta_marina", "")
            matches = re.findall(r'\bID[:\s]+(\d{6,})', resposta, re.IGNORECASE)
            ids.extend([int(m) for m in matches])
        seen = set()
        return [x for x in ids if not (x in seen or seen.add(x))]

    def processar_mensagem_sync(self, mensagem, cliente_info, historico_conversas=None,
                                 db=None, telefone=None):
        try:
            system_prompt = self._construir_system_prompt(cliente_info)
            messages = [{"role": "system", "content": system_prompt}]

            if historico_conversas:
                for conv in historico_conversas[-5:]:
                    user_msg = conv.get("mensagem_usuario", "")
                    assistant_msg = conv.get("resposta_marina", "")
                    if user_msg:
                        messages.append({"role": "user", "content": user_msg})
                    if assistant_msg:
                        messages.append({"role": "assistant", "content": assistant_msg})

            ids_agendamento = self._extrair_ids_agendamento(historico_conversas)
            if ids_agendamento:
                ids_str = ", ".join(str(i) for i in ids_agendamento)
                messages.append({
                    "role": "system",
                    "content": "[SISTEMA] IDs de agendamentos registrados nesta conversa: {}. "
                               "Use estes IDs ao cancelar — NÃO invente outros.".format(ids_str),
                })

            messages.append({"role": "user", "content": mensagem})

            resposta = self._chamar_gpt_com_tools(messages, db, telefone, cliente_info)

            if not resposta:
                resposta = self._resposta_fallback(mensagem, cliente_info)

            if not resposta.startswith("Marina IA:"):
                resposta = "Marina IA: " + resposta

            intencao = self._classificar_intencao(mensagem)
            return resposta, intencao
        except Exception as e:
            logger.error("Erro ao processar: %s", str(e))
            return "Marina IA: Desculpe, tive um problema técnico. Pode tentar novamente? 😊", "erro"

    def _classificar_intencao(self, mensagem):
        m = mensagem.lower()
        if any(p in m for p in ["agendar", "marcar", "horário", "hora", "disponível", "vaga"]):
            return "agendamento"
        elif any(p in m for p in ["cancelar", "desmarcar", "remarcar"]):
            return "cancelamento"
        elif any(p in m for p in ["preço", "valor", "custa", "quanto"]):
            return "consulta_preco"
        elif any(p in m for p in ["serviço", "serviços", "fazem", "oferecem"]):
            return "consulta_servicos"
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
