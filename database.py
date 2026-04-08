from supabase import create_client
from config import SUPABASE_URL, SUPABASE_KEY
from datetime import datetime

# Inicializa o cliente Supabase
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)


# ─────────────────────────────────────────────
# LEADS
# ─────────────────────────────────────────────

def buscar_lead_por_whatsapp(whatsapp: str):
    """Busca um lead pelo número de WhatsApp."""
    resultado = (
        supabase.table("leads")
        .select("*")
        .eq("whatsapp", whatsapp)
        .single()
        .execute()
    )
    return resultado.data


def criar_lead(whatsapp: str, nome: str = ""):
    """Cria um novo lead no banco."""
    resultado = (
        supabase.table("leads")
        .insert({"whatsapp": whatsapp, "nome": nome, "status": "novo", "etapa": "interesse"})
        .execute()
    )
    return resultado.data[0] if resultado.data else None


def atualizar_lead(lead_id: str, dados: dict):
    """Atualiza dados de um lead existente."""
    dados["updated_at"] = datetime.utcnow().isoformat()
    resultado = (
        supabase.table("leads")
        .update(dados)
        .eq("id", lead_id)
        .execute()
    )
    return resultado.data


def buscar_ou_criar_lead(whatsapp: str, nome: str = ""):
    """Busca o lead pelo WhatsApp. Se não existir, cria um novo."""
    lead = buscar_lead_por_whatsapp(whatsapp)
    if not lead:
        lead = criar_lead(whatsapp, nome)
    return lead


# ─────────────────────────────────────────────
# MENSAGENS
# ─────────────────────────────────────────────

def salvar_mensagem(lead_id: str, papel: str, conteudo: str):
    """Salva uma mensagem no histórico do lead.
    papel: 'usuario' ou 'assistente'
    """
    supabase.table("mensagens").insert({
        "lead_id": lead_id,
        "papel": papel,
        "conteudo": conteudo,
    }).execute()


def buscar_historico(lead_id: str, limite: int = 20):
    """Busca o histórico de mensagens de um lead."""
    resultado = (
        supabase.table("mensagens")
        .select("papel, conteudo")
        .eq("lead_id", lead_id)
        .order("created_at", desc=False)
        .limit(limite)
        .execute()
    )
    return resultado.data or []


# ─────────────────────────────────────────────
# FOLLOW-UPS
# ─────────────────────────────────────────────

def criar_followup(lead_id: str, mensagem: str, agendado_para: str):
    """Cria um follow-up agendado para o lead."""
    supabase.table("followups").insert({
        "lead_id": lead_id,
        "mensagem": mensagem,
        "agendado_para": agendado_para,
        "status": "pendente",
    }).execute()


def buscar_followups_pendentes():
    """Busca todos os follow-ups que devem ser enviados agora."""
    agora = datetime.utcnow().isoformat()
    resultado = (
        supabase.table("followups")
        .select("*, leads(whatsapp, nome)")
        .eq("status", "pendente")
        .lte("agendado_para", agora)
        .execute()
    )
    return resultado.data or []


def marcar_followup_enviado(followup_id: str):
    """Marca um follow-up como enviado."""
    supabase.table("followups").update({"status": "enviado"}).eq("id", followup_id).execute()


# ─────────────────────────────────────────────
# FICHAS DE REPASSE
# ─────────────────────────────────────────────

def salvar_ficha_repasse(lead_id: str, resumo: str):
    """Salva a ficha de repasse gerada para o Pedro."""
    resultado = (
        supabase.table("fichas_repasse")
        .insert({"lead_id": lead_id, "resumo": resumo})
        .execute()
    )
    return resultado.data[0] if resultado.data else None
