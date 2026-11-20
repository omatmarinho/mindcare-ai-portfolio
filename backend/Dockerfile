# Imagem da API FastAPI do MindCare AI
FROM python:3.12-slim

# WITH_LOCAL_AI=true instala o Whisper (IA real). A demonstração usa a IA simulada.
ARG WITH_LOCAL_AI=false

ENV PYTHONDONTWRITEBYTECODE=1     PYTHONUNBUFFERED=1     PIP_NO_CACHE_DIR=1     HF_HOME=/home/app/.cache/huggingface

WORKDIR /app

COPY requirements.txt requirements-ai.txt ./
RUN pip install -r requirements.txt  && if [ "$WITH_LOCAL_AI" = "true" ]; then pip install -r requirements-ai.txt; fi

COPY . .

# Roda como usuário sem privilégios (nunca como root)
RUN useradd --create-home --uid 10001 app && chown -R app /app
USER app

EXPOSE 8000

# Aplica as migrações e sobe a API. PORT vem da hospedagem (padrão 8000).
# --proxy-headers: usa o IP do visitante repassado pelo frontend (X-Forwarded-For).
# Seguro porque, com INTERNAL_API_KEY, a API só aceita chamadas do próprio frontend.
CMD ["sh", "-c", "alembic upgrade head && uvicorn main:app --host 0.0.0.0 --port ${PORT:-8000} --proxy-headers --forwarded-allow-ips '*'"]
