# services/rag_service.py
import os
import requests
from sentence_transformers import SentenceTransformer
from openai import OpenAI

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY", "YOUR_OPENAI_API_KEY"))

class RAGService:
    def __init__(self):
        # Load configuration from environment variables or use defaults.
        self.chromadb_api = os.getenv("CHROMADB_API", "http://chromadb:8020")
        self.n_results = int(os.getenv("N_RESULTS", "3"))

        # Load the embedding model.
        self.embedding_model = SentenceTransformer('multi-qa-mpnet-base-dot-v1')

    def query_chromadb(self, query_text: str, collection_name: str, n_results: int = None) -> dict:
        """
        Encodes the query and retrieves relevant document chunks from ChromaDB.
        """
        if n_results is None:
            n_results = self.n_results

        # Encode the query
        query_embedding = self.embedding_model.encode([query_text]).tolist()

        # Prepare the payload for ChromaDB
        payload = {
            "collection_name": collection_name,
            "query_embeddings": query_embedding,
            "n_results": n_results,
            "include": ["documents", "metadatas", "distances"]
        }

        # Call the ChromaDB /documents/query endpoint
        response = requests.post(f"{self.chromadb_api}/documents/query", json=payload)
        if response.status_code == 200:
            return response.json()
        else:
            raise Exception(f"Error querying ChromaDB: {response.text}")

    def build_context(self, query_result: dict) -> str:
        """
        Builds a single context string from the list of retrieved document chunks.
        """
        # Retrieve documents, metadata, and distances (assuming one query was sent).
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
        Forms a prompt with the provided context and query, and then calls the ChatGPT API.
        """
        prompt = (
            "You are a helpful assistant that answers questions based on provided context.\n\n"
            f"Context:\n{context}\n\n"
            f"Question: {query_text}\n\n"
            "Answer:"
        )

        response = client.chat.completions.create(model="gpt-4",  
        messages=[
            {"role": "system", "content": "You are a knowledgeable and helpful assistant."},
            {"role": "user", "content": prompt}
        ],
        temperature=0.7,
        max_tokens=300)

        return response.choices[0].message.content.strip()

    def query(self, query_text: str, collection_name: str, db) -> str:
        """
        High-level method to perform a RAG query. It retrieves context from ChromaDB and
        generates an answer using the ChatGPT API.
        """
        # Retrieve relevant document chunks from ChromaDB.
        query_result = self.query_chromadb(query_text, collection_name)
        context = self.build_context(query_result)

        if not context:
            return "No relevant context found in the database."

        # Generate the final answer using ChatGPT.
        answer = self.generate_answer(query_text, context)
        return answer
