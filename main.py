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

    # Estrutura do evento da Evolution API
    evento = body.get("event", "")
    dados = body.get("data", {})

    # Só processa mensagens recebidas (ignora mensagens enviadas pelo bot)
    if evento != "messages.upsert":
        return JSONResponse({"status": "ignorado", "evento": evento})

    mensagem = dados.get("message", {})
    chave = dados.get("key", {})

    # Ignora mensagens enviadas pelo próprio bot
    if chave.get("fromMe"):
        return JSONResponse({"status": "ignorado", "motivo": "mensagem própria"})

    # Extrai o número e o texto
    numero = chave.get("remoteJid", "").replace("@s.whatsapp.net", "")
    texto = mensagem.get("conversation") or mensagem.get("extendedTextMessage", {}).get("text", "")
    nome = dados.get("pushName", "")

    if not numero or not texto:
        return JSONResponse({"status": "ignorado", "motivo": "sem número ou texto"})

    print(f"[Webhook] Mensagem de {nome} ({numero}): {texto[:50]}...")

    # Processa em background para não travar o webhook
    threading.Thread(
        target=processar_mensagem,
        args=(numero, texto, nome),
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
