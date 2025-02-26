from sqlalchemy.orm import Session
from services.database import ChatHistory
from langchain_chroma import Chroma
from langchain_openai import ChatOpenAI
from langchain import hub
from langchain.chains import RetrievalQA
from langchain_huggingface import HuggingFaceEmbeddings
from langsmith import traceable
import os

class RAGService:
    def __init__(self):
        """Initialize the RAG service, connecting ChromaDB and setting up LLM."""
        self.openai_api_key = os.getenv("OPEN_AI_API_KEY")
        self.huggingface_api_key = os.getenv("HUGGINGFACE_API_KEY")
        self.chroma_persist_dir = os.getenv("CHROMADB_PERSIST_DIRECTORY", "./chroma_db_data")

        if not self.openai_api_key:
            raise ValueError("OpenAI API key not found. Set OPEN_AI_API_KEY in .env.")
        if not self.huggingface_api_key:
            raise ValueError("Hugging Face API key not found. Set HUGGINGFACE_API_KEY in .env.")

        # Initialize Embeddings
        self.embeddings = HuggingFaceEmbeddings(
            model_name="sentence-transformers/all-MiniLM-L6-v2"
        )

        # Initialize LLM
        self.llm = ChatOpenAI(
            model_name="gpt-4",
            openai_api_key=self.openai_api_key,
            temperature=0.0
        )

        # Load the Retrieval-QA prompt from LangChain Hub
        self.retrieval_qa_chat_prompt = hub.pull("langchain-ai/retrieval-qa-chat")

        # ChromaDB Setup (Lazy Initialization)
        self.vectorstore = None
        self.retriever = None
        self.rag_chain = None
        self.current_collection = None

    def load_collection(self, collection_name: str):
        """Load the specified ChromaDB collection and set up the retriever and RAG chain."""
        print(f"Loading ChromaDB collection: {collection_name}")
        self.vectorstore = Chroma(
            collection_name=collection_name,
            embedding_function=self.embeddings,
            persist_directory=self.chroma_persist_dir,
        )
        self.current_collection = collection_name
        self.retriever = self.vectorstore.as_retriever(search_kwargs={"k": 3})

        self.rag_chain = RetrievalQA.from_chain_type(
            llm=self.llm,
            chain_type="stuff",
            retriever=self.retriever,
            return_source_documents=True,
            chain_type_kwargs={
                "prompt": self.retrieval_qa_chat_prompt,
                "input_key": "query"  # Force the chain to use "query" as the input key
            },
        )

    @traceable(name="RAG Query", project_name="RAGService")
    def query(self, user_query: str, collection_name: str, db: Session) -> dict:
        """Retrieve documents from the specified ChromaDB collection and query the LLM."""
        if not collection_name:
            return {"error": "Collection name is required."}

        # Load the collection if not already loaded or if it differs from the current one.
        if self.vectorstore is None or self.current_collection != collection_name:
            try:
                self.load_collection(collection_name)
            except Exception as e:
                return {"error": f"Failed to load collection: {str(e)}"}

        # Prepare payload using the key "query" (as set in input_key)
        payload = {"query": user_query}
        print(f"Debug - Payload sent to RAG chain: {payload}")

        try:
            response = self.rag_chain.invoke(payload)
            # Store chat in DB
            chat_record = ChatHistory(user_query=user_query, response=response["result"])
            db.add(chat_record)
            db.commit()
            return {
                "response": response["result"],
                "source_documents": [doc.page_content for doc in response["source_documents"]],
            }
        except Exception as e:
            return {"error": f"RAG query failed: {str(e)}"}
