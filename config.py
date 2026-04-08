import os
from dotenv import load_dotenv

# Carrega as variáveis do arquivo .env
load_dotenv()

# OpenAI
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")

# Supabase
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

# Evolution API (WhatsApp)
EVOLUTION_API_URL = os.getenv("EVOLUTION_API_URL")
EVOLUTION_API_KEY = os.getenv("EVOLUTION_API_KEY")
EVOLUTION_INSTANCE = os.getenv("EVOLUTION_INSTANCE")

# Configurações da Lara
NOME_ASSISTENTE = "Lara"
EMPRESA = "SDR Milhas"

# Número do Pedro (para receber fichas de repasse)
WHATSAPP_PEDRO = os.getenv("WHATSAPP_PEDRO")

# Porta do servidor
PORT = int(os.getenv("PORT", 8000))
