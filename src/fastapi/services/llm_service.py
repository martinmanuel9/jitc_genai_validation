# /app/src/app/services/llm_service.py

import os
from openai import OpenAI

class LLMService:
    def __init__(self):
        # Initialize LLMs
        # self.llama_node = PromptNode(model_name_or_path="path/to/llama/model")
        self.openai_api_key = os.getenv("OPEN_AI_API_KEY")
        if not self.openai_api_key:
            raise ValueError("OpenAI API key not found. Set OPEN_AI_API_KEY environment variable.")
        
        self.open_ai_client = OpenAI(
            #This is the default and can be omitted
            api_key= self.openai_api_key,
        )
        # TODO: Add LLaMA node to pipeline
        # # self.pipeline.add_node(component=self.llama_node, name="Generator", inputs=["Retriever"])

    def generate_response(self, query):
        # TODO:Use RAG pipeline
        # result = self.pipeline.run(query=query)
        # TODO: Use LLaMA via Haystack
        # llama_response = result['answers'][0].answer if result['answers'] else "No answer found."
        
        # Use GPT-4 via OpenAI API
        openai_response = self.query_gpt4(query)
        
        # Combine responses
        # final_response = self.combine_responses(llama_response, openai_response)
        return openai_response # final_response

    def query_gpt4(self, prompt):
        response = self.open_ai_client.chat.completions.create(
            model="gpt-4o",
            messages=[{"role": "user", "content": prompt}],
        )
        return response.choices[0].message.content

    def combine_responses(self, response1, response2):
        # Simple combination logic
        return f"LLaMA says: {response1}\nGPT-4 says: {response2}"

