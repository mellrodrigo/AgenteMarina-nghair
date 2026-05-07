"""
Teste local dos imports e funcionamento basico da Marina
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

print("Testando imports...")

try:
    from app.models.database import SessionLocal, criar_tabelas, Cliente
    print("OK - database")
except Exception as e:
    print("ERRO database:", e)
    sys.exit(1)

try:
    from app.services.cliente_service import cliente_service
    print("OK - cliente_service")
except Exception as e:
    print("ERRO cliente_service:", e)
    sys.exit(1)

try:
    from app.services.ai_core import ai_core
    print("OK - ai_core")
except Exception as e:
    print("ERRO ai_core:", e)
    sys.exit(1)

try:
    from app.main import app
    print("OK - Flask app")
    rotas = [r.rule for r in app.url_map.iter_rules()]
    print("Rotas:", rotas)
except Exception as e:
    print("ERRO main:", e)
    sys.exit(1)

# Testar banco de dados
print("\nTestando banco de dados...")
try:
    criar_tabelas()
    db = SessionLocal()
    cliente = cliente_service.buscar_ou_criar_cliente(db, "5511999999999", "Teste")
    print("OK - cliente criado:", cliente.nome, cliente.telefone)
    db.close()
except Exception as e:
    print("ERRO banco:", e)

# Testar AI (sem chamar API real)
print("\nTestando classificacao de intencao...")
intencao = ai_core._classificar_intencao("quero agendar um horario")
print("OK - intencao:", intencao)

intencao2 = ai_core._classificar_intencao("quanto custa a escova?")
print("OK - intencao:", intencao2)

print("\nTodos os testes passaram!")
