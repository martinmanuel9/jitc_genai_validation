import os
import re
import tempfile
import time
import requests
from PyPDF2 import PdfReader
from sentence_transformers import SentenceTransformer

# ChromaDB API endpoint
CHROMADB_API = "http://chromadb:8020"

# Load Sentence Transformer model (multi-qa-mpnet-base-dot-v1 outputs 768-d vectors)
embedding_model = SentenceTransformer('multi-qa-mpnet-base-dot-v1')


def fetch_collections():
    """Fetch list of available collections from ChromaDB with retries."""
    for i in range(5):  # Try 5 times
        try:
            response = requests.get(f"{CHROMADB_API}/collections")
            if response.status_code == 200:
                data = response.json()
                if isinstance(data, dict) and "collections" in data:
                    return data["collections"]
                else:
                    return data
        except requests.ConnectionError:
            print(f"ChromaDB not ready, retrying {i+1}/5...")
            time.sleep(5)
    return []


def extract_sections_from_pdf(pdf_path):
    """
    Extract full text from a PDF and split it into sections based on headings.
    This regex assumes section headings start with a number followed by a dot and a space.
    Adjust the regex as needed for your documents. Change this so that we can do it based on sections of standards. 
    """
    reader = PdfReader(pdf_path)
    full_text = ""
    for page in reader.pages:
        text = page.extract_text()
        if text:
            full_text += text + "\n"
    
    # Split text into sections using regex: look for a newline that is followed by one or more digits, a period, and a space.
    sections = re.split(r'\n(?=\d+\.\s)', full_text)
    # Clean up sections
    sections = [section.strip() for section in sections if section.strip()]
    return sections


def store_pdfs_in_chromadb(uploaded_files, collection_name, distance_metric="cosine"):
    """Stores PDF documents in ChromaDB by splitting them into sections based on headings."""
    # Ensure the collection exists
    requests.post(f"{CHROMADB_API}/collection/create", params={"collection_name": collection_name})

    for uploaded_file in uploaded_files:
        # Save the file temporarily
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as temp_pdf:
            temp_pdf.write(uploaded_file.getvalue())
            temp_pdf_path = temp_pdf.name

        # Extract sections from the PDF
        sections = extract_sections_from_pdf(temp_pdf_path)
        if not sections:
            # Fallback: if no sections were found, store the entire document as one section.
            with open(temp_pdf_path, 'r', encoding="utf8") as f:
                sections = [f.read()]

        # Generate embeddings for each section
        embeddings = embedding_model.encode(sections).tolist()
        print("Embedding dimension:", len(embeddings[0]))  # Should print 768

        # Prepare metadata and IDs
        metadatas = [{"document_name": uploaded_file.name} for _ in range(len(sections))]
        ids = [f"{uploaded_file.name}_section_{i}" for i in range(len(sections))]

        # Build payload including the embeddings
        payload = {
            "collection_name": collection_name,
            "documents": sections,
            "ids": ids,
            "metadatas": metadatas,
            "embeddings": embeddings
        }
        response = requests.post(f"{CHROMADB_API}/documents/add", json=payload)

        # Cleanup temporary file
        os.remove(temp_pdf_path)

        if response.status_code == 200:
            print(f"Stored {uploaded_file.name} in collection '{collection_name}'.")
        else:
            print(f"Error storing {uploaded_file.name}: {response.json()}")


def list_all_chunks_with_scores(collection_name, query_text=None):
    """Lists all stored document sections in a ChromaDB collection with optional query scores."""
    # First, get all documents
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
            "Score": scores_dict.get(doc_id, "N/A")
        }
        for doc_id, doc_text, metadata in zip(
            docs["ids"],
            docs["documents"],
            docs.get("metadatas", [{}] * len(docs["ids"]))
        )
    ]
