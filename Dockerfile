FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

COPY pyproject.toml README.md alembic.ini ./
COPY alembic ./alembic
COPY src ./src
COPY docs ./docs
COPY tests ./tests
COPY build-doc.md ./build-doc.md
COPY .env.example ./.env.example

RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -e .[dev]

CMD ["python", "-m", "polymarket_scalper"]
