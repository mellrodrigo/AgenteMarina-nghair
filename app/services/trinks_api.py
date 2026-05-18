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

    # ── HTTP helpers ──────────────────────────────────────────

    def _get(self, endpoint: str, params: dict = None) -> Optional[Dict]:
        url = "{}/{}".format(self.base_url, endpoint.lstrip("/"))
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
            resp.raise_for_status()
            return resp.json()
        except requests.exceptions.Timeout:
            logger.error("Trinks API timeout: %s", url)
            return None
        except requests.exceptions.RequestException as e:
            logger.error("Trinks API erro em %s: %s", url, str(e))
            return None

    def _post(self, endpoint: str, payload: dict) -> Optional[Dict]:
        url = "{}/{}".format(self.base_url, endpoint.lstrip("/"))
        try:
            resp = self.session.post(url, json=payload, timeout=30)
            if resp.status_code == 404:
                logger.warning("Trinks endpoint não encontrado: %s", endpoint)
                return None
            if not resp.ok:
                logger.error("Trinks POST %s: %s %s", endpoint, resp.status_code, resp.text[:300])
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

    # ── Serviços ──────────────────────────────────────────────

    def listar_servicos(self, apenas_visiveis: bool = False) -> List[Dict[str, Any]]:
        """GET /v1/servicos — campos reais: nome, preco, duracaoEmMinutos, categoria, visivelParaCliente"""
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
            })
        logger.info("Trinks: %d serviços obtidos", len(servicos))
        return servicos

    # ── Profissionais ─────────────────────────────────────────

    def listar_profissionais(self) -> List[Dict[str, Any]]:
        """GET /v1/profissionais — campos reais: nome, apelido, id"""
        itens = self._paginar("/v1/profissionais")
        profissionais = []
        for item in itens:
            nome_exibicao = item.get("apelido") or item.get("nome", "")
            profissionais.append({
                "id": item.get("id"),
                "nome": nome_exibicao,
                "nome_completo": item.get("nome", ""),
                "cargo": "Profissional",
                "ativo": True,
            })
        logger.info("Trinks: %d profissionais obtidos", len(profissionais))
        return profissionais

    # ── Clientes ──────────────────────────────────────────────

    def listar_clientes(self, nome: str = None) -> List[Dict]:
        """GET /v1/clientes?estabelecimentoId=...&nome=... — busca por nome"""
        params = {"estabelecimentoId": TRINKS_ESTABELECIMENTO_ID}
        if nome:
            params["nome"] = nome
        dados = self._get("/v1/clientes", params=params)
        if dados is None:
            return []
        if isinstance(dados, list):
            return dados
        return dados.get("data", [])

    def criar_cliente(self, nome: str, telefone: str) -> Optional[Dict]:
        """POST /v1/clientes — payload correto com telefones[]"""
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

    def buscar_cliente_por_telefone(self, telefone: str) -> Optional[Dict]:
        """Pagina todos os clientes e filtra por telefone localmente.
        A API Trinks não suporta filtro por telefone — comparação feita aqui."""
        tel_clean = "".join(filter(str.isdigit, telefone))
        tel_sem_ddi = tel_clean[2:] if tel_clean.startswith("55") and len(tel_clean) > 10 else tel_clean

        params = {"estabelecimentoId": TRINKS_ESTABELECIMENTO_ID, "pageSize": 100, "page": 1}
        pagina = 1
        while True:
            params["page"] = pagina
            dados = self._get("/v1/clientes", params=params)
            if not dados:
                break
            clientes = dados if isinstance(dados, list) else dados.get("data", [])
            for c in clientes:
                for t in c.get("telefones", []):
                    num = "".join(filter(str.isdigit, str(t.get("numero", ""))))
                    if num and (num == tel_clean or num == tel_sem_ddi or
                                tel_sem_ddi[-8:] == num[-8:]):
                        logger.info("Trinks: cliente encontrado por telefone id=%s nome=%s", c.get("id"), c.get("nome"))
                        return c
            total_pages = dados.get("totalPages", 1) if isinstance(dados, dict) else 1
            if pagina >= total_pages:
                break
            pagina += 1
        return None

    def buscar_ou_criar_cliente(self, nome: str, telefone: str) -> Optional[int]:
        """Retorna clienteId: busca por telefone, depois por nome, cria se não encontrar."""
        # 1. Busca por telefone (mais confiável — ignora variações de nome)
        if telefone:
            cliente = self.buscar_cliente_por_telefone(telefone)
            if cliente:
                return cliente.get("id")

        # 2. Busca por nome
        if nome and nome != "Cliente":
            clientes = self.listar_clientes(nome=nome)
            if clientes:
                cid = clientes[0].get("id")
                logger.info("Trinks: cliente encontrado por nome id=%s", cid)
                return cid

        # 3. Cria novo cliente
        resultado = self.criar_cliente(nome, telefone)
        if resultado:
            return resultado.get("id")
        logger.warning("Trinks: não foi possível criar cliente %s", nome)
        return None

    # ── Disponibilidade ───────────────────────────────────────

    def horarios_disponiveis(
        self,
        data: str,
        servico_id: int = None,
        profissional_id: int = None,
    ) -> List[str]:
        """Retorna lista de horários disponíveis (HH:MM) para uma data.
        Tenta endpoint Trinks nativo; fallback: calcula a partir dos agendamentos do dia."""
        params = {"data": data}
        if servico_id:
            params["servicoId"] = servico_id
        if profissional_id:
            params["profissionalId"] = profissional_id

        for endpoint in [
            "/v1/horarios-disponiveis",
            "/v1/disponibilidade",
            "/v1/agenda/disponibilidade",
        ]:
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
                    logger.info("Trinks disponibilidade via %s: %d slots", endpoint, len(horarios))
                    return horarios

        return self._calcular_horarios_livres(data, profissional_id)

    def _calcular_horarios_livres(self, data: str, profissional_id: int = None) -> List[str]:
        """Fallback: calcula horários livres com base nos agendamentos existentes"""
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
        logger.info("Trinks disponibilidade (fallback): %d slots para %s", len(slots), data)
        return slots[:12]

    # ── Agendamentos ──────────────────────────────────────────

    def listar_agendamentos(
        self,
        data_inicio: str = None,
        data_fim: str = None,
    ) -> List[Dict[str, Any]]:
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

    # ── Sincronização com banco local ─────────────────────────

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

    # ── Diagnóstico ───────────────────────────────────────────

    def testar_conexao(self) -> Dict[str, Any]:
        dados = self._get("/v1/servicos", params={"pageSize": 1})
        if dados is not None:
            total = dados.get("totalRecords", "?")
            return {"ok": True, "mensagem": "Conexão OK — {} serviços no Trinks".format(total)}
        return {"ok": False, "mensagem": "Falha na conexão — verifique TRINKS_API_KEY e TRINKS_ESTABELECIMENTO_ID"}


trinks_api = TrinksAPIClient()
