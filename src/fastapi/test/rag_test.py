import os
import sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from services.rag_service import RAGService

def main():
    os.environ.setdefault("OPEN_AI_API_KEY", "your_openai_api_key_here")
    os.environ.setdefault("HUGGINGFACE_API_KEY", "your_huggingface_api_key_here")

    # Instantiate the RAG service
    rag_service = RAGService()

    query_text = "What IEEE standards do I have?"
    collection_name = "standards" 

    try:
        response = rag_service.query(query_text, collection_name)
        print("RAG Response:")
        print(response)
    except Exception as e:
        print("An error occurred:")
        print(e)

if __name__ == "__main__":
    main()
