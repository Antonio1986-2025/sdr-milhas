from openai import OpenAI
from config import OPENAI_API_KEY, OPENAI_MODEL, NOME_ASSISTENTE, EMPRESA
from database import (
    buscar_ou_criar_lead,
    salvar_mensagem,
    buscar_historico,
    atualizar_lead,
    criar_followup,
    salvar_ficha_repasse,
)
from whatsapp import enviar_mensagem, enviar_audio, formatar_numero
from repasse import gerar_e_enviar_ficha
from datetime import datetime, timedelta
import httpx
import base64
import tempfile
import os

client = OpenAI(api_key=OPENAI_API_KEY)

# ─────────────────────────────────────────────
# CONFIGURAÇÃO DE RESPOSTA POR ÁUDIO
# ─────────────────────────────────────────────
# Se True, a Lara responde por áudio quando o lead envia áudio.
# Se False, sempre responde por texto.
RESPONDER_AUDIO_COM_AUDIO = True

# Voz do TTS — opções OpenAI: alloy, echo, fable, onyx, nova, shimmer
# "nova" é feminina e natural — ideal para a Lara
TTS_VOZ = "nova"

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

SINAIS DE LEAD QUENTE (anote mentalmente):
✅ Gasta R$20k+ no cartão
✅ Viaja 2x ou mais por ano
✅ Tem milhas paradas
✅ Não tem tempo para administrar

ETAPA 4 — CRIAR VALOR (quando o lead tiver 2 ou mais sinais positivos)
Mostre o problema que ele tem sem saber:
"Sabia que a maioria das pessoas perde até 40% do valor das milhas por não saber administrar?
A gente cuida de tudo isso por você — acúmulo inteligente, melhores resgates, passagens muito mais baratas.
Tudo sem você precisar mexer um dedo. 😉"

ETAPA 5 — MARCAR A CALL
Quando o lead demonstrar interesse, convide para a call:
"Que tal a gente bater um papo rápido de 20 minutinhos no Google Meet?
Sem compromisso — só para eu entender melhor o seu perfil e mostrar quanto você pode economizar nas suas próximas viagens.
Você tem disponibilidade essa semana?"

Ao confirmar interesse na call, diga: [REPASSE]

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
REGRAS DE OURO
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
- Seja simpática, leve e use emojis com moderação 😊
- Faça UMA pergunta por mensagem — nunca bombardeie o lead
- Nunca mencione preços, valores ou planos
- Se perguntarem quanto custa, diga: "Os valores variam conforme o perfil de cada cliente — por isso a call é tão importante! Lá o consultor apresenta tudo direitinho para você. 😊"
- Se o lead não for qualificado (gasta pouco, não viaja), agradeça e encerre com gentileza
- Mensagens curtas e objetivas — máximo 4 linhas por mensagem
- Use linguagem informal mas profissional
- Nunca pressione — seja consultiva
- Se o lead sumir, agende follow-up automático

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
SOBRE IMAGENS E ÁUDIOS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
- Se o lead enviar uma imagem (extrato, cartão, fatura), analise com atenção e use as informações para qualificá-lo melhor
- Se o lead enviar um áudio, a mensagem já chega transcrita para você — responda normalmente
- Sempre confirme o que entendeu: "Vi aqui no seu extrato que você gasta em torno de R$X por mês, é isso?"

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
EXEMPLOS DE ABORDAGEM
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Lead pergunta "como funciona?":
"Basicamente a gente assume a gestão completa dos seus pontos e milhas — desde o acúmulo inteligente até a emissão das passagens. Você continua usando seus cartões normalmente, e a gente faz o dinheiro render muito mais. ✈️ Me conta, você já acumula pontos em algum programa?"

Lead pergunta "quanto custa?":
"Os valores são personalizados para cada perfil — por isso a call é tão importante! Lá o consultor consegue te mostrar exatamente quanto você pode economizar e qual seria o melhor plano para você. 😊 Você tem 20 minutinhos essa semana?"

Lead diz "não tenho tempo":
"Entendo! E é exatamente por isso que a nossa gestão faz sentido — você não precisa fazer nada, a gente cuida de tudo. 😄 A call é rapidinha, 20 minutos pelo Google Meet. Consegue essa semana?"
"""


# ─────────────────────────────────────────────
# FUNÇÕES DE MÍDIA — ENTRADA
# ─────────────────────────────────────────────

def transcrever_audio(url_midia: str = None, base64_midia: str = None, mimetype: str = "audio/ogg") -> str:
    """
    Transcreve um áudio usando o Whisper (OpenAI).
    Tenta usar base64 primeiro (mais rápido), depois URL.
    Retorna o texto transcrito ou uma mensagem de erro amigável.
    """
    audio_bytes = None

    # Tenta decodificar o base64 enviado pela Evolution API
    if base64_midia:
        try:
            # A Evolution às vezes manda com prefixo "data:audio/ogg;base64,..."
            if "," in base64_midia:
                base64_midia = base64_midia.split(",", 1)[1]
            audio_bytes = base64.b64decode(base64_midia)
        except Exception as e:
            print(f"[Agent] Erro ao decodificar base64 do áudio: {e}")

    # Se não tem base64, baixa pela URL
    if not audio_bytes and url_midia:
        try:
            resp = httpx.get(url_midia, timeout=20)
            resp.raise_for_status()
            audio_bytes = resp.content
        except Exception as e:
            print(f"[Agent] Erro ao baixar áudio pela URL: {e}")

    if not audio_bytes:
        return "[não consegui ouvir o áudio, pode digitar sua mensagem?]"

    # Salva em arquivo temporário (o Whisper precisa de um arquivo)
    sufixo = ".ogg"
    if "mp4" in mimetype:
        sufixo = ".mp4"
    elif "mpeg" in mimetype or "mp3" in mimetype:
        sufixo = ".mp3"
    elif "webm" in mimetype:
        sufixo = ".webm"

    try:
        with tempfile.NamedTemporaryFile(suffix=sufixo, delete=False) as tmp:
            tmp.write(audio_bytes)
            tmp_path = tmp.name

        with open(tmp_path, "rb") as audio_file:
            transcricao = client.audio.transcriptions.create(
                model="whisper-1",
                file=audio_file,
                language="pt",  # força português para melhor precisão
            )
        os.unlink(tmp_path)  # apaga o arquivo temporário
        texto = transcricao.text.strip()
        print(f"[Agent] Áudio transcrito: {texto[:80]}")
        return texto

    except Exception as e:
        print(f"[Agent] Erro ao transcrever áudio: {e}")
        if os.path.exists(tmp_path):
            os.unlink(tmp_path)
        return "[não consegui transcrever o áudio, pode digitar sua mensagem?]"


def analisar_imagem(url_midia: str = None, base64_midia: str = None, mimetype: str = "image/jpeg", legenda: str = "") -> str:
    """
    Analisa uma imagem usando o GPT-4o-mini (vision).
    Retorna uma descrição do conteúdo focada no contexto de milhas/cartões.
    """
    # Monta o conteúdo da imagem para o GPT
    conteudo_imagem = None

    if base64_midia:
        try:
            if "," in base64_midia:
                base64_midia = base64_midia.split(",", 1)[1]
            # Valida que é base64 válido
            base64.b64decode(base64_midia)
            conteudo_imagem = {
                "type": "image_url",
                "image_url": {
                    "url": f"data:{mimetype};base64,{base64_midia}",
                    "detail": "low",  # "low" é mais barato e suficiente para extratos
                },
            }
        except Exception as e:
            print(f"[Agent] Erro no base64 da imagem: {e}")

    if not conteudo_imagem and url_midia:
        conteudo_imagem = {
            "type": "image_url",
            "image_url": {"url": url_midia, "detail": "low"},
        }

    if not conteudo_imagem:
        return "[não consegui ver a imagem, pode descrever o que enviou?]"

    pergunta = "Analise essa imagem no contexto de gestão de milhas e cartões de crédito. Se for um extrato ou fatura, informe o valor gasto. Se for um cartão, informe a bandeira/banco. Seja objetivo e em português."
    if legenda:
        pergunta += f' O lead disse: "{legenda}"'

    try:
        resposta = client.chat.completions.create(
            model="gpt-4o-mini",  # vision já está incluído no gpt-4o-mini
            messages=[
                {
                    "role": "user",
                    "content": [
                        conteudo_imagem,
                        {"type": "text", "text": pergunta},
                    ],
                }
            ],
            max_tokens=300,
        )
        descricao = resposta.choices[0].message.content.strip()
        print(f"[Agent] Imagem analisada: {descricao[:80]}")
        return descricao

    except Exception as e:
        print(f"[Agent] Erro ao analisar imagem: {e}")
        return "[não consegui analisar a imagem, pode descrever o que enviou?]"


# ─────────────────────────────────────────────
# FUNÇÕES DE MÍDIA — SAÍDA (TTS)
# ─────────────────────────────────────────────

def _limpar_texto_para_tts(texto: str) -> str:
    """
    Remove emojis, markdown e marcações que soam estranho em áudio.
    O TTS da OpenAI lida bem com pontuação e tom informal, mas emojis
    são lidos como nomes (ex.: "emoji de avião"), então removemos.
    """
    import re
    # Remove emojis (bloco Unicode de emojis/símbolos)
    emoji_pattern = re.compile(
        "["
        "\U0001F600-\U0001F64F"  # emoticons
        "\U0001F300-\U0001F5FF"  # símbolos e pictogramas
        "\U0001F680-\U0001F6FF"  # transporte e mapa
        "\U0001F1E0-\U0001F1FF"  # bandeiras
        "\U00002702-\U000027B0"
        "\U000024C2-\U0001F251"
        "\U0001F900-\U0001F9FF"  # símbolos suplementares
        "\U0001FA00-\U0001FA6F"
        "\U0001FA70-\U0001FAFF"
        "\u2600-\u26FF"
        "\u2700-\u27BF"
        "]+",
        flags=re.UNICODE,
    )
    texto = emoji_pattern.sub("", texto)

    # Remove marcações markdown (negrito, itálico, etc.)
    texto = re.sub(r"\*+", "", texto)
    texto = re.sub(r"_+", "", texto)
    texto = re.sub(r"`+", "", texto)

    # Remove linhas com só traços/underlines (separadores visuais)
    texto = re.sub(r"^[-=_]{3,}$", "", texto, flags=re.MULTILINE)

    # Remove tags internas como [REPASSE]
    texto = re.sub(r"\[.*?\]", "", texto)

    # Normaliza espaços extras
    texto = re.sub(r"  +", " ", texto).strip()

    return texto


def gerar_audio_tts(texto: str) -> bytes | None:
    """
    Converte texto em áudio usando o TTS da OpenAI (tts-1).
    Retorna os bytes do áudio em formato OGG/OPUS, ou None em caso de erro.
    
    Usamos tts-1 (mais rápido e barato) com formato opus — ideal para WhatsApp.
    """
    texto_limpo = _limpar_texto_para_tts(texto)

    if not texto_limpo:
        print("[TTS] Texto vazio após limpeza, pulando geração de áudio.")
        return None

    try:
        resposta = client.audio.speech.create(
            model="tts-1",          # tts-1 = rápido e barato | tts-1-hd = mais natural
            voice=TTS_VOZ,          # nova = voz feminina natural em pt-BR
            input=texto_limpo,
            response_format="opus", # opus = menor tamanho, compatível com WhatsApp
        )
        audio_bytes = resposta.read()
        print(f"[TTS] Áudio gerado: {len(audio_bytes)} bytes")
        return audio_bytes

    except Exception as e:
        print(f"[TTS] Erro ao gerar áudio: {e}")
        return None


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
    numero = formatar_numero(numero_raw)
    lead = buscar_ou_criar_lead(numero, nome_contato)
    lead_id = lead["id"]

    if nome_contato and not lead.get("nome"):
        atualizar_lead(lead_id, {"nome": nome_contato})

    # ── Detecta se deve responder por áudio ──
    # Responde por áudio se: a flag está ativa E o lead enviou um áudio
    deve_responder_com_audio = RESPONDER_AUDIO_COM_AUDIO and tipo_midia == "audio"

    # ── Processa mídia antes de passar para o GPT ──

    if tipo_midia == "audio":
        # Transcreve o áudio e usa o texto transcrito como mensagem
        texto_transcrito = transcrever_audio(url_midia, base64_midia, mimetype_midia or "audio/ogg")
        texto_para_gpt = f"[áudio transcrito]: {texto_transcrito}"
        texto_para_salvar = texto_para_gpt
        print(f"[Agent] Áudio → texto: {texto_transcrito[:60]}")

    elif tipo_midia == "imagem":
        # Analisa a imagem e combina com a legenda (se houver)
        descricao_imagem = analisar_imagem(url_midia, base64_midia, mimetype_midia or "image/jpeg", texto or "")
        texto_para_gpt = f"[imagem enviada — análise]: {descricao_imagem}"
        if texto:
            texto_para_gpt += f" | Legenda do lead: {texto}"
        texto_para_salvar = texto_para_gpt
        print(f"[Agent] Imagem → descrição: {descricao_imagem[:60]}")

    else:
        # Mensagem de texto normal
        texto_para_gpt = texto or ""
        texto_para_salvar = texto or ""

    if not texto_para_gpt:
        return

    # Salva a mensagem no histórico
    salvar_mensagem(lead_id, "usuario", texto_para_salvar)
    historico = buscar_historico(lead_id)

    # Monta as mensagens para o GPT com histórico completo
    mensagens = [{"role": "system", "content": SYSTEM_PROMPT}]
    for msg in historico:
        role = "user" if msg["papel"] == "usuario" else "assistant"
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
        print(f"[Agent] Erro ao chamar OpenAI: {e}")
        texto_resposta = "Oi! Tive um probleminha aqui, pode repetir sua mensagem? 😊"

    salvar_mensagem(lead_id, "assistente", texto_resposta)

    # Verifica se deve fazer repasse para o Pedro
    if "[REPASSE]" in texto_resposta:
        texto_resposta = texto_resposta.replace("[REPASSE]", "").strip()
        atualizar_lead(lead_id, {"etapa": "repasse", "status": "qualificado"})
        gerar_e_enviar_ficha(lead_id, historico)
        print(f"[Agent] Ficha de repasse gerada para lead {lead_id}")

    # Agenda follow-up se lead ainda estiver em qualificação
    etapa_atual = lead.get("etapa", "interesse")
    if etapa_atual in ["interesse", "qualificacao"]:
        followup_em = (datetime.utcnow() + timedelta(hours=24)).isoformat()
        nome = lead.get("nome") or ""
        criar_followup(
            lead_id,
            f"Oi {nome}! 😊 Ainda estou por aqui caso queira saber mais sobre como maximizar suas milhas. Posso te ajudar?",
            followup_em,
        )

    # ── Envia a resposta (áudio ou texto) ──
    if deve_responder_com_audio:
        audio_bytes = gerar_audio_tts(texto_resposta)
        if audio_bytes:
            sucesso_audio = enviar_audio(numero, audio_bytes)
            if sucesso_audio:
                print(f"[Agent] Resposta enviada como ÁUDIO para {numero}")
                return texto_resposta
            else:
                # Fallback: se o áudio falhar, envia texto
                print(f"[Agent] Falha no áudio — enviando texto como fallback para {numero}")
                enviar_mensagem(numero, texto_resposta)
        else:
            # TTS falhou — envia texto
            print(f"[Agent] TTS falhou — enviando texto como fallback para {numero}")
            enviar_mensagem(numero, texto_resposta)
    else:
        enviar_mensagem(numero, texto_resposta)

    return texto_resposta
