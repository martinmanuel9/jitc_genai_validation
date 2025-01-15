# Use Python 3.11 as base image
FROM python:3.11.9-slim

# Prevent prompts from apt
ENV DEBIAN_FRONTEND=noninteractive

# Install system dependencies & Poetry
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    git \
    curl \
    wget \
    && rm -rf /var/lib/apt/lists/* \
    && curl -sSL https://install.python-poetry.org | python3 -

# Add Poetry to PATH
ENV PATH="/root/.local/bin:$PATH"

# Create a working directory
WORKDIR /app

# Copy only Poetry lock files first (better for caching)
COPY pyproject.toml poetry.lock ./

# Install dependencies with Poetry
RUN poetry config virtualenvs.create false \
    && poetry install --no-interaction --no-ansi

# Now copy everything else (source code, .env, etc.)
COPY . .

# (Optional) If your code references .env at runtime,
# you can confirm it’s present or load it in your code directly.
# In some setups, you might handle environment variables differently.

# Expose FastAPI port
EXPOSE 8000

# If your entry point is src/app/main.py, you can directly call uvicorn:
CMD ["uvicorn", "src.app.main:app", "--host", "0.0.0.0", "--port", "8000"]
