"""
whatsapp.py — Envia mensagens via Evolution API.
"""

import httpx
from config import EVOLUTION_URL, EVOLUTION_KEY, EVOLUTION_INSTANCE

HEADERS = {
    "apikey": EVOLUTION_KEY,
    "Content-Type": "application/json",
}


def enviar_mensagem(numero: str, texto: str, delay_ms: int = 1500) -> dict:
    """
    Envia mensagem de texto via WhatsApp.
    numero: formato internacional sem '+' (ex: 5511999998888)
    """
    url = f"{EVOLUTION_URL}/message/sendText/{EVOLUTION_INSTANCE}"
    payload = {
        "number": numero,
        "text": texto,
        "delay": delay_ms,
    }
    try:
        resp = httpx.post(url, headers=HEADERS, json=payload, timeout=30)
        resp.raise_for_status()
        print(f"[WhatsApp] Mensagem enviada para {numero}")
        return resp.json()
    except Exception as e:
        print(f"[WhatsApp] Erro ao enviar para {numero}: {e}")
        return {}
