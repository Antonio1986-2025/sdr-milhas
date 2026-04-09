"""
agent.py
--------
Cérebro da Lara — processa mensagens, chama o GPT e orquestra todo o fluxo.
Suporta texto, áudio (transcrição via Whisper) e imagens (análise via Vision).
"""

import os
import base64
import tempfile
import httpx
from datetime import datetime, timedelta
from openai import OpenAI

from config import OPENAI_API_KEY, OPENAI_MODEL, OPENAI_MAX_TOKENS
from database import (
    upsert_lead,
    buscar_lead_por_whatsapp,
    atualizar_lead,
    salvar_mensagem,
    buscar_historico,
)
from whatsapp import enviar_mensagem
from repasse import executar_repasse

client = OpenAI(api_key=OPENAI_API_KEY)

SYSTEM_PROMPT = """Você é a Lara, especialista em milhas e SDR da empresa de Gestão de Milhas.

Seu único objetivo é: qualificar o lead e marcar uma CALL no Google Meet com o consultor.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
SOBRE O SERVIÇO (use para contexto, nunca revele detalhes de preço)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Oferecemos Gestão Completa de Milhas — acúmulo inteligente e emissão de passagens.
Nosso cliente ideal é quem:
- Gasta R$20.000 ou mais por mês no cartão de crédito
- Viaja 2 ou mais vezes por ano
- Tem milhas paradas sem saber o que fazer
- Não tem tempo para administrar seus pontos
- Quer viajar muito mais barato usando as próprias milhas

NUNCA mencione preços, valores ou planos. Isso é feito na CALL de fechamento.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
SEU FLUXO DE ATENDIMENTO
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

ETAPA 1 — RECEPÇÃO CALOROSA
Cumprimente com simpatia. Pergunte o nome se ainda não souber.
Exemplo: "Oi! Tudo bem? 😊 Aqui é a Lara, especialista em milhas. Com quem tenho o prazer?"

ETAPA 2 — DESPERTAR CURIOSIDADE
Entenda o interesse do lead com uma pergunta aberta.
Exemplo: "Você já usa algum cartão que acumula pontos ou milhas?"

ETAPA 3 — QUALIFICAÇÃO (faça UMA pergunta por vez, de forma natural)
Colete essas informações ao longo da conversa:
- Usa cartão de crédito? Gasta quanto por mês aproximadamente?
- Tem milhas ou pontos acumulados em algum programa?
- Viaja com frequência? Quantas vezes por ano?
- Tem tempo para gerenciar tudo isso sozinho?

SINAIS DE LEAD QUENTE:
✅ Gasta R$20k+ no cartão
✅ Viaja 2x ou mais por ano
✅ Tem milhas paradas
✅ Não tem tempo para administrar

ETAPA 4 — CRIAR VALOR (quando o lead tiver 2 ou mais sinais positivos)
"Sabia que a maioria das pessoas perde até 40% do valor das milhas por não saber administrar?
A gente cuida de tudo isso por você — acúmulo inteligente, melhores resgates, passagens muito mais baratas.
Tudo sem você precisar mexer um dedo. 😉"

ETAPA 5 — MARCAR A CALL
"Que tal a gente bater um papo rápido de 20 minutinhos no Google Meet?
Sem compromisso — só para eu entender melhor o seu perfil e mostrar quanto você pode economizar.
Você tem disponibilidade essa semana?"

Quando o lead CONFIRMAR interesse na call, inclua [REPASSE] na sua resposta.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
REGRAS DE OURO
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
- Seja simpática, leve e use emojis com moderação 😊
- Faça UMA pergunta por mensagem — nunca bombardeie o lead
- Nunca mencione preços, valores ou planos
- Se perguntarem quanto custa: "Os valores variam conforme o perfil — por isso a call é tão importante! 😊"
- Se o lead não for qualificado, agradeça e encerre com gentileza
- Mensagens curtas — máximo 4 linhas por mensagem
- Use linguagem informal mas profissional

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
SOBRE IMAGENS E ÁUDIOS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
- Se o lead enviar uma imagem (extrato, cartão, fatura), analise e use para qualificá-lo
- Se o lead enviar um áudio, a mensagem já chega transcrita — responda normalmente
- Sempre confirme o que entendeu: "Vi aqui no seu extrato que você gasta em torno de R$X por mês, é isso?"

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
EXEMPLOS DE ABORDAGEM
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Lead pergunta "como funciona?":
"Basicamente a gente assume a gestão completa dos seus pontos e milhas — do acúmulo inteligente até a emissão das passagens. Você continua usando seus cartões normalmente, e a gente faz render muito mais. ✈️ Me conta, você já acumula pontos em algum programa?"

Lead pergunta "quanto custa?":
"Os valores são personalizados para cada perfil — por isso a call é tão importante! O consultor te mostra exatamente quanto você pode economizar. 😊 Você tem 20 minutinhos essa semana?"

Lead diz "não tenho tempo":
"Entendo! E é exatamente por isso que nossa gestão faz sentido — você não precisa fazer nada, a gente cuida de tudo. 😄 A call é rapidinha, 20 minutos pelo Google Meet. Consegue essa semana?"
"""


# ─────────────────────────────────────────────
# MÍDIA — ÁUDIO
# ─────────────────────────────────────────────

def transcrever_audio(url_midia: str = None, base64_midia: str = None, mimetype: str = "audio/ogg") -> str:
    """Transcreve áudio usando Whisper. Tenta base64 primeiro, depois URL."""
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
    if "mp4" in mimetype:
        sufixo = ".mp4"
    elif "mpeg" in mimetype or "mp3" in mimetype:
        sufixo = ".mp3"
    elif "webm" in mimetype:
        sufixo = ".webm"

    tmp_path = None
    try:
        with tempfile.NamedTemporaryFile(suffix=sufixo, delete=False) as tmp:
            tmp.write(audio_bytes)
            tmp_path = tmp.name

        with open(tmp_path, "rb") as audio_file:
            transcricao = client.audio.transcriptions.create(
                model="whisper-1",
                file=audio_file,
                language="pt",
            )
        texto = transcricao.text.strip()
        print(f"[Agent] Áudio transcrito: {texto[:80]}")
        return texto
    except Exception as e:
        print(f"[Agent] Erro transcrição: {e}")
        return "[não consegui transcrever o áudio, pode digitar sua mensagem?]"
    finally:
        if tmp_path and os.path.exists(tmp_path):
            os.unlink(tmp_path)


# ─────────────────────────────────────────────
# MÍDIA — IMAGEM
# ─────────────────────────────────────────────

def analisar_imagem(url_midia: str = None, base64_midia: str = None, mimetype: str = "image/jpeg", legenda: str = "") -> str:
    """Analisa imagem usando GPT-4o-mini Vision."""
    conteudo_imagem = None

    if base64_midia:
        try:
            if "," in base64_midia:
                base64_midia = base64_midia.split(",", 1)[1]
            base64.b64decode(base64_midia)
            conteudo_imagem = {
                "type": "image_url",
                "image_url": {
                    "url": f"data:{mimetype};base64,{base64_midia}",
                    "detail": "low",
                },
            }
        except Exception as e:
            print(f"[Agent] Erro base64 imagem: {e}")

    if not conteudo_imagem and url_midia:
        conteudo_imagem = {
            "type": "image_url",
            "image_url": {"url": url_midia, "detail": "low"},
        }

    if not conteudo_imagem:
        return "[não consegui ver a imagem, pode descrever o que enviou?]"

    pergunta = "Analise essa imagem no contexto de gestão de milhas e cartões de crédito. Se for extrato ou fatura, informe o valor gasto. Se for cartão, informe bandeira/banco. Seja objetivo e em português."
    if legenda:
        pergunta += f' O lead disse: "{legenda}"'

    try:
        resposta = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{
                "role": "user",
                "content": [
                    conteudo_imagem,
                    {"type": "text", "text": pergunta},
                ],
            }],
            max_tokens=300,
        )
        descricao = resposta.choices[0].message.content.strip()
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
    texto: str,
    nome_contato: str = "",
    tipo_midia: str = None,
    url_midia: str = None,
    base64_midia: str = None,
    mimetype_midia: str = None,
):
    """Processa uma mensagem recebida e responde via WhatsApp."""

    numero = numero_raw.replace("+", "").replace("-", "").replace(" ", "").strip()

    # Busca ou cria o lead
    lead = buscar_lead_por_whatsapp(numero)
    if not lead:
        lead = upsert_lead(numero, nome_contato)

    lead_id = lead["id"]
    etapa_atual = lead.get("etapa", "ABERTURA")

    # Atualiza nome se ainda não tem
    if nome_contato and not lead.get("nome"):
        atualizar_lead(lead_id, {"nome": nome_contato})

    # ── Processa mídia ──
    if tipo_midia == "audio":
        texto_transcrito = transcrever_audio(url_midia, base64_midia, mimetype_midia or "audio/ogg")
        texto_para_gpt = f"[áudio transcrito]: {texto_transcrito}"
        texto_para_salvar = texto_para_gpt

    elif tipo_midia == "imagem":
        descricao = analisar_imagem(url_midia, base64_midia, mimetype_midia or "image/jpeg", texto or "")
        texto_para_gpt = f"[imagem enviada — análise]: {descricao}"
        if texto:
            texto_para_gpt += f" | Legenda: {texto}"
        texto_para_salvar = texto_para_gpt

    else:
        texto_para_gpt = texto or ""
        texto_para_salvar = texto or ""

    if not texto_para_gpt:
        return

    # Salva mensagem do usuário
    salvar_mensagem(lead_id, "RECEBIDA", texto_para_salvar, etapa_atual)

    # Busca histórico
    historico = buscar_historico(lead_id, limite=10)

    # Monta contexto para o GPT
    mensagens = [{"role": "system", "content": SYSTEM_PROMPT}]
    for msg in historico:
        role = "user" if msg["direcao"] == "RECEBIDA" else "assistant"
        mensagens.append({"role": role, "content": msg["conteudo"]})

    # Chama o GPT
    try:
        resposta = client.chat.completions.create(
            model=OPENAI_MODEL,
            messages=mensagens,
            max_tokens=400,
            temperature=0.75,
        )
        texto_resposta = resposta.choices[0].message.content.strip()
    except Exception as e:
        print(f"[Agent] Erro OpenAI: {e}")
        texto_resposta = "Oi! Tive um probleminha aqui, pode repetir sua mensagem? 😊"

    # Salva resposta da Lara
    salvar_mensagem(lead_id, "ENVIADA", texto_resposta, etapa_atual)

    # Verifica se deve fazer repasse para o Pedro
    if "[REPASSE]" in texto_resposta:
        texto_resposta = texto_resposta.replace("[REPASSE]", "").strip()
        atualizar_lead(lead_id, {"etapa": "AGENDADO", "status": "AGENDADO"})
        executar_repasse(lead)
        print(f"[Agent] Repasse executado para lead {lead_id}")

    # Atualiza última interação
    atualizar_lead(lead_id, {"ultima_interacao": datetime.utcnow().isoformat()})

    # Envia resposta via WhatsApp
    enviar_mensagem(numero, texto_resposta)

    return texto_resposta
