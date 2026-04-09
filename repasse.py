"""
repasse.py — Gera e envia ficha de repasse para o Pedro quando call é agendada.
"""

from database import criar_ficha_repasse, marcar_ficha_enviada, buscar_agendamento_por_lead
from whatsapp import enviar_mensagem
from config import WHATSAPP_PEDRO


def montar_ficha(lead: dict, agendamento: dict | None) -> str:
    data_call = agendamento["data_call"] if agendamento else "A confirmar"
    link_call = agendamento.get("link_call", "A definir") if agendamento else "A definir"

    return f"""📋 *FICHA DE REPASSE — Pedro*

👤 *Lead:* {lead.get("nome") or "Sem nome"}
📱 *WhatsApp:* {lead.get("whatsapp")}
📅 *Call agendada:* {data_call}
🔗 *Link:* {link_call}

━━━━ QUALIFICAÇÃO ━━━━
💳 *Gasto mensal:* {lead.get("gasto_mensal") or "Não informado"}
💳 *Cartões atuais:* {lead.get("cartoes_atuais") or "Não informado"}
✈️ *Destino desejado:* {lead.get("destino_viagem") or "Não informado"}
🎫 *Milhas atuais:* {lead.get("milhas_atuais") or "Não informado"}

━━━━ CONTEXTO ━━━━
🌡 *Temperatura:* {lead.get("temperatura") or "INDEFINIDO"}
📝 *Obs:* {lead.get("observacoes") or "Nenhuma"}

Boa call! 🚀"""


def executar_repasse(lead: dict) -> bool:
    """Executa o repasse completo: salva ficha e envia para Pedro."""
    try:
        agendamento = buscar_agendamento_por_lead(lead["id"])
        ficha = criar_ficha_repasse(lead, agendamento)
        texto = montar_ficha(lead, agendamento)
        enviar_mensagem(WHATSAPP_PEDRO, texto)
        marcar_ficha_enviada(ficha["id"])
        print(f"[Repasse] Ficha enviada para Pedro — lead: {lead.get('nome')}")
        return True
    except Exception as e:
        print(f"[Repasse] Erro: {e}")
        return False
