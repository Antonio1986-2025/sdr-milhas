"""
main.py — Servidor principal FastAPI. Recebe webhooks da Evolution API.
"""

import threading
import uvicorn
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse

from config import PORT
from agent import processar_mensagem
from followup import iniciar_loop_followup

app = FastAPI(title="SDR Milhas — Lara Bot")


@app.get("/")
def health_check():
    return {"status": "online", "bot": "Lara", "empresa": "SDR Milhas"}


@app.post("/webhook")
async def webhook(request: Request):
    try:
        body = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="JSON inválido")

    evento = body.get("event", "")
    dados  = body.get("data", {})

    if evento != "messages.upsert":
        return JSONResponse({"status": "ignorado", "evento": evento})

    mensagem   = dados.get("message", {})
    chave      = dados.get("key", {})
    remote_jid = chave.get("remoteJid", "")

    # Ignora mensagens próprias e de grupos
    if chave.get("fromMe"):
        return JSONResponse({"status": "ignorado", "motivo": "mensagem própria"})
    if remote_jid.endswith("@g.us"):
        return JSONResponse({"status": "ignorado", "motivo": "mensagem de grupo"})

    numero = remote_jid.replace("@s.whatsapp.net", "")
    nome   = dados.get("pushName", "")

    # Detecta tipo de conteúdo
    texto         = None
    tipo_midia    = None
    url_midia     = None
    base64_midia  = None
    mimetype_midia = None

    if mensagem.get("conversation"):
        texto = mensagem["conversation"]
    elif mensagem.get("extendedTextMessage"):
        texto = mensagem["extendedTextMessage"].get("text", "")
    elif mensagem.get("imageMessage"):
        img            = mensagem["imageMessage"]
        tipo_midia     = "imagem"
        url_midia      = img.get("url") or img.get("directPath")
        base64_midia   = dados.get("message", {}).get("base64")
        mimetype_midia = img.get("mimetype", "image/jpeg")
        texto          = img.get("caption", "")
    elif mensagem.get("audioMessage") or mensagem.get("pttMessage"):
        audio          = mensagem.get("audioMessage") or mensagem.get("pttMessage")
        tipo_midia     = "audio"
        url_midia      = audio.get("url") or audio.get("directPath")
        base64_midia   = dados.get("message", {}).get("base64")
        mimetype_midia = audio.get("mimetype", "audio/ogg; codecs=opus")
    elif mensagem.get("documentMessage"):
        texto = "[documento enviado — sem suporte ainda]"
    elif mensagem.get("stickerMessage"):
        return JSONResponse({"status": "ignorado", "motivo": "sticker"})

    if not numero or (not texto and not tipo_midia):
        return JSONResponse({"status": "ignorado", "motivo": "sem conteúdo"})

    print(f"[Webhook] {nome} ({numero}) — {tipo_midia or 'texto'}: {str(texto)[:50]}")

    threading.Thread(
        target=processar_mensagem,
        args=(numero, texto or "", nome),
        kwargs={
            "tipo_midia":    tipo_midia,
            "url_midia":     url_midia,
            "base64_midia":  base64_midia,
            "mimetype_midia": mimetype_midia,
        },
        daemon=True,
    ).start()

    return JSONResponse({"status": "recebido"})


if __name__ == "__main__":
    iniciar_loop_followup()
    uvicorn.run(app, host="0.0.0.0", port=PORT)
