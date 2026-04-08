import requests
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


def formatar_numero(numero: str) -> str:
    """Remove caracteres especiais e garante o formato correto."""
    return numero.replace("+", "").replace("-", "").replace(" ", "").strip()
