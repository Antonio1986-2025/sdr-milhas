# Usa Python 3.12 como base (versão estável e leve)
FROM python:3.12-slim

# Define o diretório de trabalho dentro do container
WORKDIR /app

# Copia só o requirements primeiro (isso aproveita o cache do Docker)
COPY requirements.txt .

# Instala as dependências
RUN pip install --no-cache-dir -r requirements.txt

# Copia o resto do código
COPY . .

# Expõe a porta que o FastAPI vai usar
EXPOSE 8000

# Comando para iniciar o servidor
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
