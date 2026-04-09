"""
followup.py
-----------
Workflow 2: roda a cada 30 minutos e reativa leads inativos.
No EasyPanel/servidor, isso vai rodar como uma thread separada em loop.
"""

import time
import threading
from datetime import datetime
from database import buscar_leads_para_followup, atualizar_lead, registrar_followup
from whatsapp import enviar_mensagem

# Intervalo entre cada verificação: 30 minutos em segundos
INTERVALO_SEGUNDOS = 30 * 60


def montar_mensagem_followup(lead: dict) -> str:
    """
    Escolhe a mensagem correta com base na tentativa.
    Primeira tentativa: mais amigável
    Segunda tentativa: despedida
    """
    nome = lead.get("nome", "")
    tentativas = lead.get("tentativas_followup", 0)

    if tentativas == 0:
        return f"Oi {nome}! 👋 Tava por aqui e lembrei de você. Caso queira continuar de onde a gente parou é só me chamar!"
    else:
        return f"Oi {nome}, última vez que passo por aqui — se um dia mudar de ideia sobre a gestão de milhas, é só me falar! 😊"


def esta_em_horario_comercial() -> bool:
    """
    Verifica se estamos dentro do horário permitido para envio:
    Segunda a sexta, das 8h às 20h.
    """
    agora = datetime.now()
    hora = agora.hour
    dia_semana = agora.weekday()  # 0 = segunda, 6 = domingo

    return (0 <= dia_semana <= 4) and (8 <= hora < 20)


def executar_followup_uma_vez():
    """
    Verifica e envia follow-ups para todos os leads elegíveis.
    Chamado a cada INTERVALO_SEGUNDOS.
    """
    if not esta_em_horario_comercial():
        print("[FOLLOWUP] Fora do horário comercial — pulando.")
        return

    leads = buscar_leads_para_followup()
    print(f"[FOLLOWUP] {len(leads)} leads para follow-up.")

    for lead in leads:
        try:
            tentativas = lead.get("tentativas_followup", 0)
            tipo = "PRIMEIRO_FOLLOWUP" if tentativas == 0 else "SEGUNDO_FOLLOWUP"

            # Envia a mensagem
            mensagem = montar_mensagem_followup(lead)
            enviar_mensagem(lead["whatsapp"], mensagem)

            # Atualiza o contador no banco
            novas_tentativas = tentativas + 1
            bloqueado = novas_tentativas >= 2  # bloqueia após 2 tentativas

            atualizar_lead(lead["id"], {
                "tentativas_followup": novas_tentativas,
                "bloqueado_followup": bloqueado,
            })

            # Registra o follow-up na tabela de log
            registrar_followup(lead["id"], tipo)

            status = "BLOQUEADO" if bloqueado else f"tentativa {novas_tentativas}"
            print(f"[FOLLOWUP] {lead.get('nome')} — {status}")

        except Exception as e:
            print(f"[FOLLOWUP] Erro no lead {lead.get('id')}: {e}")


def iniciar_loop_followup():
    """
    Inicia o loop de follow-up em uma thread separada.
    Assim o servidor principal (FastAPI) não é bloqueado.
    """
    def loop():
        print("[FOLLOWUP] Loop iniciado.")
        while True:
            executar_followup_uma_vez()
            time.sleep(INTERVALO_SEGUNDOS)

    thread = threading.Thread(target=loop, daemon=True)
    thread.start()
