import os
from transformers import AutoModelForCausalLM, AutoTokenizer
from langchain_openai import ChatOpenAI
from langchain.schema import AIMessage, HumanMessage
from services.rag_service import RAGService
import requests
class LLMService:
    def __init__(self):
        """Initialize LLMs (OpenAI & LLaMA) + RAG service."""
        self.openai_api_key = os.getenv("OPEN_AI_API_KEY")
        self.huggingface_api_key = os.getenv("HUGGINGFACE_API_KEY")

        if not self.openai_api_key:
            raise ValueError("OpenAI API key not found. Set OPEN_AI_API_KEY in .env.")
        if not self.huggingface_api_key:
            raise ValueError("Hugging Face API key not found. Set HUGGINGFACE_API_KEY in .env.")

        # Initialize OpenAI GPT-4 via LangChain
        self.openai_client = ChatOpenAI(
            model_name="gpt-4o",  # your custom model name if relevant
            openai_api_key=self.openai_api_key
        )

        # Load LLaMA Model on CPU
        # self.model_name = "meta-llama/Llama-2-13b-chat-hf"
        # self.tokenizer = AutoTokenizer.from_pretrained(
        #     self.model_name,
        #     token=self.huggingface_api_key
        # )
        # self.model = AutoModelForCausalLM.from_pretrained(
        #     self.model_name,
        #     token=self.huggingface_api_key,
        #     device_map="cpu",
        #     torch_dtype=torch.float16
        # )

        # Initialize the RAG service
        self.rag_service = RAGService()

    def query_gpt4(self, prompt):
        """Query GPT-4 using OpenAI API (no retrieval)."""
        response = self.openai_client.invoke([HumanMessage(content=prompt)])
        return response.content.strip()

    # def query_llama(self, prompt):
    #     """Query LLaMA using Hugging Face Transformers on CPU (no retrieval)."""
    #     inputs = self.tokenizer(prompt, return_tensors="pt").to("cpu")
    #     outputs = self.model.generate(**inputs, max_new_tokens=100)
    #     return self.tokenizer.decode(outputs[0], skip_special_tokens=True)
    

    def query_llama_via_ollama(self, prompt):
        """
        Query the Ollama container running at `llama` inside Docker.
        """
        url = "http://llama:11434/api/generate"  # Use 'llama' inside Docker
        payload = {
            "model": "tinyllama",  # Ensure you specify the model
            "prompt": prompt,
            "stream": False  # Set to True if you want streaming responses
        }

        try:
            response = requests.post(url, json=payload)
            response.raise_for_status()  # Raise an error for HTTP failures
            response_data = response.json()

            # Ollama returns the generated text under 'response'
            return response_data.get("response", "")

        except requests.exceptions.RequestException as e:
            print(f"Error querying Ollama: {e}")
            return "Error: Could not connect to Ollama"



    def query_rag_gpt4(self, user_query):
        """
        Query your Chroma-based RAG pipeline with GPT-4 as the LLM.
        Returns a final answer with retrieved context.
        """
        return self.rag_service.query(user_query)
