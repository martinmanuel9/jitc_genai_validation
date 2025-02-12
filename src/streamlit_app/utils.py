import os
import fitz
import tempfile
from PyPDF2 import PdfReader
from sentence_transformers import SentenceTransformer
import requests

# ChromaDB API endpoint
CHROMADB_API = "http://chromadb:8000"

# Load Sentence Transformer model
embedding_model = SentenceTransformer('multi-qa-mpnet-base-dot-v1')

# Fetch existing collections from ChromaDB
def fetch_collections():
    response = requests.get(f"{CHROMADB_API}/collections")
    if response.status_code == 200:
        return response.json()
    return []

# Extract and chunk text from PDFs
def extract_and_chunk_text_from_pdf(pdf_path, max_chunk_size=512):
    """Extracts text from a PDF file and splits it into chunks of `max_chunk_size` tokens."""
    reader = PdfReader(pdf_path)
    text = ""
    
    for page in reader.pages:
        extracted_text = page.extract_text()
        if extracted_text:
            text += extracted_text + "\n"

    # Split text into chunks
    sentences = text.split(". ")
    chunks = []
    current_chunk = ""

    for sentence in sentences:
        if len(current_chunk.split()) + len(sentence.split()) <= max_chunk_size:
            current_chunk += sentence + ". "
        else:
            chunks.append(current_chunk.strip())
            current_chunk = sentence + ". "

    if current_chunk:
        chunks.append(current_chunk.strip())

    return chunks

# Store PDFs in ChromaDB
def store_pdfs_in_chromadb(uploaded_files, collection_name, distance_metric="cosine"):
    """Stores PDF documents in ChromaDB with generated embeddings."""
    requests.post(f"{CHROMADB_API}/collection/create", params={"collection_name": collection_name})

    for uploaded_file in uploaded_files:
        # Save the file temporarily
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as temp_pdf:
            temp_pdf.write(uploaded_file.getvalue())
            temp_pdf_path = temp_pdf.name

        # Extract text chunks
        chunks = extract_and_chunk_text_from_pdf(temp_pdf_path)

        # Generate embeddings
        embeddings = embedding_model.encode(chunks).tolist()

        # Prepare metadata and IDs
        metadatas = [{"document_name": uploaded_file.name} for _ in range(len(chunks))]
        ids = [f"{uploaded_file.name}_chunk_{i}" for i in range(len(chunks))]

        # Insert into ChromaDB
        payload = {
            "collection_name": collection_name,
            "documents": chunks,
            "ids": ids,
            "metadatas": metadatas
        }
        response = requests.post(f"{CHROMADB_API}/documents/add", json=payload)

        # Cleanup
        os.remove(temp_pdf_path)

        if response.status_code == 200:
            print(f"Stored {uploaded_file.name} in collection '{collection_name}'.")
        else:
            print(f"Error storing {uploaded_file.name}: {response.json()}")

# List all stored chunks in a collection with metadata
def list_all_chunks_with_scores(collection_name, query_text=None):
    """Lists all stored chunks in a ChromaDB collection with optional query scores."""
    # First get all documents
    response = requests.get(f"{CHROMADB_API}/documents", params={"collection_name": collection_name})
    
    if response.status_code != 200:
        print(f"Error fetching documents: {response.text}")
        return []

    docs = response.json()
    if "ids" not in docs or "documents" not in docs:
        return []

    # If there's a query, get the scores
    scores_dict = {}
    if query_text:
        query_embedding = embedding_model.encode([query_text]).tolist()
        query_payload = {
            "query_embeddings": query_embedding,
            "n_results": len(docs["ids"]),  # Get scores for all documents
            "include": ["metadatas", "distances"]
        }
        score_response = requests.post(
            f"{CHROMADB_API}/documents/query", 
            json={"collection_name": collection_name, **query_payload}
        )
        if score_response.status_code == 200:
            score_results = score_response.json()
            scores_dict = {
                doc_id: round(distance, 4)
                for doc_id, distance in zip(score_results["ids"][0], score_results["distances"][0])
            }

    # Combine document info with scores
    return [
        {
            "Chunk ID": f"`{doc_id}`",
            "Document": f">{doc_text[:250] + '...' if len(doc_text) > 250 else doc_text}",
            "Metadata": f"**{(metadata or {}).get('document_name', 'Unknown')}**",
            "Score": scores_dict.get(doc_id, "N/A")  # Add score if query was provided
        }
        for doc_id, doc_text, metadata in zip(
            docs["ids"], 
            docs["documents"], 
            docs.get("metadatas", [{}] * len(docs["ids"]))
        )
    ]

