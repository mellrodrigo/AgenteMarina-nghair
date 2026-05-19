"""
Cliente REST oficial da API Trinks
Documentação: https://trinks.readme.io/reference/introducao

Campos reais confirmados pela API (NGHair, estabelecimentoId=20181):

  Serviços:    nome, descricao, categoria, preco, duracaoEmMinutos,
               visivelParaCliente, id
  Profissionais: nome, apelido, id, cpf
  Agendamentos:  id, dataHoraInicio, duracaoEmMinutos, valor,
               cliente{id,nome}, profissional{id,nome},
               servico{id,nome}, status{id,nome},
               observacoesDoCliente, observacoesDoEstabelecimento
"""
import logging
import time
import requests
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from config import TRINKS_API_KEY, TRINKS_API_URL, TRINKS_ESTABELECIMENTO_ID

logger = logging.getLogger(__name__)

HEADERS = {
    "X-Api-Key": TRINKS_API_KEY,
    "estabelecimentoId": TRINKS_ESTABELECIMENTO_ID,
    "accept": "application/json",
    "Content-Type": "application/json",
}


class TrinksAPIClient:

    def __init__(self):
        self.base_url = TRINKS_API_URL.rstrip("/")
        self.session = requests.Session()
        self.session.headers.update(HEADERS)
        self.ultima_sincronizacao: Optional[datetime] = None

    # ── HTTP helpers ──────────────────

    def _get(self, endpoint: str, params: dict = None) -> Optional[Dict]:
        url = "{}/{}".format(self.base_url, endpoint.lstrip("/"))
        for attempt in range(4):
            try:
                resp = self.session.get(url, params=params, timeout=30)
                if resp.status_code == 401:
                    logger.error("Trinks API 401: token inválido")
                    return None
                if resp.status_code == 403:
                    logger.error("Trinks API 403: acesso negado")
                    return None
                if resp.status_code == 404:
                    logger.warning("Trinks endpoint não encontrado: %s", endpoint)
                    return None
                if resp.status_code == 429:
                    wait = 2 ** attempt
                    logger.warning("Trinks API 429 (rate limit), aguardando %ds... (tentativa %d/4)", wait, attempt + 1)
                    time.sleep(wait)
                    continue
                resp.raise_for_status()
                return resp.json()
            except requests.exceptions.Timeout:
                logger.error("Trinks API timeout: %s", url)
                return None
            except requests.exceptions.RequestException as e:
                logger.error("Trinks API erro em %s: %s", url, str(e))
                return None
        logger.error("Trinks API: máximo de tentativas atingido para %s", url)
        return None

    def _post(self, endpoint: str, payload: dict) -> Optional[Dict]:
        url = "{}/{}".format(self.base_url, endpoint.lstrip("/"))
        try:
            resp = self.session.post(url, json=payload, timeout=30)
            if resp.status_code == 404:
                logger.warning("Trinks endpoint não encontrado: %s", endpoint)
                return None
            if not resp.ok:
                logger.error("Trinks POST %s: %s %s", endpoint, resp.status_code, resp.text[:1000])
                return None
            return resp.json()
        except requests.exceptions.RequestException as e:
            logger.error("Trinks API POST erro em %s: %s", url, str(e))
            return None

    def _paginar(self, endpoint: str, params: dict = None) -> List[Dict]:
        """Busca todas as páginas de um endpoint paginado"""
        params = params or {}
        params.setdefault("pageSize", 100)
        params["page"] = 1
        todos = []
        while True:
            dados = self._get(endpoint, params=params)
            if not dados:
                break
            itens = dados.get("data", [])
            todos.extend(itens)
            total_pages = dados.get("totalPages", 1)
            if params["page"] >= total_pages:
                break
            params["page"] += 1
        return todos

    # ── Serviços ───────────────────────────────────────

    def listar_servicos(self, apenas_visiveis: bool = False) -> List[Dict[str, Any]]:
        """GET /v1/servicos"""
        itens = self._paginar("/v1/servicos")
        servicos = []
        for item in itens:
            visivel = item.get("visivelParaCliente", True)
            if apenas_visiveis and not visivel:
                continue
            servicos.append({
                "id": item.get("id"),
                "nome": item.get("nome", ""),
                "descricao": item.get("descricao", ""),
                "categoria": item.get("categoria", "Geral"),
                "preco": float(item.get("preco") or 0),
                "duracao_minutos": int(item.get("duracaoEmMinutos") or 60),
                "visivel_cliente": visivel,
                "ativo": True,
                "_raw": item,
            })
        logger.info("Trinks: %d serviços obtidos", len(servicos))
        return servicos

    # ── Profissionais ───────────────────────────────

    def listar_profissionais(self) -> List[Dict[str, Any]]:
        """GET /v1/profissionais"""
        itens = self._paginar("/v1/profissionais")
        profissionais = []
        for item in itens:
            nome_exibicao = (item.get("apelido") or item.get("nome", "")).strip()
            profissionais.append({
                "id": item.get("id"),
                "nome": nome_exibicao,
                "nome_completo": item.get("nome", ""),
                "cargo": "Profissional",
                "ativo": True,
            })
        logger.info("Trinks: %d profissionais obtidos", len(profissionais))
        return profissionais

    # ── Clientes ──────────────────────────────────

    @staticmethod
    def _tel_para_trinks(telefone: str) -> str:
        tel = "".join(filter(str.isdigit, telefone))
        if tel.startswith("55") and len(tel) >= 12:
            tel = tel[2:]
        if len(tel) in (10, 11):
            tel = tel[2:]
        return tel

    def listar_clientes(self, nome: str = None, telefone: str = None) -> List[Dict]:
        """GET /v1/clientes"""
        params = {"estabelecimentoId": TRINKS_ESTABELECIMENTO_ID, "incluirDetalhes": "false"}
        if nome:
            params["nome"] = nome
        if telefone:
            params["telefone"] = telefone
        dados = self._get("/v1/clientes", params=params)
        if dados is None:
            return []
        if isinstance(dados, list):
            return dados
        return dados.get("data", [])

    def criar_cliente(self, nome: str, telefone: str) -> Optional[Dict]:
        """POST /v1/clientes"""
        tel_clean = "".join(filter(str.isdigit, telefone))
        payload = {
            "estabelecimentoId": TRINKS_ESTABELECIMENTO_ID,
            "nome": nome,
            "telefones": [{"numero": tel_clean, "tipo": "celular"}] if tel_clean else [],
        }
        resultado = self._post("/v1/clientes", payload)
        if resultado:
            logger.info("Trinks: cliente criado nome=%s id=%s", nome, resultado.get("id"))
        return resultado

    def buscar_candidatos_cliente(self, nome: str, telefone: str) -> List[Dict]:
        """Busca clientes combinando nome + telefone (mais específico ao mais genérico)."""
        tel_trinks = self._tel_para_trinks(telefone) if telefone else ""
        primeiro_nome = nome.strip().split()[0] if nome and nome != "Cliente" else ""

        if primeiro_nome and tel_trinks:
            resultado = self.listar_clientes(nome=primeiro_nome, telefone=tel_trinks)
            if resultado:
                return resultado

        if tel_trinks:
            resultado = self.listar_clientes(telefone=tel_trinks)
            if resultado:
                return resultado

        if nome and nome != "Cliente":
            resultado = self.listar_clientes(nome=nome)
            if resultado:
                return resultado

        if primeiro_nome and primeiro_nome != nome:
            resultado = self.listar_clientes(nome=primeiro_nome)
            if resultado:
                return resultado

        return []

    def buscar_ou_criar_cliente(self, nome: str, telefone: str) -> Optional[int]:
        candidatos = self.buscar_candidatos_cliente(nome, telefone)
        if candidatos:
            return candidatos[0].get("id")
        resultado = self.criar_cliente(nome, telefone)
        if resultado:
            return resultado.get("id")
        return None

    def buscar_cliente_por_id(self, cliente_id: int) -> Optional[Dict]:
        """GET /v1/clientes/{id}"""
        dados = self._get("/v1/clientes/{}".format(cliente_id))
        return dados

    def atualizar_cliente(self, cliente_id: int, dados: dict) -> bool:
        """PUT /v1/clientes/{id}"""
        url = "{}/v1/clientes/{}".format(self.base_url, cliente_id)
        try:
            resp = self.session.put(url, json=dados, timeout=30)
            if resp.ok:
                logger.info("Trinks: cliente %s atualizado", cliente_id)
                return True
            logger.error("Trinks: falha ao atualizar cliente %s: %s %s",
                         cliente_id, resp.status_code, resp.text[:500])
            return False
        except requests.exceptions.RequestException as e:
            logger.error("Trinks: erro ao atualizar cliente %s: %s", cliente_id, str(e))
            return False

    # ── Disponibilidade ───────────────────────────────

    def horarios_disponiveis(self, data: str, servico_id: int = None, profissional_id: int = None) -> List[str]:
        params = {"data": data}
        if servico_id:
            params["servicoId"] = servico_id
        if profissional_id:
            params["profissionalId"] = profissional_id

        for endpoint in ["/v1/horarios-disponiveis", "/v1/disponibilidade", "/v1/agenda/disponibilidade"]:
            dados = self._get(endpoint, params=params)
            if dados is not None:
                horarios = []
                itens = dados if isinstance(dados, list) else dados.get("data", dados.get("horarios", []))
                for h in itens:
                    if isinstance(h, str):
                        horarios.append(h)
                    elif isinstance(h, dict) and h.get("disponivel", True):
                        hora = h.get("hora") or h.get("horario") or h.get("dataHora", "")
                        if hora:
                            horarios.append(hora[-5:] if len(hora) > 5 else hora)
                if horarios:
                    return horarios

        return self._calcular_horarios_livres(data, profissional_id)

    def _calcular_horarios_livres(self, data: str, profissional_id: int = None) -> List[str]:
        agendamentos = self.listar_agendamentos(data_inicio=data, data_fim=data)
        if profissional_id:
            agendamentos = [a for a in agendamentos if a.get("profissional_id") == profissional_id]

        ocupados = set()
        for ag in agendamentos:
            try:
                dt_str = ag.get("data_hora", "")
                if dt_str:
                    dt = datetime.fromisoformat(dt_str.replace("Z", "+00:00"))
                    ocupados.add(dt.strftime("%H:%M"))
            except Exception:
                pass

        slots = []
        hora = 8
        while hora < 18:
            for minuto in [0, 30]:
                slot = "{:02d}:{:02d}".format(hora, minuto)
                if slot not in ocupados:
                    slots.append(slot)
            hora += 1
        return slots[:12]

    # ── Agendamentos ────────────────────────────────

    def listar_agendamentos(self, data_inicio: str = None, data_fim: str = None) -> List[Dict[str, Any]]:
        """GET /v1/agendamentos"""
        params = {}
        if data_inicio:
            params["dataInicio"] = data_inicio
        if data_fim:
            params["dataFim"] = data_fim
        itens = self._paginar("/v1/agendamentos", params=params)
        agendamentos = []
        for item in itens:
            agendamentos.append({
                "id": item.get("id"),
                "cliente": item.get("cliente", {}).get("nome", ""),
                "cliente_id": item.get("cliente", {}).get("id"),
                "data_hora": item.get("dataHoraInicio", ""),
                "duracao_minutos": item.get("duracaoEmMinutos", 0),
                "servico": item.get("servico", {}).get("nome", ""),
                "servico_id": item.get("servico", {}).get("id"),
                "profissional": item.get("profissional", {}).get("nome", ""),
                "profissional_id": item.get("profissional", {}).get("id"),
                "status": item.get("status", {}).get("nome", ""),
                "status_id": item.get("status", {}).get("id"),
                "valor": float(item.get("valor") or 0),
                "observacoes_cliente": item.get("observacoesDoCliente", ""),
                "observacoes_salao": item.get("observacoesDoEstabelecimento", ""),
            })
        logger.info("Trinks: %d agendamentos obtidos", len(agendamentos))
        return agendamentos

    def criar_agendamento(self, payload: dict) -> Optional[Dict]:
        """POST /v1/agendamentos"""
        resultado = self._post("/v1/agendamentos", payload)
        if resultado:
            logger.info("Trinks: agendamento criado id=%s", resultado.get("id"))
        return resultado

    def cancelar_agendamento(self, agendamento_id: int, motivo: str = "") -> bool:
        """PATCH /v1/agendamentos/{id}/status/cancelado"""
        url = "{}/v1/agendamentos/{}/status/cancelado".format(self.base_url, agendamento_id)
        payload = {
            "quemCancelou": 1,  # 1=cliente, 2=profissional, 3=estabelecimento, 4=outro
            "motivo": motivo or "A pedido do cliente",
        }
        try:
            resp = self.session.patch(url, json=payload, timeout=30)
            if resp.ok:
                logger.info("Trinks: agendamento %s cancelado", agendamento_id)
                return True
            logger.error("Trinks: falha ao cancelar agendamento %s: %s %s",
                         agendamento_id, resp.status_code, resp.text[:500])
            return False
        except requests.exceptions.RequestException as e:
            logger.error("Trinks: erro ao cancelar agendamento %s: %s", agendamento_id, str(e))
            return False

    # ── Sincronizaç── com banco local ────────────────────

    def sincronizar_dados(self, db: Session) -> bool:
        """Sincroniza serviços e profissionais do Trinks para o banco local"""
        from app.models.database import Servico, Profissional
        try:
            logger.info("Sincronização Trinks iniciada...")

            servicos_api = self.listar_servicos(apenas_visiveis=False)
            for s in servicos_api:
                if not s["nome"]:
                    continue
                existente = db.query(Servico).filter(Servico.nome == s["nome"]).first()
                if existente:
                    existente.preco = s["preco"]
                    existente.duracao_minutos = s["duracao_minutos"]
                    existente.categoria = s["categoria"]
                    existente.data_atualizacao = datetime.utcnow()
                else:
                    try:
                        sp = db.begin_nested()
                        db.add(Servico(
                            nome=s["nome"],
                            descricao=s["descricao"],
                            categoria=s["categoria"],
                            preco=s["preco"],
                            duracao_minutos=s["duracao_minutos"],
                            ativo=True,
                        ))
                        sp.commit()
                    except IntegrityError:
                        sp.rollback()

            profissionais_api = self.listar_profissionais()
            for p in profissionais_api:
                if not p["nome"]:
                    continue
                existente = db.query(Profissional).filter(Profissional.nome == p["nome"]).first()
                if existente:
                    existente.data_atualizacao = datetime.utcnow()
                else:
                    try:
                        sp = db.begin_nested()
                        db.add(Profissional(
                            nome=p["nome"],
                            cargo=p["cargo"],
                            ativo=True,
                        ))
                        sp.commit()
                    except IntegrityError:
                        sp.rollback()

            db.commit()
            self.ultima_sincronizacao = datetime.utcnow()
            logger.info("Sync concluído: %d serviços, %d profissionais",
                        len(servicos_api), len(profissionais_api))
            return True

        except Exception as e:
            db.rollback()
            logger.error("Erro no sync Trinks: %s", str(e))
            return False

    # ── Diagnóstico ────────────────────────────────────

    def testar_conexao(self) -> Dict[str, Any]:
        dados = self._get("/v1/servicos", params={"pageSize": 1})
        if dados is not None:
            total = dados.get("totalRecords", "?")
            return {"ok": True, "mensagem": "Conexão OK — {} serviços no Trinks".format(total)}
        return {"ok": False, "mensagem": "Falha na conexão — verifique TRINKS_API_KEY e TRINKS_ESTABELECIMENTO_ID"}


trinks_api = TrinksAPIClient()
