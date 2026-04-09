"""
repasse.py — Gera e envia ficha de repasse para o Caio (fechador).
O cliente recebe apenas a confirmação, enviada pelo agent.py.
"""

from database import criar_ficha_repasse, marcar_ficha_enviada, buscar_agendamento_por_lead
from whatsapp import enviar_mensagem
from config import WHATSAPP_PEDRO  # variável mantém o nome WHATSAPP_PEDRO no config


def montar_ficha(lead: dict, agendamento: dict | None) -> str:
    """Monta o texto da ficha que vai para o Caio."""
    data_call = agendamento.get("data_call") if agendamento else "A confirmar"
    link_call = agendamento.get("link_call", "A definir") if agendamento else "A definir"

    return f"""📋 *FICHA DE REPASSE — Caio*

👤 *Lead:* {lead.get("nome") or "Sem nome"}
📱 *WhatsApp:* {lead.get("whatsapp")}
📅 *Call agendada:* {data_call or "A confirmar"}
🔗 *Link:* {link_call or "A definir"}

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
    """
    Executa o repasse completo:
    1. Busca agendamento
    2. Salva ficha no banco
    3. Envia ficha SOMENTE para o Caio
    4. Marca como enviada
    """
    try:
        agendamento = buscar_agendamento_por_lead(lead["id"])
        ficha = criar_ficha_repasse(lead, agendamento)
        texto = montar_ficha(lead, agendamento)

        # ✅ Envia SOMENTE para o Caio
        enviar_mensagem(WHATSAPP_PEDRO, texto)
        marcar_ficha_enviada(ficha["id"])

        print(f"[Repasse] ✅ Ficha enviada para Caio — lead: {lead.get('nome')} | gasto: {lead.get('gasto_mensal')}")
        return True

    except Exception as e:
        print(f"[Repasse] ❌ Erro: {e}")
        return False
