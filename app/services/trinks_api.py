"""
Cliente REST oficial da API Trinks
Documentação: https://trinks.readme.io/reference/introducao
"""
import logging
import os
import requests
from datetime import datetime
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session

from config import TRINKS_API_KEY, TRINKS_API_URL

logger = logging.getLogger(__name__)

HEADERS = {
    "X-Api-Key": TRINKS_API_KEY,
    "accept": "application/json",
    "Content-Type": "application/json",
}


class TrinksAPIClient:
    """Cliente para a API REST oficial do Trinks"""

    def __init__(self):
        self.base_url = TRINKS_API_URL.rstrip("/")
        self.session = requests.Session()
        self.session.headers.update(HEADERS)
        self.ultima_sincronizacao: Optional[datetime] = None

    def _get(self, endpoint: str, params: dict = None) -> Optional[Dict]:
        """Executa GET na API e retorna JSON ou None em caso de erro"""
        url = f"{self.base_url}/{endpoint.lstrip('/')}"
        try:
            resp = self.session.get(url, params=params, timeout=30)
            if resp.status_code == 401:
                logger.error("Trinks API: token inválido ou expirado (401)")
                return None
            if resp.status_code == 403:
                logger.error("Trinks API: acesso negado (403)")
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
        """Executa POST na API e retorna JSON ou None em caso de erro"""
        url = f"{self.base_url}/{endpoint.lstrip('/')}"
        try:
            resp = self.session.post(url, json=payload, timeout=30)
            resp.raise_for_status()
            return resp.json()
        except requests.exceptions.RequestException as e:
            logger.error("Trinks API POST erro em %s: %s", url, str(e))
            return None

    # ------------------------------------------------------------------
    # Serviços
    # ------------------------------------------------------------------

    def listar_servicos(self) -> List[Dict[str, Any]]:
        """GET /v1/servicos — Retorna todos os serviços do estabelecimento"""
        dados = self._get("/v1/servicos")
        if not dados:
            return []
        itens = dados if isinstance(dados, list) else dados.get("data", dados.get("servicos", []))
        servicos = []
        for item in itens:
            servicos.append({
                "nome": item.get("nome", item.get("name", "")),
                "descricao": item.get("descricao", item.get("description", "")),
                "categoria": item.get("categoria", item.get("category", "Geral")),
                "preco": float(item.get("preco", item.get("price", 0)) or 0),
                "duracao_minutos": int(item.get("duracao", item.get("duration_minutes", 60)) or 60),
                "ativo": bool(item.get("ativo", item.get("active", True))),
            })
        logger.info("Trinks API: %d serviços obtidos", len(servicos))
        return servicos

    # ------------------------------------------------------------------
    # Profissionais
    # ------------------------------------------------------------------

    def listar_profissionais(self) -> List[Dict[str, Any]]:
        """GET /v1/profissionais — Retorna todos os profissionais"""
        dados = self._get("/v1/profissionais")
        if not dados:
            return []
        itens = dados if isinstance(dados, list) else dados.get("data", dados.get("profissionais", []))
        profissionais = []
        for item in itens:
            profissionais.append({
                "nome": item.get("nome", item.get("name", "")),
                "cargo": item.get("cargo", item.get("role", "Profissional")),
                "ativo": bool(item.get("ativo", item.get("active", True))),
            })
        logger.info("Trinks API: %d profissionais obtidos", len(profissionais))
        return profissionais

    # ------------------------------------------------------------------
    # Clientes
    # ------------------------------------------------------------------

    def listar_clientes(self, pagina: int = 1) -> List[Dict[str, Any]]:
        """GET /v1/clientes — Retorna clientes do estabelecimento"""
        dados = self._get("/v1/clientes", params={"page": pagina, "per_page": 100})
        if not dados:
            return []
        itens = dados if isinstance(dados, list) else dados.get("data", dados.get("clientes", []))
        clientes = []
        for item in itens:
            clientes.append({
                "nome": item.get("nome", item.get("name", "")),
                "telefone": item.get("telefone", item.get("phone", "")),
                "email": item.get("email", ""),
            })
        logger.info("Trinks API: %d clientes obtidos (página %d)", len(clientes), pagina)
        return clientes

    # ------------------------------------------------------------------
    # Agendamentos
    # ------------------------------------------------------------------

    def listar_agendamentos(
        self,
        data_inicio: str = None,
        data_fim: str = None,
    ) -> List[Dict[str, Any]]:
        """GET /v1/agendamentos — Retorna agendamentos no período"""
        params = {}
        if data_inicio:
            params["data_inicio"] = data_inicio
        if data_fim:
            params["data_fim"] = data_fim
        dados = self._get("/v1/agendamentos", params=params)
        if not dados:
            return []
        itens = dados if isinstance(dados, list) else dados.get("data", dados.get("agendamentos", []))
        agendamentos = []
        for item in itens:
            agendamentos.append({
                "cliente": item.get("cliente", item.get("client_name", "")),
                "data_hora": item.get("data_hora", item.get("scheduled_at", "")),
                "servico": item.get("servico", item.get("service_name", "")),
                "profissional": item.get("profissional", item.get("professional_name", "")),
                "status": item.get("status", "confirmado"),
                "valor": float(item.get("valor", item.get("price", 0)) or 0),
            })
        logger.info("Trinks API: %d agendamentos obtidos", len(agendamentos))
        return agendamentos

    def criar_agendamento(self, payload: dict) -> Optional[Dict]:
        """POST /v1/agendamentos — Cria novo agendamento"""
        resultado = self._post("/v1/agendamentos", payload)
        if resultado:
            logger.info("Trinks API: agendamento criado")
        return resultado

    # ------------------------------------------------------------------
    # Sincronização com banco local
    # ------------------------------------------------------------------

    def sincronizar_dados(self, db: Session) -> bool:
        """Sincroniza serviços e profissionais do Trinks para o banco local"""
        from app.models.database import Servico, Profissional

        try:
            logger.info("Iniciando sincronização com API Trinks...")

            servicos_api = self.listar_servicos()
            for s in servicos_api:
                if not s["nome"]:
                    continue
                existente = db.query(Servico).filter(Servico.nome == s["nome"]).first()
                if existente:
                    existente.preco = s["preco"]
                    existente.duracao_minutos = s["duracao_minutos"]
                    existente.ativo = s["ativo"]
                    existente.data_atualizacao = datetime.utcnow()
                else:
                    db.add(Servico(
                        nome=s["nome"],
                        descricao=s["descricao"],
                        categoria=s["categoria"],
                        preco=s["preco"],
                        duracao_minutos=s["duracao_minutos"],
                        ativo=s["ativo"],
                    ))

            profissionais_api = self.listar_profissionais()
            for p in profissionais_api:
                if not p["nome"]:
                    continue
                existente = db.query(Profissional).filter(Profissional.nome == p["nome"]).first()
                if existente:
                    existente.cargo = p["cargo"]
                    existente.ativo = p["ativo"]
                    existente.data_atualizacao = datetime.utcnow()
                else:
                    db.add(Profissional(nome=p["nome"], cargo=p["cargo"], ativo=p["ativo"]))

            db.commit()
            self.ultima_sincronizacao = datetime.utcnow()
            logger.info("Sincronização concluída: %d serviços, %d profissionais",
                        len(servicos_api), len(profissionais_api))
            return True

        except Exception as e:
            db.rollback()
            logger.error("Erro na sincronização com Trinks: %s", str(e))
            return False

    def testar_conexao(self) -> Dict[str, Any]:
        """Verifica se o token está válido fazendo uma chamada leve"""
        dados = self._get("/v1/servicos")
        if dados is not None:
            return {"ok": True, "mensagem": "Conexão com Trinks API bem-sucedida"}
        return {"ok": False, "mensagem": "Falha na conexão com Trinks API — verifique TRINKS_API_KEY"}


trinks_api = TrinksAPIClient()
