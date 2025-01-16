FROM python:3.11.9-slim

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    python3-dev \
    curl \
    wget \
    git \
    && rm -rf /var/lib/apt/lists/*

# Install Poetry
RUN curl -sSL https://install.python-poetry.org | python3 - --version 1.5.1

ENV PATH="/root/.local/bin:$PATH"

WORKDIR /app

# Copy Poetry files first
COPY pyproject.toml poetry.lock ./

# Install dependencies with logs
# RUN poetry config virtualenvs.create false \
#     && poetry install --no-interaction --no-ansi --verbose || cat /root/.cache/pypoetry/log/debug.log

# Copy the remaining code
COPY . .

EXPOSE 8000

CMD ["uvicorn", "src.app.main:app", "--host", "0.0.0.0", "--port", "8000"]
