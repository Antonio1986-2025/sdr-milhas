"""
whatsapp.py
-----------
Tudo relacionado a enviar mensagens pelo WhatsApp via Evolution API.
"""

import httpx
from config import EVOLUTION_URL, EVOLUTION_KEY, EVOLUTION_INSTANCE

HEADERS = {
    "apikey": EVOLUTION_KEY,
    "Content-Type": "application/json",
}


def enviar_mensagem(numero: str, texto: str, delay_ms: int = 1500) -> dict:
    """
    Envia uma mensagem de texto para um número via WhatsApp.

    numero: número no formato internacional sem '+' (ex: '5511999998888')
    texto: o texto da mensagem
    delay_ms: tempo de espera em milissegundos antes de enviar (simula digitação)
    """
    url = f"{EVOLUTION_URL}/message/sendText/{EVOLUTION_INSTANCE}"
    payload = {
        "number": numero,
        "text": texto,
        "delay": delay_ms,
    }
    resp = httpx.post(url, headers=HEADERS, json=payload, timeout=30)
    resp.raise_for_status()
    return resp.json()
