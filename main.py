from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse
import uvicorn
import threading
from config import PORT
from agent import processar_mensagem
from followup import iniciar_loop

app = FastAPI(title="SDR Milhas — Lara Bot")


@app.get("/")
def health_check():
    """Rota de verificação — confirma que o servidor está no ar."""
    return {"status": "online", "bot": "Lara", "empresa": "SDR Milhas"}


@app.post("/webhook")
async def webhook(request: Request):
    """Recebe os eventos da Evolution API (mensagens do WhatsApp)."""
    try:
        body = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="JSON inválido")

    evento = body.get("event", "")
    dados = body.get("data", {})

    # Só processa mensagens recebidas
    if evento != "messages.upsert":
        return JSONResponse({"status": "ignorado", "evento": evento})

    mensagem = dados.get("message", {})
    chave = dados.get("key", {})

    # Ignora mensagens enviadas pelo próprio bot
    if chave.get("fromMe"):
        return JSONResponse({"status": "ignorado", "motivo": "mensagem própria"})

    # Ignora mensagens de grupo (@g.us = grupo)
    remote_jid = chave.get("remoteJid", "")
    if remote_jid.endswith("@g.us"):
        return JSONResponse({"status": "ignorado", "motivo": "mensagem de grupo"})

    numero = remote_jid.replace("@s.whatsapp.net", "")
    nome = dados.get("pushName", "")

    # ─────────────────────────────────────────
    # Detecta o tipo de mídia enviada pelo lead
    # ─────────────────────────────────────────

    texto = None
    tipo_midia = None
    url_midia = None
    base64_midia = None
    mimetype_midia = None

    # Texto simples
    if mensagem.get("conversation"):
        texto = mensagem["conversation"]

    # Texto formatado (negrito, itálico, link, etc.)
    elif mensagem.get("extendedTextMessage"):
        texto = mensagem["extendedTextMessage"].get("text", "")

    # Imagem
    elif mensagem.get("imageMessage"):
        img = mensagem["imageMessage"]
        tipo_midia = "imagem"
        url_midia = img.get("url") or img.get("directPath")
        base64_midia = dados.get("message", {}).get("base64")
        mimetype_midia = img.get("mimetype", "image/jpeg")
        texto = img.get("caption", "")  # legenda da imagem (pode ser vazia)

    # Áudio / PTT (push-to-talk = mensagem de voz)
    elif mensagem.get("audioMessage") or mensagem.get("pttMessage"):
        audio = mensagem.get("audioMessage") or mensagem.get("pttMessage")
        tipo_midia = "audio"
        url_midia = audio.get("url") or audio.get("directPath")
        base64_midia = dados.get("message", {}).get("base64")
        mimetype_midia = audio.get("mimetype", "audio/ogg; codecs=opus")

    # Documento — avisa que não consegue processar
    elif mensagem.get("documentMessage"):
        texto = "[documento enviado — sem suporte ainda]"

    # Sticker — ignora silenciosamente
    elif mensagem.get("stickerMessage"):
        return JSONResponse({"status": "ignorado", "motivo": "sticker"})

    # Se não tem nada útil, ignora
    if not numero or (not texto and not tipo_midia):
        return JSONResponse({"status": "ignorado", "motivo": "sem conteúdo reconhecido"})

    print(f"[Webhook] {nome} ({numero}) — tipo: {tipo_midia or 'texto'} — {str(texto)[:50]}")

    # Processa em background para não travar o webhook
    threading.Thread(
        target=processar_mensagem,
        args=(numero, texto, nome),
        kwargs={
            "tipo_midia": tipo_midia,
            "url_midia": url_midia,
            "base64_midia": base64_midia,
            "mimetype_midia": mimetype_midia,
        },
        daemon=True,
    ).start()

    return JSONResponse({"status": "recebido"})


def iniciar_followup_background():
    """Inicia o loop de follow-up em uma thread separada."""
    thread = threading.Thread(target=iniciar_loop, daemon=True)
    thread.start()
    print("[Main] Loop de follow-up iniciado em background.")


if __name__ == "__main__":
    iniciar_followup_background()
    uvicorn.run(app, host="0.0.0.0", port=PORT)
