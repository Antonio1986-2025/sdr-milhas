import requests
import base64
from config import EVOLUTION_API_URL, EVOLUTION_API_KEY, EVOLUTION_INSTANCE


def enviar_mensagem(numero: str, texto: str) -> bool:
    """Envia uma mensagem de texto via Evolution API.
    
    numero: número no formato 5511999999999 (sem + ou espaços)
    texto: conteúdo da mensagem
    """
    url = f"{EVOLUTION_API_URL}/message/sendText/{EVOLUTION_INSTANCE}"

    headers = {
        "apikey": EVOLUTION_API_KEY,
        "Content-Type": "application/json",
    }

    payload = {
        "number": numero,
        "text": texto,
    }

    try:
        resposta = requests.post(url, json=payload, headers=headers, timeout=10)
        resposta.raise_for_status()
        print(f"[WhatsApp] Mensagem enviada para {numero}")
        return True
    except requests.exceptions.RequestException as e:
        print(f"[WhatsApp] Erro ao enviar mensagem para {numero}: {e}")
        return False


def enviar_audio(numero: str, audio_bytes: bytes) -> bool:
    """Envia um áudio (PTT/voice note) via Evolution API.

    numero: número no formato 5511999999999 (sem + ou espaços)
    audio_bytes: bytes do áudio em formato OGG/OPUS (gerado pelo TTS)
    """
    url = f"{EVOLUTION_API_URL}/message/sendWhatsAppAudio/{EVOLUTION_INSTANCE}"

    headers = {
        "apikey": EVOLUTION_API_KEY,
        "Content-Type": "application/json",
    }

    # A Evolution API aceita áudio em base64 com o campo "audio"
    audio_base64 = base64.b64encode(audio_bytes).decode("utf-8")

    payload = {
        "number": numero,
        "audio": f"data:audio/ogg;base64,{audio_base64}",
        "encoding": True,  # pede para a Evolution API converter se necessário
    }

    try:
        resposta = requests.post(url, json=payload, headers=headers, timeout=30)
        resposta.raise_for_status()
        print(f"[WhatsApp] Áudio enviado para {numero}")
        return True
    except requests.exceptions.RequestException as e:
        print(f"[WhatsApp] Erro ao enviar áudio para {numero}: {e}")
        # Tenta fallback: endpoint alternativo com mediaMessage
        return _enviar_audio_fallback(numero, audio_bytes)


def _enviar_audio_fallback(numero: str, audio_bytes: bytes) -> bool:
    """Fallback: envia o áudio como mediaMessage (base64)."""
    url = f"{EVOLUTION_API_URL}/message/sendMedia/{EVOLUTION_INSTANCE}"

    headers = {
        "apikey": EVOLUTION_API_KEY,
        "Content-Type": "application/json",
    }

    audio_base64 = base64.b64encode(audio_bytes).decode("utf-8")

    payload = {
        "number": numero,
        "mediatype": "audio",
        "mimetype": "audio/ogg; codecs=opus",
        "media": audio_base64,
        "fileName": "audio.ogg",
    }

    try:
        resposta = requests.post(url, json=payload, headers=headers, timeout=30)
        resposta.raise_for_status()
        print(f"[WhatsApp] Áudio enviado (fallback) para {numero}")
        return True
    except requests.exceptions.RequestException as e:
        print(f"[WhatsApp] Erro no fallback de áudio para {numero}: {e}")
        return False


def formatar_numero(numero: str) -> str:
    """Remove caracteres especiais e garante o formato correto."""
    return numero.replace("+", "").replace("-", "").replace(" ", "").strip()
