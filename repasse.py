"""
repasse.py
----------
Workflow 3: quando a Lara agenda uma call com sucesso,
esse módulo monta e envia a ficha completa do lead para o Pedro (fechador).
"""

from database import criar_ficha_repasse, marcar_ficha_enviada, buscar_agendamento_por_lead
from whatsapp import enviar_mensagem
from config import WHATSAPP_PEDRO


def montar_ficha(lead: dict, agendamento: dict | None) -> str:
    """
    Monta o texto formatado da ficha de repasse.
    Usa os mesmos emojis e estrutura definidos na documentação.
    """
    data_call = agendamento["data_call"] if agendamento else "A confirmar"
    link_call = agendamento.get("link_call", "A definir") if agendamento else "A definir"

    ficha = f"""📋 *FICHA DE REPASSE — Pedro*

👤 *Lead:* {lead.get('nome', 'Sem nome')}
📱 *WhatsApp:* {lead.get('whatsapp')}
📅 *Call agendada:* {data_call}
🔗 *Link:* {link_call}

━━━━ QUALIFICAÇÃO ━━━━
💳 *Gasto mensal:* {lead.get('gasto_mensal') or 'Não informado'}
💳 *Cartões atuais:* {lead.get('cartoes_atuais') or 'Não informado'}
✈️ *Destino desejado:* {lead.get('destino_viagem') or 'Não informado'}
🎫 *Milhas atuais:* {lead.get('milhas_atuais') or 'Não informado'}

━━━━ CONTEXTO ━━━━
🌡 *Temperatura:* {lead.get('temperatura', 'INDEFINIDO')}
📝 *Obs:* {lead.get('observacoes') or 'Nenhuma'}

Boa call! 🚀"""

    return ficha


def executar_repasse(lead: dict) -> bool:
    """
    Executa o Workflow 3 completo:
    1. Busca o agendamento do lead
    2. Registra a ficha no banco
    3. Monta o texto da ficha
    4. Envia para o Pedro via WhatsApp
    5. Marca como enviada

    Retorna True se enviou com sucesso, False se houve erro.
    """
    try:
        # Busca o agendamento mais recente desse lead
        agendamento = buscar_agendamento_por_lead(lead["id"])

        # Salva a ficha no banco
        ficha = criar_ficha_repasse(lead, agendamento)

        # Monta e envia a mensagem para o Pedro
        texto = montar_ficha(lead, agendamento)
        enviar_mensagem(WHATSAPP_PEDRO, texto)

        # Marca como enviada
        marcar_ficha_enviada(ficha["id"])

        print(f"[REPASSE] Ficha enviada para Pedro — lead: {lead.get('nome')}")
        return True

    except Exception as e:
        print(f"[REPASSE] Erro ao enviar ficha: {e}")
        return False
