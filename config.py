import os

# OpenAI
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
OPENAI_MODEL = os.environ.get("OPENAI_MODEL", "gpt-4o-mini")

# Supabase
SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")

# Evolution API (WhatsApp)
EVOLUTION_API_URL = os.environ.get("EVOLUTION_URL")
EVOLUTION_API_KEY = os.environ.get("EVOLUTION_KEY")
EVOLUTION_INSTANCE = os.environ.get("EVOLUTION_INSTANCE")

# Configurações da Lara
NOME_ASSISTENTE = "Lara"
EMPRESA = "SDR Milhas"

# Número do Pedro
WHATSAPP_PEDRO = os.environ.get("WHATSAPP_PEDRO")

# Porta
PORT = int(os.environ.get("PORT", 8000))