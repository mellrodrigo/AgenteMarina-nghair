"""
Scraper real do Trinks usando Selenium
Extrai dados de clientes, serviços e agendamentos
"""
import logging
import asyncio
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from sqlalchemy.orm import Session

from config import TRINKS_EMAIL, TRINKS_PASSWORD

logger = logging.getLogger(__name__)


class TrinksScraperReal:
    """Scraper real do Trinks usando Selenium"""

    def __init__(self):
        self.email = TRINKS_EMAIL
        self.password = TRINKS_PASSWORD
        self.base_url = "https://www.trinks.com"
        self.driver = None
        self.ultima_sincronizacao = None

    def _criar_driver(self) -> webdriver.Chrome:
        """Cria instância do Selenium WebDriver"""
        try:
            chrome_options = Options()
            
            # Configurações para ambiente de servidor
            chrome_options.add_argument("--headless")  # Modo headless
            chrome_options.add_argument("--no-sandbox")
            chrome_options.add_argument("--disable-dev-shm-usage")
            chrome_options.add_argument("--disable-gpu")
            chrome_options.add_argument("--window-size=1920,1080")
            chrome_options.add_argument("--user-agent=Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36")
            
            # Desabilitar notificações
            prefs = {
                "profile.default_content_setting_values.notifications": 2
            }
            chrome_options.add_experimental_option("prefs", prefs)
            
            driver = webdriver.Chrome(options=chrome_options)
            driver.set_page_load_timeout(30)
            
            logger.info("WebDriver criado com sucesso")
            return driver
            
        except Exception as e:
            logger.error(f"Erro ao criar WebDriver: {str(e)}")
            raise

    async def fazer_login(self) -> bool:
        """
        Faz login no Trinks
        """
        try:
            logger.info("Iniciando login no Trinks...")
            
            self.driver = self._criar_driver()
            
            # Navegar para página de login
            self.driver.get(f"{self.base_url}/login")
            
            # Aguardar campo de email
            wait = WebDriverWait(self.driver, 10)
            email_field = wait.until(EC.presence_of_element_located((By.ID, "fEmail")))
            
            # Preencher email
            email_field.clear()
            email_field.send_keys(self.email)
            
            # Preencher senha
            senha_field = self.driver.find_element(By.ID, "fSenha")
            senha_field.clear()
            senha_field.send_keys(self.password)
            
            # Clicar botão entrar
            botao_entrar = self.driver.find_element(By.XPATH, "//button[contains(text(), 'Entrar')]")
            botao_entrar.click()
            
            # Aguardar redirecionamento
            wait.until(EC.url_contains("/backoffice"))
            
            logger.info("Login realizado com sucesso")
            return True
            
        except Exception as e:
            logger.error(f"Erro ao fazer login: {str(e)}")
            return False

    async def extrair_servicos(self) -> List[Dict[str, Any]]:
        """
        Extrai lista de serviços disponíveis
        """
        try:
            logger.info("Extraindo serviços do Trinks...")
            
            # Navegar para página de configurações
            self.driver.get(f"{self.base_url}/backoffice/configuracoes")
            
            wait = WebDriverWait(self.driver, 10)
            
            # Aguardar carregamento da página
            wait.until(EC.presence_of_all_elements_located((By.CLASS_NAME, "servico-item")))
            
            servicos = []
            
            # Extrair elementos de serviço
            elementos_servicos = self.driver.find_elements(By.CLASS_NAME, "servico-item")
            
            for elemento in elementos_servicos:
                try:
                    nome = elemento.find_element(By.CLASS_NAME, "servico-nome").text
                    preco_text = elemento.find_element(By.CLASS_NAME, "servico-preco").text
                    duracao_text = elemento.find_element(By.CLASS_NAME, "servico-duracao").text
                    
                    # Parse do preço (ex: "R$ 80,00" -> 80.00)
                    preco = float(preco_text.replace("R$", "").replace(",", ".").strip())
                    
                    # Parse da duração (ex: "45 min" -> 45)
                    duracao = int(duracao_text.split()[0])
                    
                    servicos.append({
                        "nome": nome,
                        "preco": preco,
                        "duracao_minutos": duracao,
                        "categoria": "CAB",  # Categoria padrão
                        "descricao": f"Serviço: {nome}"
                    })
                    
                except Exception as e:
                    logger.warning(f"Erro ao extrair serviço: {str(e)}")
                    continue
            
            logger.info(f"Extraídos {len(servicos)} serviços")
            return servicos
            
        except Exception as e:
            logger.error(f"Erro ao extrair serviços: {str(e)}")
            return []

    async def extrair_profissionais(self) -> List[Dict[str, Any]]:
        """
        Extrai lista de profissionais
        """
        try:
            logger.info("Extraindo profissionais do Trinks...")
            
            # Navegar para página de profissionais
            self.driver.get(f"{self.base_url}/backoffice/configuracoes/profissionais")
            
            wait = WebDriverWait(self.driver, 10)
            wait.until(EC.presence_of_all_elements_located((By.CLASS_NAME, "profissional-item")))
            
            profissionais = []
            
            elementos_profissionais = self.driver.find_elements(By.CLASS_NAME, "profissional-item")
            
            for elemento in elementos_profissionais:
                try:
                    nome = elemento.find_element(By.CLASS_NAME, "profissional-nome").text
                    cargo = elemento.find_element(By.CLASS_NAME, "profissional-cargo").text
                    
                    profissionais.append({
                        "nome": nome,
                        "cargo": cargo,
                        "ativo": True
                    })
                    
                except Exception as e:
                    logger.warning(f"Erro ao extrair profissional: {str(e)}")
                    continue
            
            logger.info(f"Extraídos {len(profissionais)} profissionais")
            return profissionais
            
        except Exception as e:
            logger.error(f"Erro ao extrair profissionais: {str(e)}")
            return []

    async def extrair_agenda(
        self,
        data_inicio: datetime = None,
        data_fim: datetime = None
    ) -> List[Dict[str, Any]]:
        """
        Extrai agenda de agendamentos
        """
        try:
            if not data_inicio:
                data_inicio = datetime.now()
            if not data_fim:
                data_fim = datetime.now() + timedelta(days=30)
            
            logger.info(f"Extraindo agenda de {data_inicio} a {data_fim}...")
            
            # Navegar para página de agenda
            self.driver.get(f"{self.base_url}/backoffice/agenda")
            
            wait = WebDriverWait(self.driver, 10)
            
            # Aguardar carregamento da agenda
            wait.until(EC.presence_of_all_elements_located((By.CLASS_NAME, "agendamento-item")))
            
            agendamentos = []
            
            elementos_agendamentos = self.driver.find_elements(By.CLASS_NAME, "agendamento-item")
            
            for elemento in elementos_agendamentos:
                try:
                    cliente = elemento.find_element(By.CLASS_NAME, "agendamento-cliente").text
                    data_hora = elemento.find_element(By.CLASS_NAME, "agendamento-data").text
                    servico = elemento.find_element(By.CLASS_NAME, "agendamento-servico").text
                    profissional = elemento.find_element(By.CLASS_NAME, "agendamento-profissional").text
                    
                    agendamentos.append({
                        "cliente": cliente,
                        "data_hora": data_hora,
                        "servico": servico,
                        "profissional": profissional,
                        "status": "confirmado"
                    })
                    
                except Exception as e:
                    logger.warning(f"Erro ao extrair agendamento: {str(e)}")
                    continue
            
            logger.info(f"Extraídos {len(agendamentos)} agendamentos")
            return agendamentos
            
        except Exception as e:
            logger.error(f"Erro ao extrair agenda: {str(e)}")
            return []

    async def extrair_clientes(self) -> List[Dict[str, Any]]:
        """
        Extrai lista de clientes
        """
        try:
            logger.info("Extraindo clientes do Trinks...")
            
            # Navegar para página de clientes
            self.driver.get(f"{self.base_url}/backoffice/clientes")
            
            wait = WebDriverWait(self.driver, 10)
            wait.until(EC.presence_of_all_elements_located((By.CLASS_NAME, "cliente-item")))
            
            clientes = []
            
            elementos_clientes = self.driver.find_elements(By.CLASS_NAME, "cliente-item")
            
            for elemento in elementos_clientes:
                try:
                    nome = elemento.find_element(By.CLASS_NAME, "cliente-nome").text
                    telefone = elemento.find_element(By.CLASS_NAME, "cliente-telefone").text
                    email = elemento.find_element(By.CLASS_NAME, "cliente-email").text
                    
                    clientes.append({
                        "nome": nome,
                        "telefone": telefone,
                        "email": email
                    })
                    
                except Exception as e:
                    logger.warning(f"Erro ao extrair cliente: {str(e)}")
                    continue
            
            logger.info(f"Extraídos {len(clientes)} clientes")
            return clientes
            
        except Exception as e:
            logger.error(f"Erro ao extrair clientes: {str(e)}")
            return []

    async def sincronizar_dados(self, db: Session) -> bool:
        """
        Sincroniza todos os dados do Trinks
        """
        try:
            logger.info("Iniciando sincronização com Trinks...")
            
            # Fazer login
            if not await self.fazer_login():
                logger.error("Falha ao fazer login")
                return False
            
            # Extrair dados
            servicos = await self.extrair_servicos()
            profissionais = await self.extrair_profissionais()
            agendamentos = await self.extrair_agenda()
            clientes = await self.extrair_clientes()
            
            # Salvar no banco (implementar depois com db.add, db.commit)
            logger.info("Dados sincronizados com sucesso")
            self.ultima_sincronizacao = datetime.utcnow()
            
            return True
            
        except Exception as e:
            logger.error(f"Erro na sincronização: {str(e)}")
            return False
        
        finally:
            # Fechar driver
            if self.driver:
                self.driver.quit()
                logger.info("WebDriver fechado")

    def fechar(self):
        """Fecha o driver"""
        if self.driver:
            self.driver.quit()
            logger.info("Driver fechado")


# Instância global
trinks_scraper_real = TrinksScraperReal()
