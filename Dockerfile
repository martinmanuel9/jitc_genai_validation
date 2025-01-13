# Use Python 3.11 as base image
FROM python:3.11.9-slim

# Set working directory to the directory containing main.py
WORKDIR /app/src/app

# Install system dependencies and Poetry
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    git \
    curl \
    wget \
    && rm -rf /var/lib/apt/lists/* \
    && curl -sSL https://install.python-poetry.org | python3 -

# Add Poetry to PATH
ENV PATH="/root/.local/bin:$PATH"

# Copy Poetry files to root of app directory
WORKDIR /app
COPY pyproject.toml poetry.lock ./

# Install dependencies with Poetry
RUN poetry config virtualenvs.create false \
    && poetry install --no-interaction --no-ansi

# Copy the .env file to the image
COPY .env /app

# Copy the rest of the application code into /app
COPY . .

# Expose ports for vector database and FastAPI
EXPOSE 19530 8000

# Set working directory back to src/app
WORKDIR /app/src/app

# Set default command to start FastAPI server with Uvicorn
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
