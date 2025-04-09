#!/bin/bash
# Platform-agnostic JITC GENAI Validation System setup

# Configuration - change these as needed
PROJECT_NAME="jitc_genai_validation"
REPO_URL="https://github.com/martinmanuel9/jitc_genai_validation.git"

echo "Setting up $PROJECT_NAME..."

# Check for Docker
if ! command -v docker &> /dev/null; then
    echo "Docker not found!"
    echo "Please install Docker Desktop from https://www.docker.com/products/docker-desktop"
    exit 1
fi

# Check for docker-compose or docker compose
DOCKER_COMPOSE_CMD=""
if command -v docker-compose &> /dev/null; then
    DOCKER_COMPOSE_CMD="docker-compose"
elif docker compose version &> /dev/null; then
    DOCKER_COMPOSE_CMD="docker compose"
else
    echo "Neither docker-compose nor docker compose found!"
    echo "Please install Docker Desktop or Docker Compose plugin"
    exit 1
fi

echo "Using compose command: $DOCKER_COMPOSE_CMD"

# Check for .env file
if [ ! -f ".env" ]; then
    echo "Error: .env file not found in the current directory."
    echo "Please create a .env file with your API keys and configuration before running this script."
    exit 1
fi

# Create project directory in user's home folder
PROJECT_DIR="$HOME/$PROJECT_NAME"
DATA_DIR="$PROJECT_DIR/data"
MODEL_DIR="$PROJECT_DIR/models"

# Create directories
mkdir -p "$PROJECT_DIR"
mkdir -p "$DATA_DIR/chromadb"
mkdir -p "$DATA_DIR/postgres"
mkdir -p "$DATA_DIR/huggingface_cache"
mkdir -p "$MODEL_DIR"

# Get the code (clone or update)
if [ -d "$PROJECT_DIR/.git" ]; then
    echo "Updating existing repository..."
    cd "$PROJECT_DIR"
    git pull
else
    echo "Cloning repository..."
    git clone "$REPO_URL" "$PROJECT_DIR"
    cd "$PROJECT_DIR"
fi

# Copy the existing .env file to the project directory
echo "Copying .env file to project directory..."
cp .env "$PROJECT_DIR/.env"

# Update docker-compose.yml to use the persistent model directory
echo "Updating docker-compose.yml for persistent model storage..."
MODEL_PATH="$HOME/$PROJECT_NAME/models"
CHROMADB_PATH="$HOME/$PROJECT_NAME/data/chromadb"
POSTGRES_PATH="$HOME/$PROJECT_NAME/data/postgres"
HUGGINGFACE_PATH="$HOME/$PROJECT_NAME/data/huggingface_cache"

# Function to check and update docker-compose.yml
update_docker_compose() {
    # Make a backup first
    cp docker-compose.yml docker-compose.yml.bak
    
    # Replace volume mappings with absolute paths
    sed -i.bak "s|llama_data:/root/.ollama|$MODEL_PATH:/root/.ollama|g" docker-compose.yml
    sed -i.bak "s|chromadb_data:/app/chroma_db_data|$CHROMADB_PATH:/app/chroma_db_data|g" docker-compose.yml
    sed -i.bak "s|pg_data:/var/lib/postgresql/data|$POSTGRES_PATH:/var/lib/postgresql/data|g" docker-compose.yml
    sed -i.bak "s|huggingface_cache_data:/app/huggingface_cache|$HUGGINGFACE_PATH:/app/huggingface_cache|g" docker-compose.yml
    
    # Update entrypoint for llama service to not re-download models
    sed -i.bak 's|"ollama serve & sleep 5 && ollama pull.*"|"ollama serve & wait"|g' docker-compose.yml
    
    # Remove named volumes since we're using directory mounts
    sed -i.bak '/^volumes:/,$d' docker-compose.yml
    
    echo "docker-compose.yml updated successfully."
}

# Execute the update function
update_docker_compose

# Ask about downloading the models
echo "Would you like to download the Llama3, Mistral, and Gemma models now? (y/n)"
echo "Note: This is a one-time download (about 12GB total) and will be reused in the future."
read download_answer
if [ "$download_answer" == "y" ] || [ "$download_answer" == "Y" ]; then
    # Create a temporary Dockerfile for downloading
    TEMP_DIR=$(mktemp -d)
    echo "Creating temporary download environment in $TEMP_DIR"
    
    cat > "$TEMP_DIR/Dockerfile" << EOL
FROM ollama/ollama:latest
WORKDIR /app
ENTRYPOINT ["/bin/sh"]
EOL

    # Build a temporary image for downloading
    echo "Building temporary download container..."
    docker build -t ollama-downloader "$TEMP_DIR"
    
    # Create directory for logs
    LOGS_DIR="$PROJECT_DIR/logs"
    mkdir -p "$LOGS_DIR"
    
    # Download each model
    for model in llama3 mistral gemma; do
        echo "======================================"
        echo "Starting download of $model..."
        echo "This may take a long time depending on your internet speed."
        echo "======================================"
        
        # Start timing
        start_time=$(date +%s)
        
        # Run a container that downloads the model
        echo "Running container to download $model to $MODEL_DIR..."
        docker run --rm -v "$MODEL_DIR:/root/.ollama" ollama-downloader -c "ollama serve & sleep 5 && ollama pull $model && echo 'Download complete' && ls -la /root/.ollama/models" | tee "$LOGS_DIR/${model}_download.log"
        
        # Check if download was successful by looking for model files
        if [ -d "$MODEL_DIR/models" ] && find "$MODEL_DIR/models" -name "*$model*" | grep -q .; then
            # End timing
            end_time=$(date +%s)
            duration=$((end_time - start_time))
            minutes=$((duration / 60))
            seconds=$((duration % 60))
            
            echo "✅ $model downloaded successfully in ${minutes}m ${seconds}s!"
        else
            echo "❌ Error: Failed to download $model. Check logs for details."
            echo "Will try again with an alternative method..."
            
            # Try an alternative method - simpler approach
            docker run --rm -v "$MODEL_DIR:/root/.ollama" ollama/ollama pull $model
            
            # Check again
            if [ -d "$MODEL_DIR/models" ] && find "$MODEL_DIR/models" -name "*$model*" | grep -q .; then
                echo "✅ $model downloaded successfully with alternative method!"
            else
                echo "❌ Error: Could not download $model after multiple attempts."
                echo "Please download it manually after the system is running."
            fi
        fi
    done
    
    # Check and report what models were actually downloaded
    echo "======================================"
    echo "Download summary"
    echo "======================================"
    echo "Models directory content:"
    ls -la "$MODEL_DIR/models" 2>/dev/null || echo "No models directory found"
    
    # Check for each model specifically
    for model in llama3 mistral gemma; do
        if [ -d "$MODEL_DIR/models" ] && find "$MODEL_DIR/models" -name "*$model*" | grep -q .; then
            echo "✅ $model: DOWNLOADED"
        else
            echo "❌ $model: NOT FOUND"
        fi
    done
    
    # Clean up
    echo "Removing temporary download image..."
    docker rmi ollama-downloader
    rm -rf "$TEMP_DIR"
    
    echo "======================================"
    echo "To manually download any missing models after system startup:"
    echo "docker exec -it llama ollama pull <model_name>"
    echo "======================================"
else
    echo "Skipping model download."
fi

# Create the Dockerfile.ollama if it doesn't exist or update it
cat > "$PROJECT_DIR/Dockerfile.ollama" << EOL
FROM ollama/ollama:latest

# Expose Ollama API port
EXPOSE 11434

# Just start Ollama server (no downloads needed as models are mounted)
ENTRYPOINT ["/bin/sh", "-c", "ollama serve & wait"]
EOL

# Create simple start/stop scripts that handle both docker-compose formats
cat > "$PROJECT_DIR/start.sh" << EOL
#!/bin/bash
cd "\$(dirname "\$0")"

# Determine which docker compose command to use
if command -v docker-compose &> /dev/null; then
    docker-compose up --build -d
elif docker compose version &> /dev/null; then
    docker compose up --build -d
else
    echo "Error: Neither docker-compose nor docker compose found"
    exit 1
fi

echo "JITC GENAI Validation System started. Access the UI at http://localhost:8501"
EOL

cat > "$PROJECT_DIR/stop.sh" << EOL
#!/bin/bash
cd "\$(dirname "\$0")"

# Determine which docker compose command to use
if command -v docker-compose &> /dev/null; then
    docker-compose down -v
elif docker compose version &> /dev/null; then
    docker compose down -v
else
    echo "Error: Neither docker-compose nor docker compose found"
    exit 1
fi

echo "JITC GENAI Validation System stopped."
EOL

# Make scripts executable
chmod +x "$PROJECT_DIR/start.sh"
chmod +x "$PROJECT_DIR/stop.sh"

echo "Installation complete!"
echo "To start the system: $PROJECT_DIR/start.sh"
echo "To stop the system: $PROJECT_DIR/stop.sh"
echo ""
echo "Would you like to start the system now? (y/n)"
read answer
if [ "$answer" == "y" ] || [ "$answer" == "Y" ]; then
    "$PROJECT_DIR/start.sh"
fi