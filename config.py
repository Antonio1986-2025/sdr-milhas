import os

# ─────────────────────────────────────────────
# SUPABASE
# ─────────────────────────────────────────────
SUPABASE_URL = os.getenv("SUPABASE_URL", "https://irnnouhlvtapdkcvlank.supabase.co")
SUPABASE_KEY = os.getenv("SUPABASE_KEY", "")

# ─────────────────────────────────────────────
# EVOLUTION API (WhatsApp)
# ─────────────────────────────────────────────
EVOLUTION_URL      = os.getenv("EVOLUTION_URL", "https://robert-appp-evolution-api.mpysnt.easypanel.host")
EVOLUTION_KEY      = os.getenv("EVOLUTION_KEY", "")
EVOLUTION_INSTANCE = os.getenv("EVOLUTION_INSTANCE", "sdr-milhas")

# ─────────────────────────────────────────────
# OPENAI
# ─────────────────────────────────────────────
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
OPENAI_MODEL   = os.getenv("OPENAI_MODEL", "gpt-4o-mini")

# ─────────────────────────────────────────────
# CONTATOS
# ─────────────────────────────────────────────
NOME_ASSISTENTE = "Lara"
EMPRESA         = "Gestão de Milhas"

# Fechador: Caio
WHATSAPP_PEDRO = os.getenv("WHATSAPP_PEDRO", "5567999020392")  # Caio

# ─────────────────────────────────────────────
# APP
# ─────────────────────────────────────────────
PORT = int(os.getenv("PORT", 8000))
