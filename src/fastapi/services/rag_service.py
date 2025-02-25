from sqlalchemy import Column, Integer, String, DateTime
from datetime import datetime
from services.database import Base
import os
# from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_chroma import Chroma
from langchain_openai import ChatOpenAI
from langchain import hub
from langchain.chains import RetrievalQA
from langsmith import traceable, Client
from langchain_huggingface import HuggingFaceEmbeddings

class ChatHistory(Base):
    __tablename__ = "chat_history"
    id = Column(Integer, primary_key=True, index=True)
    user_query = Column(String)
    response = Column(String)
    timestamp = Column(DateTime, default=datetime.utcnow())

class RAGService:
    def __init__(self):
        self.openai_api_key = os.getenv("OPEN_AI_API_KEY")
        self.huggingface_api_key = os.getenv("HUGGINGFACE_API_KEY")

        if not self.openai_api_key:
            raise ValueError("OpenAI API key not found. Set OPEN_AI_API_KEY in .env.")
        if not self.huggingface_api_key:
            raise ValueError("Hugging Face API key not found. Set HUGGINGFACE_API_KEY in .env.")
        # 1) Embeddings
        self.embeddings = HuggingFaceEmbeddings(
            model_name="sentence-transformers/all-MiniLM-L6-v2"
        )
        
        self.vectorstore = Chroma(
            collection_name="my_collection",
            embedding_function=self.embeddings,
            persist_directory="/app/chroma_db_data",
        )

        self.llm = ChatOpenAI(
            model_name="gpt-4",
            openai_api_key=self.openai_api_key,
            temperature=0.0
        )

        # 4) Pull a retrieval-qa prompt from the Hub (optional)
        retrieval_qa_chat_prompt = hub.pull("langchain-ai/retrieval-qa-chat")

        # 5) Build the RetrievalQA using `.from_chain_type(...)`
        self.rag_chain = RetrievalQA.from_chain_type(
            llm=self.llm,
            chain_type="stuff",
            retriever=self.vectorstore.as_retriever(search_kwargs={"k": 3}),
            return_source_documents=False,
            chain_type_kwargs={
                "prompt": retrieval_qa_chat_prompt
            },
        )

    @traceable(name="RAG Query", project_name="RAGService")
    def query(self, user_query: str, collection_name: str) -> str:
        """Retrieve docs from the correct collection before querying LLM"""
        retriever = self.vectorstore.as_retriever(search_kwargs={"k": 3})

        if collection_name:
            self.vectorstore = Chroma(
                collection_name=collection_name,
                embedding_function=self.embeddings,
                persist_directory="/app/chroma_db_data"
            )
            retriever = self.vectorstore.as_retriever()

        return self.rag_chain.invoke({"query": user_query})

