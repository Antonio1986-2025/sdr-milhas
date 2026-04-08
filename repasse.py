from openai import OpenAI
from config import OPENAI_API_KEY, OPENAI_MODEL, WHATSAPP_PEDRO
from database import buscar_lead_por_whatsapp, salvar_ficha_repasse
from supabase import create_client
from config import SUPABASE_URL, SUPABASE_KEY
from whatsapp import enviar_mensagem

client = OpenAI(api_key=OPENAI_API_KEY)
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)


def buscar_lead_por_id(lead_id: str):
    """Busca um lead pelo ID."""
    resultado = (
        supabase.table("leads")
        .select("*")
        .eq("id", lead_id)
        .single()
        .execute()
    )
    return resultado.data


def gerar_ficha(lead: dict, historico: list) -> str:
    """Usa o GPT para gerar um resumo estruturado do lead."""
    
    historico_texto = "\n".join(
        [f"{'Cliente' if m['papel'] == 'usuario' else 'Lara'}: {m['conteudo']}" for m in historico]
    )

    prompt = f"""Com base nessa conversa de WhatsApp, gere uma ficha de repasse resumida para o vendedor Pedro.

CONVERSA:
{historico_texto}

DADOS DO LEAD:
- Nome: {lead.get('nome', 'Não informado')}
- WhatsApp: {lead.get('whatsapp', '')}
- E-mail: {lead.get('email', 'Não informado')}
- Status: {lead.get('status', '')}

Gere a ficha neste formato:
👤 *FICHA DE REPASSE*
---
*Nome:* 
*WhatsApp:* 
*E-mail:* 
*Interesse principal:* 
*Resumo da conversa:* 
*Próximo passo sugerido:* 
---
"""

    try:
        resposta = client.chat.completions.create(
            model=OPENAI_MODEL,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=400,
            temperature=0.3,
        )
        return resposta.choices[0].message.content.strip()
    except Exception as e:
        print(f"[Repasse] Erro ao gerar ficha: {e}")
        return f"Ficha de repasse — Lead: {lead.get('nome')} | WhatsApp: {lead.get('whatsapp')}"


def gerar_e_enviar_ficha(lead_id: str, historico: list):
    """Gera a ficha do lead e envia para o Pedro no WhatsApp."""
    
    lead = buscar_lead_por_id(lead_id)
    if not lead:
        print(f"[Repasse] Lead {lead_id} não encontrado.")
        return

    ficha = gerar_ficha(lead, historico)
    
    # Salva a ficha no banco
    salvar_ficha_repasse(lead_id, ficha)

    # Envia para o Pedro
    if WHATSAPP_PEDRO:
        enviar_mensagem(WHATSAPP_PEDRO, ficha)
        print(f"[Repasse] Ficha enviada para Pedro ({WHATSAPP_PEDRO})")
    else:
        print("[Repasse] WHATSAPP_PEDRO não configurado no .env")
