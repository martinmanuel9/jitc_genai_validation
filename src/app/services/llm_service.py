# /app/src/app/services/llm_service.py

import os
from haystack.nodes import PromptNode, PromptTemplate
from haystack.pipelines import Pipeline
from haystack.document_stores import MilvusDocumentStore
from haystack.nodes import DensePassageRetriever
from openai import ChatCompletion

from haystack.document_stores import MilvusDocumentStore

document_store = MilvusDocumentStore(
    host="milvus",
    port="19530",
    connection_pool="SingletonThreadPool",
    index="jitc_genai",
    consistency_level="Session",
)


class LLMService:
    def __init__(self):
        # Initialize LLMs
        self.llama_node = PromptNode(model_name_or_path="path/to/llama/model")
        self.openai_api_key = os.getenv("OPENAI_API_KEY")
        self.document_store = MilvusDocumentStore()
        self.retriever = DensePassageRetriever(document_store=self.document_store)
        self.pipeline = Pipeline()
        self.pipeline.add_node(component=self.retriever, name="Retriever", inputs=["Query"])
        self.pipeline.add_node(component=self.llama_node, name="Generator", inputs=["Retriever"])

    def generate_response(self, query):
        # Use RAG pipeline
        result = self.pipeline.run(query=query)
        llama_response = result['answers'][0].answer

        # Use GPT-4 via OpenAI API
        openai_response = self.query_gpt4(query)

        # Combine responses or choose one
        final_response = self.combine_responses(llama_response, openai_response)
        return final_response

    def query_gpt4(self, prompt):
        if not self.openai_api_key:
            raise Exception("OpenAI API key not found.")
        response = ChatCompletion.create(
            model="gpt-4",
            messages=[{"role": "user", "content": prompt}],
            api_key=self.openai_api_key
        )
        return response.choices[0].message.content

    def combine_responses(self, response1, response2):
        # Simple heuristic or more complex logic to combine responses
        return f"LLaMA says: {response1}\nGPT-4 says: {response2}"
