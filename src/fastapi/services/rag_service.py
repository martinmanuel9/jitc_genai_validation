# services/rag_service.py
import os
import requests
from sentence_transformers import SentenceTransformer
import openai

# Set up OpenAI client (for GPT-4)
openai.api_key = os.getenv("OPEN_AI_API_KEY", "YOUR_OPEN_AI_API_KEY")

def llama3_chat_completion(prompt: str, temperature: float = 0.7, max_tokens: int = 300) -> str:
    """
    Calls the LLaMA3 API (running in the 'llama3' container) to generate a chat completion.
    Adjust the endpoint and payload as needed.
    """
    llama_api_url = "http://llama3:11434/v1/chat/completions"  # Adjust if needed
    payload = {
        "model": "llama3",  # or specify the actual model name if required
        "messages": [
            {"role": "system", "content": "You are a knowledgeable and helpful assistant."},
            {"role": "user", "content": prompt}
        ],
        "temperature": temperature,
        "max_tokens": max_tokens,
    }
    response = requests.post(llama_api_url, json=payload)
    if response.status_code == 200:
        return response.json()["choices"][0]["message"]["content"].strip()
    else:
        raise Exception(f"Error querying LLaMA: {response.text}")

class RAGService:
    def __init__(self):
        # Configuration for ChromaDB
        self.chromadb_api = os.getenv("CHROMADB_API", "http://chromadb:8020")
        self.n_results = int(os.getenv("N_RESULTS", "3"))
        # Load the embedding model (produces 768-d vectors)
        self.embedding_model = SentenceTransformer('multi-qa-mpnet-base-dot-v1')

    def query_chromadb(self, query_text: str, collection_name: str, n_results: int = None) -> dict:
        """
        Encodes the query and retrieves relevant document chunks from ChromaDB.
        """
        if n_results is None:
            n_results = self.n_results
        
        query_embedding = self.embedding_model.encode([query_text]).tolist()
        payload = {
            "collection_name": collection_name,
            "query_embeddings": query_embedding,
            "n_results": n_results,
            "include": ["documents", "metadatas", "distances"]
        }
        response = requests.post(f"{self.chromadb_api}/documents/query", json=payload)
        if response.status_code == 200:
            return response.json()
        else:
            raise Exception(f"Error querying ChromaDB: {response.text}")

    def build_context(self, query_result: dict) -> str:
        """
        Builds a single context string from the retrieved document sections.
        """
        documents = query_result.get("documents", [[]])[0]
        metadatas = query_result.get("metadatas", [[]])[0]
        distances = query_result.get("distances", [[]])[0]
        
        context_parts = []
        for doc, meta, dist in zip(documents, metadatas, distances):
            doc_name = meta.get("document_name", "Unknown") if meta else "Unknown"
            context_parts.append(f"[{doc_name} | Score: {round(dist, 4)}] {doc}")
        return "\n\n".join(context_parts)

    def generate_answer(self, query_text: str, context: str) -> str:
        """
        Generates an answer using GPT-4 via the OpenAI API.
        """
        prompt = (
            "You are a helpful assistant that answers questions based on provided context.\n\n"
            f"Context:\n{context}\n\n"
            f"Question: {query_text}\n\n"
            "Answer:"
        )
        response = openai.ChatCompletion.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": "You are a knowledgeable and helpful assistant."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7,
            max_tokens=300,
        )
        return response.choices[0].message.content.strip()

    def generate_llama_answer(self, query_text: str, context: str) -> str:
        """
        Generates an answer using LLaMA3 via its API.
        """
        prompt = (
            "You are a helpful assistant that answers questions based on provided context.\n\n"
            f"Context:\n{context}\n\n"
            f"Question: {query_text}\n\n"
            "Answer:"
        )
        return llama3_chat_completion(prompt, temperature=0.7, max_tokens=300)

    def query_gpt(self, query_text: str, collection_name: str, db) -> str:
        """
        Performs a RAG query using GPT-4.
        """
        query_result = self.query_chromadb(query_text, collection_name)
        context = self.build_context(query_result)
        if not context:
            return "No relevant context found in the database."
        return self.generate_answer(query_text, context)

    def query_llama(self, query_text: str, collection_name: str, db) -> str:
        """
        Performs a RAG query using LLaMA3.
        """
        query_result = self.query_chromadb(query_text, collection_name)
        context = self.build_context(query_result)
        if not context:
            return "No relevant context found in the database."
        return self.generate_llama_answer(query_text, context)
