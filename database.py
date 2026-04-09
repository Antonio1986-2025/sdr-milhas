"""
database.py — Todas as operações com o Supabase via REST API.
"""

import httpx
from config import SUPABASE_URL, SUPABASE_KEY

HEADERS = {
    "apikey": SUPABASE_KEY,
    "Authorization": f"Bearer {SUPABASE_KEY}",
    "Content-Type": "application/json",
    "Prefer": "return=representation",
}


def _url(tabela: str) -> str:
    return f"{SUPABASE_URL}/rest/v1/{tabela}"


# ─────────────────────────────────────────────
# LEADS
# ─────────────────────────────────────────────

def buscar_lead_por_whatsapp(whatsapp: str) -> dict | None:
    resp = httpx.get(
        _url("leads"),
        headers=HEADERS,
        params={"whatsapp": f"eq.{whatsapp}", "limit": "1"},
        timeout=10,
    )
    resp.raise_for_status()
    dados = resp.json()
    return dados[0] if dados else None


def criar_lead(whatsapp: str, nome: str = "") -> dict:
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


def buscar_ou_criar_lead(whatsapp: str, nome: str = "") -> dict:
    lead = buscar_lead_por_whatsapp(whatsapp)
    if not lead:
        lead = criar_lead(whatsapp, nome)
    return lead


def atualizar_lead(lead_id: str, campos: dict) -> dict:
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
    resp = httpx.get(
        _url("leads"),
        headers=HEADERS,
        params={
            "bloqueado_followup": "eq.false",
            "tentativas_followup": "lt.2",
            "status": "not.in.(AGENDADO,DESCARTADO)",
            "select": "*",
        },
        timeout=10,
    )
    resp.raise_for_status()
    return resp.json()


# ─────────────────────────────────────────────
# MENSAGENS
# ─────────────────────────────────────────────

def salvar_mensagem(lead_id: str, direcao: str, conteudo: str, etapa: str = "") -> dict:
    """direcao: RECEBIDA ou ENVIADA"""
    payload = {
        "lead_id": lead_id,
        "direcao": direcao,
        "conteudo": conteudo,
        "etapa_no_momento": etapa,
    }
    resp = httpx.post(_url("mensagens"), headers=HEADERS, json=payload, timeout=10)
    resp.raise_for_status()
    dados = resp.json()
    return dados[0] if dados else {}


def buscar_historico(lead_id: str, limite: int = 10) -> list[dict]:
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
    return list(reversed(resp.json()))


# ─────────────────────────────────────────────
# AGENDAMENTOS
# ─────────────────────────────────────────────

def criar_agendamento(lead_id: str, data_call: str = "", link_call: str = "") -> dict:
    payload = {
        "lead_id": lead_id,
        "data_call": data_call,
        "link_call": link_call,
        "status": "AGENDADO",
    }
    resp = httpx.post(_url("agendamentos"), headers=HEADERS, json=payload, timeout=10)
    resp.raise_for_status()
    dados = resp.json()
    return dados[0] if dados else {}


def buscar_agendamento_por_lead(lead_id: str) -> dict | None:
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
    dados = resp.json()
    return dados[0] if dados else {}


def marcar_ficha_enviada(ficha_id: str) -> None:
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
    payload = {
        "lead_id": lead_id,
        "tipo": tipo,
        "disparado": True,
    }
    resp = httpx.post(_url("followups"), headers=HEADERS, json=payload, timeout=10)
    resp.raise_for_status()
    dados = resp.json()
    return dados[0] if dados else {}
