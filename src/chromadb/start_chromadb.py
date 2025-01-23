import os
import uvicorn
from fastapi import FastAPI
from chromadb.config import Settings
from chromadb import Client

# Where ChromaDB should persist data (overridden by CHROMADB_PERSIST_DIRECTORY, if set)
PERSIST_DIR = os.getenv("CHROMADB_PERSIST_DIRECTORY", "/app/chroma_db_data")

# Configure Chroma
settings = Settings(
    persist_directory=PERSIST_DIR,
    anonymized_telemetry=False  # optional
)

# Create a ChromaDB client
chroma_client = Client(settings)

# Create a standard FastAPI app
app = FastAPI(title="ChromaDB Dockerized")

@app.get("/")
def health_check():
    """Basic health check."""
    return {"status": "ok", "detail": "ChromaDB custom server running."}

@app.get("/collections")
def list_collections():
    """List all ChromaDB collections (example endpoint)."""
    return [c.name for c in chroma_client.list_collections()]

# Run with Uvicorn if called directly
if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
