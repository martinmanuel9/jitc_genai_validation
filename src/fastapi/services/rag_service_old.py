import os
import logging
from sqlalchemy.orm import Session
from services.database import ChatHistory
from langchain_chroma import Chroma
from langchain_openai import ChatOpenAI
from langchain import hub
from langchain.chains import RetrievalQA
from langchain_huggingface import HuggingFaceEmbeddings
from langsmith import traceable

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

class RAGService:
    def __init__(self):
        """
        Initialize the RAG service, connecting ChromaDB and setting up the LLM, embeddings, and prompt.
        """
        self.openai_api_key = os.getenv("OPEN_AI_API_KEY")
        self.huggingface_api_key = os.getenv("HUGGINGFACE_API_KEY")
        self.chroma_persist_dir = os.getenv("CHROMADB_PERSIST_DIRECTORY", "./chroma_db_data")

        if not self.openai_api_key:
            raise ValueError("OpenAI API key not found. Set OPEN_AI_API_KEY in .env.")
        if not self.huggingface_api_key:
            raise ValueError("Hugging Face API key not found. Set HUGGINGFACE_API_KEY in .env.")

        # Initialize Embeddings using a sentence-transformer model
        self.embeddings = HuggingFaceEmbeddings(
            model_name="sentence-transformers/all-MiniLM-L6-v2"
        )

        # Initialize LLM (e.g., GPT-4 via OpenAI)
        self.llm = ChatOpenAI(
            model_name="gpt-4",
            openai_api_key=self.openai_api_key,
            temperature=0.0
        )

        # Load the Retrieval-QA prompt from LangChain Hub
        self.retrieval_qa_chat_prompt = hub.pull("langchain-ai/retrieval-qa-chat")
        logger.info("Original input variables: %s", self.retrieval_qa_chat_prompt.input_variables)

        # If the prompt is a ChatPromptTemplate, update its messages and input variables
        if hasattr(self.retrieval_qa_chat_prompt, "messages"):
            new_messages = []
            for message in self.retrieval_qa_chat_prompt.messages:
                if hasattr(message, "template"):
                    new_template = message.template.replace("{input}", "{query}")
                    # Rebuild the message with the updated template
                    new_message = type(message)(template=new_template)
                    new_messages.append(new_message)
                else:
                    new_messages.append(message)
            from langchain.prompts import ChatPromptTemplate
            self.retrieval_qa_chat_prompt = ChatPromptTemplate.from_messages(new_messages)
            
            # Map original input variables: change "input" to "query" but keep "context" (or add it if missing)
            original_vars = self.retrieval_qa_chat_prompt.input_variables
            new_vars = [("query" if var == "input" else var) for var in original_vars]
            if "context" not in new_vars:
                new_vars.append("context")
            self.retrieval_qa_chat_prompt.input_variables = new_vars
            logger.info("Modified input variables: %s", self.retrieval_qa_chat_prompt.input_variables)
        else:
            logger.warning("Retrieved prompt does not have a 'messages' attribute; skipping modification.")



        # ChromaDB Setup (Lazy Initialization)
        self.vectorstore = None
        self.retriever = None
        self.rag_chain = None
        self.current_collection = None

    def load_collection(self, collection_name: str, k: int = 3):
        """
        Load the specified ChromaDB collection and set up the retriever and RAG chain.

        Parameters:
        - collection_name (str): The name of the ChromaDB collection to load.
        - k (int): The number of top documents to retrieve (default is 3).
        """
        logger.info("Loading ChromaDB collection: %s", collection_name)
        self.vectorstore = Chroma(
            collection_name=collection_name,
            embedding_function=self.embeddings,
            persist_directory=self.chroma_persist_dir,
        )
        self.current_collection = collection_name
        self.retriever = self.vectorstore.as_retriever(search_kwargs={"k": k})
        self.rag_chain = RetrievalQA.from_chain_type(
            llm=self.llm,
            chain_type="stuff",
            retriever=self.retriever,
            return_source_documents=True,
            input_key="input",  
            chain_type_kwargs={"prompt": self.retrieval_qa_chat_prompt},
        )
        logger.info("ChromaDB collection loaded and RAG chain initialized.")

    def index_documents(self, collection_name: str, documents: list, ids: list = None):
        """
        Index documents into the specified ChromaDB collection.

        Parameters:
        - collection_name (str): Name of the collection.
        - documents (list): List of document strings to index.
        - ids (list, optional): Optional list of unique identifiers for the documents.
        """
        # Ensure the collection is loaded
        if self.vectorstore is None or self.current_collection != collection_name:
            self.load_collection(collection_name)
        logger.info("Indexing %d documents into collection %s", len(documents), collection_name)
        # Embed the documents and add them to the collection
        embeddings = self.embeddings.embed_documents(documents)
        self.vectorstore.add(documents=documents, embeddings=embeddings, ids=ids)
        logger.info("Documents indexed successfully.")

    @traceable(name="RAG Query", project_name="RAGService")
    def query(self, user_query: str, collection_name: str, db: Session) -> dict:
        """
        Execute a RAG query using the provided user query and ChromaDB collection.

        Parameters:
        - user_query (str): The query string from the user.
        - collection_name (str): Name of the ChromaDB collection to use.
        - db (Session): SQLAlchemy session for recording chat history.

        Returns:
        - dict: A dictionary containing the LLM's response and the source documents,
                or an error message if the query fails.
        """
        if not collection_name:
            return {"error": "Collection name is required."}

        # Load the collection if it's not already loaded or if it has changed
        if self.vectorstore is None or self.current_collection != collection_name:
            try:
                self.load_collection(collection_name)
            except Exception as e:
                logger.error("Failed to load collection: %s", e)
                return {"error": f"Failed to load collection: {str(e)}"}

        payload = {"input": user_query}
        logger.debug("Payload sent to RAG chain: %s", payload)

        try:
            response = self.rag_chain.invoke(payload)
            # Save the chat history to your database
            chat_record = ChatHistory(user_query=user_query, response=response["result"])
            db.add(chat_record)
            db.commit()
            return {
                "response": response["result"],
                "source_documents": [doc.page_content for doc in response["source_documents"]],
            }
        except Exception as e:
            logger.error("RAG query failed: %s", e)
            return {"error": f"RAG query failed: {str(e)}"}
