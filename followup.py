"""
followup.py — Loop automático que reativa leads inativos a cada 30 minutos.
"""

import time
import threading
from datetime import datetime
from database import buscar_leads_para_followup, atualizar_lead, registrar_followup
from whatsapp import enviar_mensagem

INTERVALO_SEGUNDOS = 30 * 60  # 30 minutos


def esta_em_horario_comercial() -> bool:
    agora = datetime.now()
    return (0 <= agora.weekday() <= 4) and (8 <= agora.hour < 20)


def montar_mensagem_followup(lead: dict) -> str:
    nome = lead.get("nome") or ""
    tentativas = lead.get("tentativas_followup", 0)
    if tentativas == 0:
        return f"Oi {nome}! 👋 Tava por aqui e lembrei de você. Caso queira continuar de onde a gente parou é só me chamar!"
    return f"Oi {nome}, última vez que passo por aqui — se um dia mudar de ideia sobre a gestão de milhas, é só me falar! 😊"


def executar_followups():
    if not esta_em_horario_comercial():
        print("[Followup] Fora do horário comercial — pulando.")
        return

    leads = buscar_leads_para_followup()
    print(f"[Followup] {len(leads)} leads para follow-up.")

    for lead in leads:
        try:
            tentativas = lead.get("tentativas_followup", 0)
            tipo = "PRIMEIRO_FOLLOWUP" if tentativas == 0 else "SEGUNDO_FOLLOWUP"
            mensagem = montar_mensagem_followup(lead)
            enviar_mensagem(lead["whatsapp"], mensagem)
            novas_tentativas = tentativas + 1
            bloqueado = novas_tentativas >= 2
            atualizar_lead(lead["id"], {
                "tentativas_followup": novas_tentativas,
                "bloqueado_followup": bloqueado,
            })
            registrar_followup(lead["id"], tipo)
            print(f"[Followup] {lead.get('nome')} — tentativa {novas_tentativas}")
        except Exception as e:
            print(f"[Followup] Erro no lead {lead.get('id')}: {e}")


def iniciar_loop_followup():
    """Inicia o loop em thread separada — nome exportado para main.py."""
    def loop():
        print("[Followup] Loop iniciado.")
        while True:
            try:
                executar_followups()
            except Exception as e:
                print(f"[Followup] Erro no loop: {e}")
            time.sleep(INTERVALO_SEGUNDOS)

    thread = threading.Thread(target=loop, daemon=True)
    thread.start()
