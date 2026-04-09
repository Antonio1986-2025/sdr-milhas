"""
agent.py — Cérebro da Lara. Processa texto, áudio e imagens e responde via WhatsApp.
"""

import os
import base64
import tempfile
import httpx
from datetime import datetime
from openai import OpenAI

from config import OPENAI_API_KEY, OPENAI_MODEL
from database import buscar_ou_criar_lead, atualizar_lead, salvar_mensagem, buscar_historico
from whatsapp import enviar_mensagem
from repasse import executar_repasse

client = OpenAI(api_key=OPENAI_API_KEY)

SYSTEM_PROMPT = """Você é a Lara, especialista em milhas e SDR da empresa de Gestão de Milhas.

Seu único objetivo é: qualificar o lead e marcar uma CALL no Google Meet com o consultor.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
SOBRE O SERVIÇO
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Oferecemos Gestão Completa de Milhas — acúmulo inteligente e emissão de passagens.
Cliente ideal:
- Gasta R$20.000 ou mais por mês no cartão de crédito
- Viaja 2 ou mais vezes por ano
- Tem milhas paradas sem saber o que fazer
- Não tem tempo para administrar pontos

NUNCA mencione preços. Isso é feito na CALL de fechamento pelo consultor.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
FLUXO DE ATENDIMENTO
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

ETAPA 1 — RECEPÇÃO
Cumprimente com simpatia e pergunte o nome.
"Oi! Tudo bem? 😊 Aqui é a Lara, especialista em milhas. Com quem tenho o prazer?"

ETAPA 2 — CURIOSIDADE
"Você já usa algum cartão que acumula pontos ou milhas?"

ETAPA 3 — QUALIFICAÇÃO (UMA pergunta por vez)
- Gasta quanto por mês no cartão?
- Tem milhas/pontos acumulados em algum programa?
- Viaja quantas vezes por ano?
- Tem tempo para gerenciar tudo isso sozinho?

SINAIS DE LEAD QUENTE:
✅ Gasta R$20k+ no cartão
✅ Viaja 2x ou mais por ano
✅ Tem milhas paradas
✅ Não tem tempo para administrar

ETAPA 4 — CRIAR VALOR (2+ sinais positivos)
"Sabia que a maioria das pessoas perde até 40% do valor das milhas por não saber administrar?
A gente cuida de tudo por você — acúmulo inteligente, melhores resgates, passagens muito mais baratas.
Tudo sem você precisar mexer um dedo. 😉"

ETAPA 5 — MARCAR CALL
"Que tal um papo rápido de 20 minutinhos no Google Meet?
Sem compromisso — só para entender seu perfil e mostrar quanto você pode economizar.
Você tem disponibilidade essa semana?"

Quando o lead CONFIRMAR interesse na call, inclua [REPASSE] na sua resposta.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
REGRAS DE OURO
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
- Simpática, leve, emojis com moderação 😊
- UMA pergunta por mensagem
- Nunca mencione preços
- Se perguntarem quanto custa: "Os valores variam por perfil — por isso a call é tão importante! 😊"
- Lead não qualificado: agradeça e encerre com gentileza
- Mensagens curtas — máximo 4 linhas
- Linguagem informal mas profissional

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
IMAGENS E ÁUDIOS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
- Imagem (extrato, fatura, cartão): analise e use para qualificar o lead
- Áudio: já chega transcrito — responda normalmente
- Confirme o que entendeu: "Vi que você gasta em torno de R$X por mês, é isso?"

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
EXEMPLOS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"Como funciona?":
"A gente assume a gestão completa dos seus pontos — do acúmulo até a emissão das passagens. Você continua usando seus cartões normalmente e a gente faz render muito mais. ✈️ Você já acumula pontos em algum programa?"

"Quanto custa?":
"Os valores são personalizados por perfil — por isso a call é tão importante! O consultor te mostra exatamente quanto você pode economizar. 😊 Você tem 20 minutinhos essa semana?"

"Não tenho tempo":
"Entendo! E é exatamente por isso que nossa gestão faz sentido — você não precisa fazer nada. 😄 A call é rapidinha, 20 minutos no Google Meet. Consegue essa semana?"
"""


# ─────────────────────────────────────────────
# ÁUDIO
# ─────────────────────────────────────────────

def transcrever_audio(url_midia: str = None, base64_midia: str = None, mimetype: str = "audio/ogg") -> str:
    audio_bytes = None

    if base64_midia:
        try:
            if "," in base64_midia:
                base64_midia = base64_midia.split(",", 1)[1]
            audio_bytes = base64.b64decode(base64_midia)
        except Exception as e:
            print(f"[Agent] Erro base64 áudio: {e}")

    if not audio_bytes and url_midia:
        try:
            resp = httpx.get(url_midia, timeout=20)
            resp.raise_for_status()
            audio_bytes = resp.content
        except Exception as e:
            print(f"[Agent] Erro download áudio: {e}")

    if not audio_bytes:
        return "[não consegui ouvir o áudio, pode digitar sua mensagem?]"

    sufixo = ".ogg"
    if "mp4" in mimetype:   sufixo = ".mp4"
    elif "mpeg" in mimetype or "mp3" in mimetype: sufixo = ".mp3"
    elif "webm" in mimetype: sufixo = ".webm"

    tmp_path = None
    try:
        with tempfile.NamedTemporaryFile(suffix=sufixo, delete=False) as tmp:
            tmp.write(audio_bytes)
            tmp_path = tmp.name
        with open(tmp_path, "rb") as f:
            result = client.audio.transcriptions.create(model="whisper-1", file=f, language="pt")
        texto = result.text.strip()
        print(f"[Agent] Áudio transcrito: {texto[:80]}")
        return texto
    except Exception as e:
        print(f"[Agent] Erro transcrição: {e}")
        return "[não consegui transcrever o áudio, pode digitar sua mensagem?]"
    finally:
        if tmp_path and os.path.exists(tmp_path):
            os.unlink(tmp_path)


# ─────────────────────────────────────────────
# IMAGEM
# ─────────────────────────────────────────────

def analisar_imagem(url_midia: str = None, base64_midia: str = None, mimetype: str = "image/jpeg", legenda: str = "") -> str:
    conteudo = None

    if base64_midia:
        try:
            if "," in base64_midia:
                base64_midia = base64_midia.split(",", 1)[1]
            base64.b64decode(base64_midia)
            conteudo = {"type": "image_url", "image_url": {"url": f"data:{mimetype};base64,{base64_midia}", "detail": "low"}}
        except Exception as e:
            print(f"[Agent] Erro base64 imagem: {e}")

    if not conteudo and url_midia:
        conteudo = {"type": "image_url", "image_url": {"url": url_midia, "detail": "low"}}

    if not conteudo:
        return "[não consegui ver a imagem, pode descrever o que enviou?]"

    pergunta = "Analise essa imagem no contexto de gestão de milhas e cartões. Se for extrato ou fatura, informe o valor gasto. Se for cartão, informe bandeira/banco. Seja objetivo e em português."
    if legenda:
        pergunta += f' O lead disse: "{legenda}"'

    try:
        resp = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": [conteudo, {"type": "text", "text": pergunta}]}],
            max_tokens=300,
        )
        descricao = resp.choices[0].message.content.strip()
        print(f"[Agent] Imagem analisada: {descricao[:80]}")
        return descricao
    except Exception as e:
        print(f"[Agent] Erro análise imagem: {e}")
        return "[não consegui analisar a imagem, pode descrever o que enviou?]"


# ─────────────────────────────────────────────
# FUNÇÃO PRINCIPAL
# ─────────────────────────────────────────────

def processar_mensagem(
    numero_raw: str,
    texto: str = "",
    nome_contato: str = "",
    tipo_midia: str = None,
    url_midia: str = None,
    base64_midia: str = None,
    mimetype_midia: str = None,
):
    numero = numero_raw.replace("+", "").replace("-", "").replace(" ", "").strip()

    # Busca ou cria o lead
    lead = buscar_ou_criar_lead(numero, nome_contato)
    lead_id = lead["id"]
    etapa_atual = lead.get("etapa", "ABERTURA")

    # Atualiza nome se ainda não tem
    if nome_contato and not lead.get("nome"):
        atualizar_lead(lead_id, {"nome": nome_contato})

    # Processa mídia
    if tipo_midia == "audio":
        transcrito = transcrever_audio(url_midia, base64_midia, mimetype_midia or "audio/ogg")
        texto_para_gpt = f"[áudio transcrito]: {transcrito}"

    elif tipo_midia == "imagem":
        descricao = analisar_imagem(url_midia, base64_midia, mimetype_midia or "image/jpeg", texto or "")
        texto_para_gpt = f"[imagem enviada — análise]: {descricao}"
        if texto:
            texto_para_gpt += f" | Legenda: {texto}"

    else:
        texto_para_gpt = texto or ""

    if not texto_para_gpt:
        return

    # Salva mensagem recebida
    salvar_mensagem(lead_id, "RECEBIDA", texto_para_gpt, etapa_atual)

    # Busca histórico e monta contexto
    historico = buscar_historico(lead_id, limite=10)
    mensagens = [{"role": "system", "content": SYSTEM_PROMPT}]
    for msg in historico:
        role = "user" if msg["direcao"] == "RECEBIDA" else "assistant"
        mensagens.append({"role": role, "content": msg["conteudo"]})

    # Chama o GPT
    try:
        resp = client.chat.completions.create(
            model=OPENAI_MODEL,
            messages=mensagens,
            max_tokens=400,
            temperature=0.75,
        )
        texto_resposta = resp.choices[0].message.content.strip()
    except Exception as e:
        print(f"[Agent] Erro OpenAI: {e}")
        texto_resposta = "Oi! Tive um probleminha aqui, pode repetir sua mensagem? 😊"

    # Salva resposta
    salvar_mensagem(lead_id, "ENVIADA", texto_resposta, etapa_atual)

    # Verifica repasse
    if "[REPASSE]" in texto_resposta:
        texto_resposta = texto_resposta.replace("[REPASSE]", "").strip()
        atualizar_lead(lead_id, {"etapa": "AGENDADO", "status": "AGENDADO"})
        executar_repasse(lead)
        print(f"[Agent] Repasse executado para lead {lead_id}")

    # Atualiza última interação
    atualizar_lead(lead_id, {"ultima_interacao": datetime.utcnow().isoformat()})

    # Envia resposta
    enviar_mensagem(numero, texto_resposta)
    return texto_resposta
