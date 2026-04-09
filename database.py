"""
database.py
-----------
Todas as operações com o banco de dados Supabase.
O Supabase tem uma API REST — fazemos chamadas HTTP simples para criar,
buscar e atualizar os dados.
"""

import httpx
from config import SUPABASE_URL, SUPABASE_KEY

# Cabeçalhos que precisamos enviar em toda requisição ao Supabase
HEADERS = {
    "apikey": SUPABASE_KEY,
    "Authorization": f"Bearer {SUPABASE_KEY}",
    "Content-Type": "application/json",
    "Prefer": "return=representation",  # faz o Supabase retornar o registro criado/atualizado
}


def _url(tabela: str) -> str:
    """Monta a URL completa de uma tabela."""
    return f"{SUPABASE_URL}/{tabela}"


# ─────────────────────────────────────────────
# LEADS
# ─────────────────────────────────────────────

def upsert_lead(whatsapp: str, nome: str) -> dict:
    """
    Cria um lead novo ou retorna o existente.
    'Upsert' = insert + update: se já existe, não duplica.
    """
    payload = {
        "whatsapp": whatsapp,
        "nome": nome,
        "status": "NOVO",
        "etapa": "ABERTURA",
        "temperatura": "INDEFINIDO",
        "tentativas_followup": 0,
        "bloqueado_followup": False,
    }
    resp = httpx.post(
        _url("leads"),
        headers={**HEADERS, "Prefer": "resolution=ignore-duplicates,return=representation"},
        json=payload,
        timeout=10,
    )
    resp.raise_for_status()
    dados = resp.json()
    return dados[0] if dados else buscar_lead_por_whatsapp(whatsapp)


def buscar_lead_por_whatsapp(whatsapp: str) -> dict | None:
    """Busca um lead pelo número de WhatsApp."""
    resp = httpx.get(
        _url("leads"),
        headers=HEADERS,
        params={"whatsapp": f"eq.{whatsapp}", "limit": "1"},
        timeout=10,
    )
    resp.raise_for_status()
    dados = resp.json()
    return dados[0] if dados else None


def atualizar_lead(lead_id: str, campos: dict) -> dict:
    """
    Atualiza campos específicos de um lead.
    Exemplo: atualizar_lead(id, {"etapa": "PERGUNTA_1", "temperatura": "QUENTE"})
    """
    resp = httpx.patch(
        _url("leads"),
        headers=HEADERS,
        params={"id": f"eq.{lead_id}"},
        json=campos,
        timeout=10,
    )
    resp.raise_for_status()
    dados = resp.json()
    return dados[0] if dados else {}


def buscar_leads_para_followup() -> list[dict]:
    """
    Busca leads inativos há mais de 1 hora que ainda podem receber follow-up.
    Condições:
    - bloqueado_followup = false
    - tentativas_followup < 2
    - ultima_interacao há mais de 1 hora
    - status não é AGENDADO nem DESCARTADO
    """
    resp = httpx.get(
        _url("leads"),
        headers=HEADERS,
        params={
            "bloqueado_followup": "eq.false",
            "tentativas_followup": "lt.2",
            "ultima_interacao": "lt.now()-interval '1 hour'",
            "status": "not.in.(AGENDADO,DESCARTADO)",
        },
        timeout=10,
    )
    resp.raise_for_status()
    return resp.json()


# ─────────────────────────────────────────────
# MENSAGENS
# ─────────────────────────────────────────────

def salvar_mensagem(lead_id: str, direcao: str, conteudo: str, etapa: str, evolution_msg_id: str = None) -> dict:
    """
    Salva uma mensagem no histórico.
    direcao: "RECEBIDA" ou "ENVIADA"
    """
    payload = {
        "lead_id": lead_id,
        "direcao": direcao,
        "conteudo": conteudo,
        "etapa_no_momento": etapa,
    }
    if evolution_msg_id:
        payload["evolution_msg_id"] = evolution_msg_id

    resp = httpx.post(_url("mensagens"), headers=HEADERS, json=payload, timeout=10)
    resp.raise_for_status()
    return resp.json()[0]


def buscar_historico(lead_id: str, limite: int = 10) -> list[dict]:
    """Busca as últimas N mensagens do lead para passar como contexto ao GPT."""
    resp = httpx.get(
        _url("mensagens"),
        headers=HEADERS,
        params={
            "lead_id": f"eq.{lead_id}",
            "order": "created_at.desc",
            "limit": str(limite),
        },
        timeout=10,
    )
    resp.raise_for_status()
    # Inverte para ordem cronológica (mais antiga primeiro)
    return list(reversed(resp.json()))


# ─────────────────────────────────────────────
# AGENDAMENTOS
# ─────────────────────────────────────────────

def criar_agendamento(lead_id: str, data_call: str, link_call: str = "") -> dict:
    """Cria um novo agendamento de call."""
    payload = {
        "lead_id": lead_id,
        "data_call": data_call,
        "link_call": link_call,
        "status": "AGENDADO",
    }
    resp = httpx.post(_url("agendamentos"), headers=HEADERS, json=payload, timeout=10)
    resp.raise_for_status()
    return resp.json()[0]


def buscar_agendamento_por_lead(lead_id: str) -> dict | None:
    """Busca o agendamento mais recente de um lead."""
    resp = httpx.get(
        _url("agendamentos"),
        headers=HEADERS,
        params={
            "lead_id": f"eq.{lead_id}",
            "order": "created_at.desc",
            "limit": "1",
        },
        timeout=10,
    )
    resp.raise_for_status()
    dados = resp.json()
    return dados[0] if dados else None


# ─────────────────────────────────────────────
# FICHAS DE REPASSE
# ─────────────────────────────────────────────

def criar_ficha_repasse(lead: dict, agendamento: dict | None) -> dict:
    """Registra a ficha de repasse no banco."""
    payload = {
        "lead_id": lead["id"],
        "agendamento_id": agendamento["id"] if agendamento else None,
        "nome": lead.get("nome"),
        "whatsapp": lead.get("whatsapp"),
        "data_call": agendamento["data_call"] if agendamento else None,
        "gasto_mensal": lead.get("gasto_mensal"),
        "cartoes": lead.get("cartoes_atuais"),
        "temperatura": lead.get("temperatura"),
        "enviada_ao_fechador": False,
    }
    resp = httpx.post(_url("fichas_repasse"), headers=HEADERS, json=payload, timeout=10)
    resp.raise_for_status()
    return resp.json()[0]


def marcar_ficha_enviada(ficha_id: str) -> None:
    """Marca a ficha como enviada ao fechador."""
    httpx.patch(
        _url("fichas_repasse"),
        headers=HEADERS,
        params={"id": f"eq.{ficha_id}"},
        json={"enviada_ao_fechador": True},
        timeout=10,
    ).raise_for_status()


# ─────────────────────────────────────────────
# FOLLOWUPS
# ─────────────────────────────────────────────

def registrar_followup(lead_id: str, tipo: str) -> dict:
    """Registra que um follow-up foi disparado."""
    payload = {
        "lead_id": lead_id,
        "tipo": tipo,  # "PRIMEIRO_FOLLOWUP" ou "SEGUNDO_FOLLOWUP"
        "disparado": True,
    }
    resp = httpx.post(_url("followups"), headers=HEADERS, json=payload, timeout=10)
    resp.raise_for_status()
    return resp.json()[0]
