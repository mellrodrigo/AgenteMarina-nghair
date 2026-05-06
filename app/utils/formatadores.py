"""
Utilitários para formatação de mensagens e dados
"""
from datetime import datetime
from typing import List, Dict, Any


class FormatadorMensagens:
    """Classe para formatar mensagens para WhatsApp"""

    @staticmethod
    def formatar_servicos(servicos: List[Dict[str, Any]]) -> str:
        """Formata lista de serviços para WhatsApp"""
        if not servicos:
            return "Desculpe, não consegui carregar os serviços no momento."
        
        mensagem = "✂️ *Nossos Serviços:*\n\n"
        
        for i, servico in enumerate(servicos, 1):
            nome = servico.get("nome", "")
            preco = servico.get("preco", 0)
            duracao = servico.get("duracao_minutos", 0)
            
            mensagem += f"{i}. *{nome}*\n"
            mensagem += f"   💰 R$ {preco:.2f} | ⏱️ {duracao} min\n\n"
        
        mensagem += "Qual serviço você gostaria de agendar? 😊"
        return mensagem

    @staticmethod
    def formatar_profissionais(profissionais: List[Dict[str, Any]]) -> str:
        """Formata lista de profissionais para WhatsApp"""
        if not profissionais:
            return "Desculpe, não consegui carregar os profissionais no momento."
        
        mensagem = "👩‍💼 *Nossos Profissionais:*\n\n"
        
        for i, prof in enumerate(profissionais, 1):
            nome = prof.get("nome", "")
            cargo = prof.get("cargo", "")
            
            mensagem += f"{i}. *{nome}* - {cargo}\n"
        
        mensagem += "\nQual profissional você prefere? 😊"
        return mensagem

    @staticmethod
    def formatar_horarios(horarios: List[str], data: str) -> str:
        """Formata lista de horários para WhatsApp"""
        if not horarios:
            return f"Desculpe, não há horários disponíveis para {data}."
        
        mensagem = f"🕐 *Horários Disponíveis para {data}:*\n\n"
        
        # Agrupar horários em linhas de 3
        for i in range(0, len(horarios), 3):
            grupo = horarios[i:i+3]
            mensagem += " | ".join(grupo) + "\n"
        
        mensagem += "\nQual horário você prefere? 😊"
        return mensagem

    @staticmethod
    def formatar_confirmacao_agendamento(agendamento: Dict[str, Any]) -> str:
        """Formata confirmação de agendamento"""
        return f"""
✅ *Agendamento Confirmado!*

📅 Data: {agendamento.get('data')}
🕐 Hora: {agendamento.get('horario')}
✂️ Serviço: {agendamento.get('servico')}
👩‍💼 Profissional: {agendamento.get('profissional')}
💰 Valor: R$ {agendamento.get('valor', 'A confirmar')}

Você receberá um lembrete 24h antes do seu agendamento! 📱

Precisa de algo mais? 😊
        """

    @staticmethod
    def formatar_proximos_agendamentos(agendamentos: List[Dict[str, Any]]) -> str:
        """Formata próximos agendamentos"""
        if not agendamentos:
            return "Você não tem agendamentos próximos. Quer agendar algo? 😊"
        
        mensagem = "📅 *Seus Próximos Agendamentos:*\n\n"
        
        for i, ag in enumerate(agendamentos, 1):
            data = ag.get('data', '').split('T')[0]  # Pegar apenas a data
            hora = ag.get('data', '').split('T')[1][:5] if 'T' in ag.get('data', '') else ''
            servico = ag.get('servico', '')
            profissional = ag.get('profissional', '')
            
            mensagem += f"{i}. *{servico}*\n"
            mensagem += f"   📆 {data} às {hora}\n"
            mensagem += f"   👩‍💼 {profissional}\n\n"
        
        mensagem += "Precisa cancelar ou remarcar algum? 😊"
        return mensagem

    @staticmethod
    def formatar_recomendacao(recomendacao: str) -> str:
        """Formata recomendação"""
        return f"💡 *Minha Recomendação:*\n\n{recomendacao}\n\nQuer agendar? 😊"

    @staticmethod
    def formatar_menu_principal() -> str:
        """Formata menu principal"""
        return """
👋 *Olá! Bem-vinda ao NGHair!*

Sou a Marina, sua assistente virtual. Como posso ajudar você hoje?

1️⃣ 📅 Agendar um serviço
2️⃣ 📋 Ver meus agendamentos
3️⃣ ✂️ Conhecer nossos serviços
4️⃣ 👩‍💼 Conhecer nossa equipe
5️⃣ 💰 Consultar preços

Apenas responda com o número! 😊
        """

    @staticmethod
    def formatar_erro() -> str:
        """Formata mensagem de erro"""
        return """
😅 Desculpe, não consegui entender sua mensagem.

Pode tentar novamente ou escolher uma das opções:
1️⃣ Agendar
2️⃣ Ver agendamentos
3️⃣ Serviços
4️⃣ Equipe
5️⃣ Preços

Estou aqui para ajudar! 😊
        """

    @staticmethod
    def formatar_saudacao(nome: str = "Cliente") -> str:
        """Formata saudação personalizada"""
        hora = datetime.now().hour
        
        if hora < 12:
            saudacao = "Bom dia"
        elif hora < 18:
            saudacao = "Boa tarde"
        else:
            saudacao = "Boa noite"
        
        return f"{saudacao}, {nome}! 👋\n\nBem-vinda ao NGHair! Como posso ajudar? 😊"


class FormatadorDados:
    """Classe para formatar dados"""

    @staticmethod
    def formatar_telefone(telefone: str) -> str:
        """Formata número de telefone"""
        # Remove caracteres especiais
        telefone_limpo = ''.join(c for c in telefone if c.isdigit())
        
        # Formata como (XX) XXXXX-XXXX
        if len(telefone_limpo) == 11:
            return f"({telefone_limpo[:2]}) {telefone_limpo[2:7]}-{telefone_limpo[7:]}"
        
        return telefone_limpo

    @staticmethod
    def formatar_data(data: datetime, formato: str = "%d/%m/%Y") -> str:
        """Formata data"""
        return data.strftime(formato)

    @staticmethod
    def formatar_hora(data: datetime) -> str:
        """Formata hora"""
        return data.strftime("%H:%M")

    @staticmethod
    def formatar_moeda(valor: float) -> str:
        """Formata valor em moeda"""
        return f"R$ {valor:.2f}".replace(".", ",")
