import os
import uuid
from concurrent.futures import ThreadPoolExecutor, as_completed
from sqlalchemy.orm import Session

from services.database import SessionLocal, ComplianceAgent, DebateSession
from services.llm_service import LLMService

# We'll use the existing LLMService (which holds a reference to RAGService)
llm_service = LLMService()
rag_service = llm_service.rag_service

class RAGAgentService:
    """
    This service parallels your AgentService, but uses retrieval (RAG).
    Each agent is expected to do a RAG query (with GPT-4 or TinyLLaMA) 
    and then respond in a "Yes" or "No" + explanation format.
    """

    def __init__(self):
        self.compliance_agents = []

    def load_selected_compliance_agents(self, agent_ids):
        """Load the specified compliance agents from DB."""
        session = SessionLocal()
        try:
            self.compliance_agents = []
            agents = (
                session.query(ComplianceAgent)
                .filter(ComplianceAgent.id.in_(agent_ids))
                .all()
            )
            for agent in agents:
                self.compliance_agents.append({
                    "id": agent.id,
                    "name": agent.name,
                    "model_name": agent.model_name,
                    "system_prompt": agent.system_prompt,
                    "user_prompt_template": agent.user_prompt_template
                })
        finally:
            session.close()

    def run_rag_check(self, query_text: str, collection_name: str, agent_ids: list[int], db: Session):
        """
        1) Runs parallel RAG checks (one per agent).
        2) If all say "Yes," returns a final result. Otherwise, spawns a new 
        debate session & runs them in the same manner, returning the debate results.
        """
        # 1) Load the specified RAG agents
        self.load_selected_compliance_agents(agent_ids)

        # 2) Run the checks in parallel
        rag_results = self.run_parallel_rag_checks(query_text, collection_name, db)

        # 3) Determine overall compliance
        bool_vals = [res["compliant"] for res in rag_results.values() if res["compliant"] is not None]
        all_compliant = bool_vals and all(bool_vals)

        if all_compliant:
            return {
                "overall_compliance": True,
                "details": rag_results
            }
        else:
            # 4) Create a new session for the debate
            session_id = str(uuid.uuid4())

            # Save these agents in the DebateSession table
            for idx, agent_info in enumerate(self.compliance_agents):
                db.add(DebateSession(
                    session_id=session_id,
                    compliance_agent_id=agent_info["id"],
                    debate_order=idx + 1
                ))
            db.commit()

            # 5) Run the RAG-based debate
            debate_results = self.run_rag_debate(session_id, query_text, collection_name, db)

            return {
                "overall_compliance": False,
                "details": rag_results,
                "debate_results": debate_results,
                "session_id": session_id
            }

    def run_parallel_rag_checks(self, query_text: str, collection_name: str, db: Session):
        """Calls each agent in parallel, collecting yes/no answers from RAG queries."""
        results = {}
        with ThreadPoolExecutor() as executor:
            futures = {
                executor.submit(self.verify_rag, agent, query_text, collection_name, db): i
                for i, agent in enumerate(self.compliance_agents)
            }
            for future in as_completed(futures):
                idx = futures[future]
                results[idx] = future.result()
        return results

    def verify_rag(self, agent: dict, query_text: str, collection_name: str, db: Session):
        """
        1) Perform a RAG query using either GPT-4 or TinyLLaMA.
        2) Parse the result into a "Yes"/"No" + explanation. 
        (You can adjust the prompts to ensure the model returns this format.)
        """
        model_name = agent["model_name"].lower()

        # We'll pass the user query, collection, and db to rag_service
        if model_name == "gpt-4":
            # Query GPT-4 with retrieval
            raw_text = rag_service.query_gpt(query_text, collection_name, db)
        elif model_name == "tinyllama":
            # Query TinyLLaMA with retrieval
            raw_text = rag_service.query_llama(query_text, collection_name, db)
        else:
            raw_text = f"Error: Model '{agent['model_name']}' not recognized."

        # The agent might produce any text; we assume they say "Yes" or "No" 
        # on the first line, plus an explanation after.
        lines = raw_text.split("\n", 1)
        first_line = lines[0].lower()

        if "yes" in first_line:
            compliant = True
        elif "no" in first_line:
            compliant = False
        else:
            compliant = None

        reason = lines[1].strip() if len(lines) > 1 else ""

        return {
            "compliant": compliant,
            "reason": reason,
            "raw_text": raw_text
        }

    def run_rag_debate(self, session_id: str, query_text: str, collection_name: str, db: Session):
        """
        1) Loads the debate agents in the correct order from DB.
        2) Each agent does a retrieval-based check again, 
        but now you might want a different prompt or logic.
        """
        debate_agents = self.load_debate_agents(session_id)
        results = {}

        with ThreadPoolExecutor() as executor:
            futures = {
                executor.submit(self.debate_rag_compliance, agent, query_text, collection_name, db): agent["name"]
                for agent in debate_agents
            }
            for future in as_completed(futures):
                agent_name = futures[future]
                results[agent_name] = future.result()

        return results

    def load_debate_agents(self, session_id: str):
        """Fetch compliance agents for the given debate session."""
        session = SessionLocal()
        try:
            debate_records = (
                session.query(DebateSession)
                .filter(DebateSession.session_id == session_id)
                .order_by(DebateSession.debate_order)
                .all()
            )

            debate_agents = []
            for record in debate_records:
                agent = record.compliance_agent
                debate_agents.append({
                    "id": agent.id,
                    "name": agent.name,
                    "model_name": agent.model_name,
                    "system_prompt": agent.system_prompt,
                    "user_prompt_template": agent.user_prompt_template
                })
            return debate_agents

        finally:
            session.close()

    def debate_rag_compliance(self, agent: dict, query_text: str, collection_name: str, db: Session):
        """
        1) Another retrieval-based step for the debate.
        2) Possibly a different style prompt or logic. 
        For demonstration, just re-run the same approach.
        """
        model_name = agent["model_name"].lower()

        # You might want to incorporate "the previous agent said NO" or something 
        # to show debate context. For now, we just do the same retrieval-based logic:
        if model_name == "gpt-4":
            raw_text = rag_service.query_gpt(query_text, collection_name, db)
        elif model_name == "tinyllama":
            raw_text = rag_service.query_llama(query_text, collection_name, db)
        else:
            raw_text = f"Error: Model '{agent['model_name']}' not recognized."

        return raw_text

    def run_rag_debate_sequence(self, db: Session, session_id: str | None, agent_ids: list[int], query_text: str, collection_name: str):
        """
        1) If session_id is None, create a new one.
        2) Clear out prior debate records for that session (if any) to start fresh.
        3) Insert these agents in the DB in the specified order.
        4) Iterate them in order, each time:
            - Construct a prompt that includes the running context so far
            - Perform a new RAG retrieval
            - Agent produces a response
            - Append that response to the chain and the context
        5) Return (session_id, debate_chain).
        """

        if not session_id:
            session_id = str(uuid.uuid4())

        # 1) Clear existing debate records if you want a truly fresh chain.
        db.query(DebateSession).filter(DebateSession.session_id == session_id).delete()
        db.commit()

        # 2) Insert these agents in order
        for idx, agent_id in enumerate(agent_ids):
            db.add(DebateSession(
                session_id=session_id,
                compliance_agent_id=agent_id,
                debate_order=idx + 1
            ))
        db.commit()

        # 3) Load the debate agents from the DB
        debate_agents = self.load_debate_agents(session_id)

        debate_chain = []
        context = f"Original user query:\n{query_text}\n"

        # 4) Run them in a sequence
        for agent in debate_agents:
            agent_prompt = (
                f"You have the following context:\n{context}\n"
                "Please provide your answer. If you have a final stance (Yes or No), "
                "include it on the first line, followed by your reasoning."
            )

            # Single turn with RAG
            agent_response = self.single_rag_agent_run(agent, agent_prompt, collection_name, db)

            debate_chain.append({
                "agent_id": agent["id"],
                "agent_name": agent["name"],
                "response": agent_response
            })

            # Update context so next agent sees what the previous one said
            context += f"\n---\nAgent {agent['name']} responded:\n{agent_response}\n"

        return session_id, debate_chain

    def single_rag_agent_run(self, agent: dict, query_text: str, collection_name: str, db: Session) -> str:
        """
        For a single turn:
        1) Use the agent's model (GPT-4 vs. TinyLLaMA).
        2) Perform retrieval using the entire `query_text`.
        3) Return the raw text of the agent's answer.
        """
        model_name = agent["model_name"].lower()

        if model_name == "gpt-4":
            raw_text = rag_service.query_gpt(query_text, collection_name, db)
        elif model_name == "tinyllama":
            raw_text = rag_service.query_llama(query_text, collection_name, db)
        else:
            raw_text = f"Error: Model '{agent['model_name']}' not recognized."

        return raw_text.strip()
