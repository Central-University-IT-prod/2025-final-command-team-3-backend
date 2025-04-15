FROM python:3.11-slim

WORKDIR /app
COPY pyproject.toml poetry.lock* ./
COPY src/ /app/src

RUN apt-get update \
    && apt-get install -y --no-install-recommends gcc libpq-dev \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir poetry

RUN poetry config virtualenvs.create false
RUN poetry install --only main

EXPOSE 80
CMD ["uvicorn", "src.app.main:app", "--port", "80", "--host=0.0.0.0"]