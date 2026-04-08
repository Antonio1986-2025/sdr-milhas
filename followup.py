import time
from database import buscar_followups_pendentes, marcar_followup_enviado
from whatsapp import enviar_mensagem

INTERVALO_SEGUNDOS = 60  # verifica a cada 1 minuto


def executar_followups():
    """Verifica e envia todos os follow-ups pendentes."""
    pendentes = buscar_followups_pendentes()

    if not pendentes:
        print("[Followup] Nenhum follow-up pendente.")
        return

    for followup in pendentes:
        lead = followup.get("leads", {})
        numero = lead.get("whatsapp")
        mensagem = followup.get("mensagem")

        if numero and mensagem:
            sucesso = enviar_mensagem(numero, mensagem)
            if sucesso:
                marcar_followup_enviado(followup["id"])
                print(f"[Followup] Enviado para {numero}")
        else:
            print(f"[Followup] Dados incompletos para followup {followup['id']}")


def iniciar_loop():
    """Inicia o loop de verificação de follow-ups."""
    print(f"[Followup] Loop iniciado. Verificando a cada {INTERVALO_SEGUNDOS}s...")
    while True:
        try:
            executar_followups()
        except Exception as e:
            print(f"[Followup] Erro no loop: {e}")
        time.sleep(INTERVALO_SEGUNDOS)


if __name__ == "__main__":
    iniciar_loop()
