FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

ENV POETRY_VERSION=1.5.1

RUN curl -sSL https://install.python-poetry.org | python3 - && \
    ln -s /root/.local/bin/poetry /usr/local/bin/poetry

RUN poetry config virtualenvs.create false

RUN mkdir /vitact
WORKDIR /vitact

COPY pyproject.toml poetry.lock* /vitact/

RUN poetry install --no-root --no-interaction --no-ansi

COPY . /vitact

CMD ["python", "vitact/main.py"] 
