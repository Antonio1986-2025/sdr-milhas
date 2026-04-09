from openai import OpenAI
import json
from config import OPENAI_API_KEY, OPENAI_MODEL
from database import (
    buscar_ou_criar_lead,
    salvar_mensagem,
    buscar_historico,
    atualizar_lead,
    criar_agendamento,
    registrar_followup,
)
from whatsapp import enviar_mensagem
from repasse import executar_repasse
from datetime import datetime, timedelta
import httpx
import base64
import tempfile
import os

client = OpenAI(api_key=OPENAI_API_KEY)

# ─────────────────────────────────────────────
# PROMPT PRINCIPAL DA LARA
# ─────────────────────────────────────────────

SYSTEM_PROMPT = """Você é a Lara, especialista em milhas e SDR da empresa Gestão de Milhas.

Seu único objetivo é: qualificar o lead e marcar uma CALL no Google Meet com o consultor Caio.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
SOBRE O SERVIÇO
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Oferecemos Gestão Completa de Milhas — acúmulo inteligente e emissão de passagens.
Cliente ideal: gasta R$20k+/mês no cartão, viaja 2x+/ano, tem milhas paradas.
NUNCA mencione preços — isso é feito na CALL pelo consultor Caio.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
FLUXO DE ATENDIMENTO
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
ETAPA 1 — APRESENTAÇÃO (sempre na primeira mensagem)
Apresente-se pelo nome e pergunte o nome do lead.
Exemplo: "Oi! Tudo bem? 😊 Aqui é a Lara, especialista em milhas da Gestão de Milhas. Com quem tenho o prazer?"

ETAPA 2 — CURIOSIDADE
Pergunta aberta sobre cartões/milhas.
Exemplo: "Você já usa algum cartão que acumula pontos ou milhas?"

ETAPA 3 — QUALIFICAÇÃO (UMA pergunta por vez)
- Gasto mensal aproximado no cartão
- Quais cartões possui
- Tem milhas acumuladas? Quantas?
- Viaja quantas vezes por ano?

SINAIS DE LEAD QUENTE:
✅ Gasta R$20k+ no cartão
✅ Viaja 2x+ por ano
✅ Tem milhas paradas
✅ Não tem tempo para administrar

ETAPA 4 — CRIAR VALOR (2+ sinais positivos)
"Sabia que a maioria das pessoas perde até 40% do valor das milhas por não saber administrar?
A gente cuida de tudo — acúmulo inteligente, melhores resgates, passagens muito mais baratas.
Tudo sem você precisar mexer um dedo. 😉"

ETAPA 5 — MARCAR CALL
"Que tal um papo rápido de 20 minutinhos no Google Meet com o Caio, nosso consultor?
Sem compromisso — só para mostrar quanto você pode economizar. Você tem disponibilidade essa semana?"

Quando o lead CONFIRMAR data e horário, inclua [REPASSE] no final da sua mensagem.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
REGRAS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
- SEMPRE se apresente na primeira mensagem como Lara
- UMA pergunta por mensagem
- Nunca revelar preços
- Se gasta pouco/não viaja: encerre com gentileza
- Máximo 4 linhas por mensagem
- Linguagem informal mas profissional, emojis com moderação 😊

Se perguntarem o preço: "Os valores são personalizados — por isso a call é tão importante! O Caio apresenta tudo direitinho. 😊"

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
SOBRE IMAGENS E ÁUDIOS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
- Imagens (extrato, fatura, cartão): analise e use para qualificar
- Áudios: já chegam transcritos, responda normalmente
- Sempre confirme o que entendeu"""

# ─────────────────────────────────────────────
# PROMPT DE EXTRAÇÃO DE DADOS
# ─────────────────────────────────────────────

PROMPT_EXTRACAO = """Analise o histórico de conversa abaixo e extraia os dados do lead.
Retorne APENAS um JSON puro, sem markdown, sem explicações.
Se uma informação não foi mencionada, use null.

{
  "nome": "nome do lead ou null",
  "gasto_mensal": "valor mencionado ex: R$30.000 ou null",
  "cartoes_atuais": "cartões mencionados ou null",
  "milhas_atuais": "quantidade de milhas ou null",
  "tem_milhas": true ou false ou null,
  "destino_viagem": "destino mencionado ou null",
  "temperatura": "QUENTE se gasta 20k+ e quer agendar, MORNO se hesitante, FRIO se não qualificado, INDEFINIDO se sem dados",
  "data_agendamento": "data e hora confirmada ex: amanhã às 16h ou null",
  "observacoes": "qualquer info relevante adicional ou null"
}"""


def extrair_dados_conversa(historico: list[dict]) -> dict:
    """Usa GPT para extrair dados estruturados do histórico da conversa."""
    if not historico:
        return {}
    linhas = []
    for msg in historico:
        quem = "Lead" if msg.get("direcao") == "RECEBIDA" else "Lara"
        linhas.append(f"{quem}: {msg.get('conteudo', '')}")
    try:
        resposta = client.chat.completions.create(
            model=OPENAI_MODEL,
            messages=[
                {"role": "system", "content": PROMPT_EXTRACAO},
                {"role": "user", "content": "\n".join(linhas)},
            ],
            max_tokens=400,
            temperature=0,
        )
        texto = resposta.choices[0].message.content.strip()
        if "```" in texto:
            partes = texto.split("```")
            texto = partes[1] if len(partes) > 1 else partes[0]
            if texto.startswith("json"):
                texto = texto[4:]
        dados = json.loads(texto.strip())
        print(f"[Agent] Dados extraídos: {dados}")
        return dados
    except Exception as e:
        print(f"[Agent] Erro ao extrair dados: {e}")
        return {}


# ─────────────────────────────────────────────
# FUNÇÕES DE MÍDIA
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
    if "mp4" in mimetype:    sufixo = ".mp4"
    elif "mpeg" in mimetype: sufixo = ".mp3"
    elif "webm" in mimetype: sufixo = ".webm"
    tmp_path = None
    try:
        with tempfile.NamedTemporaryFile(suffix=sufixo, delete=False) as tmp:
            tmp.write(audio_bytes)
            tmp_path = tmp.name
        with open(tmp_path, "rb") as f:
            transcricao = client.audio.transcriptions.create(model="whisper-1", file=f, language="pt")
        texto = transcricao.text.strip()
        print(f"[Agent] Áudio transcrito: {texto[:80]}")
        return texto
    except Exception as e:
        print(f"[Agent] Erro transcrição: {e}")
        return "[não consegui transcrever o áudio, pode digitar sua mensagem?]"
    finally:
        if tmp_path and os.path.exists(tmp_path):
            os.unlink(tmp_path)


def analisar_imagem(url_midia: str = None, base64_midia: str = None, mimetype: str = "image/jpeg", legenda: str = "") -> str:
    conteudo_imagem = None
    if base64_midia:
        try:
            if "," in base64_midia:
                base64_midia = base64_midia.split(",", 1)[1]
            base64.b64decode(base64_midia)
            conteudo_imagem = {"type": "image_url", "image_url": {"url": f"data:{mimetype};base64,{base64_midia}", "detail": "low"}}
        except Exception as e:
            print(f"[Agent] Erro base64 imagem: {e}")
    if not conteudo_imagem and url_midia:
        conteudo_imagem = {"type": "image_url", "image_url": {"url": url_midia, "detail": "low"}}
    if not conteudo_imagem:
        return "[não consegui ver a imagem, pode descrever o que enviou?]"
    pergunta = "Analise essa imagem no contexto de gestão de milhas e cartões. Se for extrato/fatura, informe o valor gasto. Se for cartão, informe bandeira/banco. Seja objetivo e em português."
    if legenda:
        pergunta += f' O lead disse: "{legenda}"'
    try:
        resposta = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": [conteudo_imagem, {"type": "text", "text": pergunta}]}],
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
    numero = numero_raw
    lead = buscar_ou_criar_lead(numero, nome_contato)
    lead_id = lead["id"]

    if nome_contato and not lead.get("nome"):
        atualizar_lead(lead_id, {"nome": nome_contato})

    # ── Processa mídia ──
    if tipo_midia == "audio":
        texto_transcrito = transcrever_audio(url_midia, base64_midia, mimetype_midia or "audio/ogg")
        texto_para_gpt = f"[áudio transcrito]: {texto_transcrito}"
    elif tipo_midia == "imagem":
        descricao = analisar_imagem(url_midia, base64_midia, mimetype_midia or "image/jpeg", texto or "")
        texto_para_gpt = f"[imagem enviada — análise]: {descricao}"
        if texto:
            texto_para_gpt += f" | Legenda: {texto}"
    else:
        texto_para_gpt = texto or ""

    if not texto_para_gpt:
        return

    # ── Salva mensagem recebida ──
    salvar_mensagem(lead_id, "RECEBIDA", texto_para_gpt)

    # ── Busca histórico e monta contexto para o GPT ──
    historico = buscar_historico(lead_id, limite=20)
    mensagens = [{"role": "system", "content": SYSTEM_PROMPT}]
    for msg in historico:
        role = "user" if msg.get("direcao") == "RECEBIDA" else "assistant"
        mensagens.append({"role": role, "content": msg.get("conteudo", "")})

    # ── Chama o GPT ──
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

    fazer_repasse = "[REPASSE]" in texto_resposta
    texto_para_cliente = texto_resposta.replace("[REPASSE]", "").strip()

    # ── Salva resposta da Lara ──
    salvar_mensagem(lead_id, "ENVIADA", texto_para_cliente)

    if fazer_repasse:
        # 1. Extrai dados da conversa
        historico_completo = buscar_historico(lead_id, limite=30)
        dados = extrair_dados_conversa(historico_completo)

        # 2. Atualiza lead com os campos que existem na tabela
        campos = {
            "etapa": "repasse",
            "status": "qualificado",
            "temperatura": dados.get("temperatura") or "INDEFINIDO",
        }
        if dados.get("nome"):                    campos["nome"] = dados["nome"]
        if dados.get("gasto_mensal"):            campos["gasto_mensal"] = dados["gasto_mensal"]
        if dados.get("cartoes_atuais"):          campos["cartoes_atuais"] = dados["cartoes_atuais"]
        if dados.get("milhas_atuais"):           campos["milhas_atuais"] = dados["milhas_atuais"]
        if dados.get("tem_milhas") is not None:  campos["tem_milhas"] = dados["tem_milhas"]
        if dados.get("destino_viagem"):          campos["destino_viagem"] = dados["destino_viagem"]
        if dados.get("observacoes"):             campos["observacoes"] = dados["observacoes"]

        try:
            lead_atualizado = atualizar_lead(lead_id, campos)
        except Exception as e:
            print(f"[Agent] Erro atualizar lead (continuando mesmo assim): {e}")
            lead_atualizado = lead

        # 3. Cria agendamento
        data_call = dados.get("data_agendamento") or "A confirmar"
        try:
            criar_agendamento(lead_id, data_call)
        except Exception as e:
            print(f"[Agent] Erro criar agendamento: {e}")

        # 4. Envia ficha para o Caio (somente Caio!)
        try:
            executar_repasse(lead_atualizado or lead)
        except Exception as e:
            print(f"[Agent] Erro repasse: {e}")

        # 5. Envia confirmação para o cliente
        enviar_mensagem(numero, texto_para_cliente)
        print(f"[Agent] ✅ Repasse concluído — lead: {lead.get('nome')} | call: {data_call}")

    else:
        # Agenda follow-up se lead ainda em qualificação
        etapa_atual = lead.get("etapa", "ABERTURA")
        if etapa_atual not in ["repasse", "qualificado", "AGENDADO", "DESCARTADO"]:
            try:
                registrar_followup(lead_id, "PRIMEIRO_FOLLOWUP")
            except Exception:
                pass  # não crítico, não trava o fluxo

        enviar_mensagem(numero, texto_para_cliente)

    return texto_para_cliente
