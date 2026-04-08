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
from whatsapp import enviar_mensagem, formatar_numero
from repasse import gerar_e_enviar_ficha
from datetime import datetime, timedelta

client = OpenAI(api_key=OPENAI_API_KEY)

SYSTEM_PROMPT = f"""Você é {NOME_ASSISTENTE}, assistente de vendas da {EMPRESA}.

Seu objetivo é:
1. Recepcionar leads que chegam pelo WhatsApp com simpatia e profissionalismo
2. Entender o interesse do cliente (compra ou venda de milhas, passagens, etc.)
3. Coletar informações importantes: nome, e-mail, origem do interesse
4. Qualificar o lead e mover ele pelo funil de vendas
5. Quando o lead estiver qualificado, gerar uma ficha de repasse para o Pedro

Regras importantes:
- Seja simpática, direta e objetiva
- Use linguagem informal mas profissional
- Nunca invente informações sobre preços ou disponibilidade
- Se o cliente perguntar algo que você não sabe, diga que vai verificar e acionar o time
- Quando tiver nome, e-mail e interesse claro do cliente, diga: [REPASSE] para acionar o Pedro

Etapas do funil: interesse → qualificação → repasse → fechamento
"""


def processar_mensagem(numero_raw: str, texto: str, nome_contato: str = ""):
    """Processa uma mensagem recebida do WhatsApp e responde."""
    
    numero = formatar_numero(numero_raw)
    
    # Busca ou cria o lead no banco
    lead = buscar_ou_criar_lead(numero, nome_contato)
    lead_id = lead["id"]

    # Atualiza nome se veio do webhook e ainda não está salvo
    if nome_contato and not lead.get("nome"):
        atualizar_lead(lead_id, {"nome": nome_contato})

    # Salva a mensagem do usuário
    salvar_mensagem(lead_id, "usuario", texto)

    # Busca histórico de conversa
    historico = buscar_historico(lead_id)

    # Monta as mensagens para o GPT
    mensagens = [{"role": "system", "content": SYSTEM_PROMPT}]
    for msg in historico:
        role = "user" if msg["papel"] == "usuario" else "assistant"
        mensagens.append({"role": role, "content": msg["conteudo"]})

    # Chama o GPT
    try:
        resposta = client.chat.completions.create(
            model=OPENAI_MODEL,
            messages=mensagens,
            max_tokens=500,
            temperature=0.7,
        )
        texto_resposta = resposta.choices[0].message.content.strip()
    except Exception as e:
        print(f"[Agent] Erro ao chamar OpenAI: {e}")
        texto_resposta = "Oi! Tive um probleminha aqui, pode repetir sua mensagem?"

    # Salva a resposta da Lara
    salvar_mensagem(lead_id, "assistente", texto_resposta)

    # Verifica se deve acionar o repasse
    if "[REPASSE]" in texto_resposta:
        texto_resposta = texto_resposta.replace("[REPASSE]", "").strip()
        atualizar_lead(lead_id, {"etapa": "repasse", "status": "qualificado"})
        gerar_e_enviar_ficha(lead_id, historico)
    
    # Agenda follow-up para 24h se o lead ainda estiver em qualificação
    if lead.get("etapa") == "interesse":
        followup_em = (datetime.utcnow() + timedelta(hours=24)).isoformat()
        criar_followup(
            lead_id,
            f"Oi {lead.get('nome') or ''}! Ainda posso te ajudar com milhas? 😊",
            followup_em,
        )

    # Envia a resposta pelo WhatsApp
    enviar_mensagem(numero, texto_resposta)

    return texto_resposta
