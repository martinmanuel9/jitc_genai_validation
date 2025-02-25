import os
import torch
from concurrent.futures import ThreadPoolExecutor, as_completed
from transformers import AutoModelForCausalLM, AutoTokenizer
from langchain_openai import ChatOpenAI
from langchain.schema import AIMessage, HumanMessage
from services.rag_service import RAGService
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
        self.model_name = "meta-llama/Llama-2-13b-chat-hf"
        self.tokenizer = AutoTokenizer.from_pretrained(
            self.model_name,
            token=self.huggingface_api_key
        )
        self.model = AutoModelForCausalLM.from_pretrained(
            self.model_name,
            token=self.huggingface_api_key,
            device_map="cpu",
            torch_dtype=torch.float16
        )

        # Initialize the RAG service
        self.rag_service = RAGService()

    def query_gpt4(self, prompt):
        """Query GPT-4 using OpenAI API (no retrieval)."""
        response = self.openai_client.invoke([HumanMessage(content=prompt)])
        return response.content.strip()

    def query_llama(self, prompt):
        """Query LLaMA using Hugging Face Transformers on CPU (no retrieval)."""
        inputs = self.tokenizer(prompt, return_tensors="pt").to("cpu")
        outputs = self.model.generate(**inputs, max_new_tokens=100)
        return self.tokenizer.decode(outputs[0], skip_special_tokens=True)

    def query_rag_gpt4(self, user_query):
        """
        Query your Chroma-based RAG pipeline with GPT-4 as the LLM.
        Returns a final answer with retrieved context.
        """
        return self.rag_service.query(user_query)

    # -----------
    # MULTI-AGENT COMPLIANCE
    # -----------

    def compliance_check(self, data_sample, standards):
        """Run compliance check using multiple LLMs."""
        agents = [ComplianceAgent(section, f"Section {i + 1}") for i, section in enumerate(standards)]
        compliance_results = self.run_parallel_compliance_checks(agents, data_sample)
        if all(compliance_results.values()):
            return True  # All agents agree

        # Debate non-compliant sections
        debate_results = self.run_debate(agents, compliance_results, data_sample)
        for idx, compliant in compliance_results.items():
            if idx in debate_results:
                compliance_results[idx] = debate_results[idx]

        return all(compliance_results.values())  # Final decision

    def run_parallel_compliance_checks(self, agents, data_sample):
        """Run compliance checks in parallel."""
        results = {}
        with ThreadPoolExecutor() as executor:
            futures = {executor.submit(agent.verify_compliance, data_sample): i for i, agent in enumerate(agents)}
            for future in as_completed(futures):
                idx = futures[future]
                results[idx] = future.result()
        return results

    def run_debate(self, agents, compliance_results, data_sample):
        """Run debates on compliance decisions."""
        debate_results = {}
        non_compliant_indices = [idx for idx, compliant in compliance_results.items() if not compliant]

        with ThreadPoolExecutor() as executor:
            futures = []
            for idx in non_compliant_indices:
                peer_agent = agents[non_compliant_indices[(non_compliant_indices.index(idx) + 1) % len(non_compliant_indices)]]
                futures.append((idx, executor.submit(peer_agent.debate_compliance, compliance_results[idx], data_sample)))

            for idx, future in futures:
                debate_results[idx] = future.result()
        return debate_results


class ComplianceAgent:
    """Agent for verifying compliance with standards using GPT-4."""
    def __init__(self, section_text, section_name):
        self.section_text = section_text
        self.section_name = section_name
        self.llm = ChatOpenAI(
            model_name="gpt-4",
            openai_api_key=os.getenv("OPEN_AI_API_KEY")
        )

    def verify_compliance(self, data_sample):
        """Verify if data complies with a standard section."""
        system_prompt = f"You are an expert verifying data compliance."
        user_prompt = f"Standard Section:\n{self.section_text}\n\nDoes this data comply? Respond 'Yes' or 'No'.\nData: {data_sample}"

        response = self.llm([AIMessage(content=system_prompt), HumanMessage(content=user_prompt)])
        return response.content.strip().lower() == "yes"

    def debate_compliance(self, peer_response, data_sample):
        """Debate compliance with another agent."""
        debate_prompt = f"The agent for {self.section_name} found the data {'compliant' if peer_response else 'non-compliant'}.\nDo you agree? Respond 'Yes' or 'No'."
        response = self.llm([HumanMessage(content=debate_prompt)])
        return response.content.strip().lower() == "yes"
