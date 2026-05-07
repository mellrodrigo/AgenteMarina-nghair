"""
Schemas de WhatsApp - sem pydantic para compatibilidade com Python 3.6
"""

class MensagemWhatsApp:
    def __init__(self, telefone, mensagem):
        self.telefone = telefone
        self.mensagem = mensagem
