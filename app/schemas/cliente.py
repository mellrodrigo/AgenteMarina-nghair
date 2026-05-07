"""
Schemas de Cliente - sem pydantic para compatibilidade com Python 3.6
"""

class ClienteCreate:
    def __init__(self, telefone, nome=None, email=None):
        self.telefone = telefone
        self.nome = nome or ""
        self.email = email or ""

class ClienteUpdate:
    def __init__(self, nome=None, email=None, preferencias=None):
        self.nome = nome
        self.email = email
        self.preferencias = preferencias or {}
