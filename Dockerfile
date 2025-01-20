FROM python:3.11.9-slim

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    git \
    python3-dev \
    curl \
    wget \
    && rm -rf /var/lib/apt/lists/*

# Set up working directory
WORKDIR /app

# Clone Chroma repository from GitHub
RUN git clone https://github.com/chroma-core/chroma.git

# Set working directory to the cloned repository
WORKDIR /app/chroma

# Install Python dependencies
RUN pip install --upgrade pip \
    && pip install poetry \
    && poetry config virtualenvs.create false \
    && poetry install --no-interaction --no-ansi

# Expose the Chroma API port
EXPOSE 8001

# Command to start Chroma
CMD ["uvicorn", "chromadb.app:app", "--host", "0.0.0.0", "--port", "8001"]
