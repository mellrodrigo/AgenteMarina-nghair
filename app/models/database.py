"""
Modelos de banco de dados para Marina
"""
from sqlalchemy import create_engine, Column, Integer, String, DateTime, Text, Float, Boolean, ForeignKey, text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from datetime import datetime
import os

# Configuração do banco de dados
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./data/marina.db")

# Criar engine
if DATABASE_URL.startswith("sqlite"):
    engine = create_engine(
        DATABASE_URL,
        connect_args={"check_same_thread": False},
        echo=False
    )
else:
    engine = create_engine(DATABASE_URL, echo=False)

# Criar session
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base para modelos
Base = declarative_base()


class Cliente(Base):
    """Modelo para armazenar informações de clientes"""
    __tablename__ = "clientes"

    id = Column(Integer, primary_key=True, index=True)
    nome = Column(String(255), nullable=False)
    telefone = Column(String(20), unique=True, index=True, nullable=False)
    email = Column(String(255), nullable=True)
    
    # Dados de controle
    data_criacao = Column(DateTime, default=datetime.utcnow)
    ultima_interacao = Column(DateTime, default=datetime.utcnow)
    
    # Preferências
    profissional_preferido = Column(String(255), nullable=True)
    servico_preferido = Column(String(255), nullable=True)
    horario_preferido = Column(String(50), nullable=True)
    sexo = Column(String(10), nullable=True)  # M ou F
    
    # Notas personalizadas
    notas = Column(Text, nullable=True)
    
    # Relacionamentos
    conversas = relationship("Conversa", back_populates="cliente", cascade="all, delete-orphan")
    agendamentos = relationship("Agendamento", back_populates="cliente", cascade="all, delete-orphan")
    memoria = relationship("MemoriaIA", back_populates="cliente", cascade="all, delete-orphan")


class Conversa(Base):
    """Modelo para armazenar histórico de conversas"""
    __tablename__ = "conversas"

    id = Column(Integer, primary_key=True, index=True)
    cliente_id = Column(Integer, ForeignKey("clientes.id"), nullable=False)
    
    # Conteúdo da conversa
    mensagem_usuario = Column(Text, nullable=False)
    resposta_marina = Column(Text, nullable=False)
    
    # Contexto
    intencao = Column(String(100), nullable=True)  # agendamento, consulta, etc
    contexto = Column(Text, nullable=True)  # JSON com contexto
    
    # Controle
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)
    
    # Relacionamento
    cliente = relationship("Cliente", back_populates="conversas")


class Agendamento(Base):
    """Modelo para armazenar agendamentos"""
    __tablename__ = "agendamentos"

    id = Column(Integer, primary_key=True, index=True)
    cliente_id = Column(Integer, ForeignKey("clientes.id"), nullable=False)
    
    # Detalhes do agendamento
    data = Column(DateTime, nullable=False, index=True)
    servico = Column(String(255), nullable=False)
    profissional = Column(String(255), nullable=False)
    valor = Column(Float, nullable=True)
    
    # Status
    status = Column(String(50), default="confirmado")  # confirmado, cancelado, realizado
    
    # Notas
    notas = Column(Text, nullable=True)
    
    # Controle
    data_criacao = Column(DateTime, default=datetime.utcnow)
    data_atualizacao = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relacionamento
    cliente = relationship("Cliente", back_populates="agendamentos")


class Servico(Base):
    """Modelo para armazenar serviços do salão"""
    __tablename__ = "servicos"

    id = Column(Integer, primary_key=True, index=True)
    
    # Informações do serviço
    nome = Column(String(255), unique=True, nullable=False, index=True)
    descricao = Column(Text, nullable=True)
    categoria = Column(String(100), nullable=False)  # CAB, CIL, DEP, etc
    
    # Detalhes
    preco = Column(Float, nullable=False)
    duracao_minutos = Column(Integer, nullable=False)
    
    # Status
    ativo = Column(Boolean, default=True)
    
    # Controle
    data_atualizacao = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class Profissional(Base):
    """Modelo para armazenar profissionais do salão"""
    __tablename__ = "profissionais"

    id = Column(Integer, primary_key=True, index=True)
    
    # Informações
    nome = Column(String(255), unique=True, nullable=False, index=True)
    cargo = Column(String(255), nullable=False)  # Cabeleireiro, Manicure, etc
    
    # Status
    ativo = Column(Boolean, default=True)
    
    # Controle
    data_atualizacao = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class MemoriaIA(Base):
    """Modelo para armazenar memória de aprendizado sobre clientes"""
    __tablename__ = "memoria_ia"

    id = Column(Integer, primary_key=True, index=True)
    cliente_id = Column(Integer, ForeignKey("clientes.id"), nullable=False)
    
    # Tipo de memória
    tipo = Column(String(100), nullable=False)  # preferencia, feedback, comportamento, etc
    
    # Conteúdo
    conteudo = Column(Text, nullable=False)  # JSON com dados
    
    # Relevância
    relevancia = Column(Float, default=1.0)  # 0-1, para priorizar memórias
    
    # Controle
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)
    
    # Relacionamento
    cliente = relationship("Cliente", back_populates="memoria")


class ConfiguracaoTrinks(Base):
    """Modelo para armazenar configurações de sincronização com Trinks"""
    __tablename__ = "configuracao_trinks"

    id = Column(Integer, primary_key=True, index=True)
    
    # Informações de sincronização
    ultima_sincronizacao = Column(DateTime, nullable=True)
    proxima_sincronizacao = Column(DateTime, nullable=True)
    
    # Status
    status = Column(String(50), default="pendente")  # pendente, sincronizando, sucesso, erro
    mensagem_erro = Column(Text, nullable=True)
    
    # Controle
    data_criacao = Column(DateTime, default=datetime.utcnow)
    data_atualizacao = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


# Função para criar todas as tabelas
def criar_tabelas():
    """Cria todas as tabelas no banco de dados e aplica migrações pendentes"""
    Base.metadata.create_all(bind=engine)
    # Migração: adiciona colunas novas que podem não existir em bancos antigos
    _migrar_colunas()


# Função para obter sessão do banco
def _migrar_colunas():
    """Adiciona colunas novas em tabelas já existentes (sem recriar o banco)."""
    migracoes = [
        "ALTER TABLE clientes ADD COLUMN sexo VARCHAR(10)",
    ]
    with engine.connect() as conn:
        for sql in migracoes:
            try:
                conn.execute(text(sql))
                conn.commit()
            except Exception:
                pass  # coluna já existe


def get_db():
    """Dependency para obter sessão do banco de dados"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
