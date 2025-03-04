import os
import uuid
from concurrent.futures import ThreadPoolExecutor, as_completed
from sqlalchemy.orm import Session
from langchain_openai import ChatOpenAI
from langchain.schema import AIMessage, HumanMessage
from services.database import SessionLocal, ComplianceAgent, ComplianceSequence, DebateSession
from services.llm_service import LLMService

llm_service = LLMService()

class AgentService:
    """Service for managing compliance checks and debates dynamically."""

    def __init__(self):
        self.compliance_agents = []

    def load_selected_compliance_agents(self, agent_ids):
        """Load only the selected compliance agents from the database."""
        session = SessionLocal()
        try:
            self.compliance_agents = []
            agents = session.query(ComplianceAgent).filter(ComplianceAgent.id.in_(agent_ids)).all()
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

    def run_compliance_check(self, data_sample: str, agent_ids: list[int], db: Session):
        """
        1) Run parallel compliance checks using selected agents.
        2) If all are compliant, return. Otherwise, create a new debate session,
        store the agents, and run the debate automatically.
        """
        # Load the specified agents into self.compliance_agents
        self.load_selected_compliance_agents(agent_ids)

        # Step 1: Run parallel checks
        compliance_results = self.run_parallel_compliance_checks(data_sample)
        # compliance_results is a dict like:
        #   {
        #       0: {"compliant": True, "reason": "...", "raw_text": "..."},
        #       1: {"compliant": False, "reason": "...", "raw_text": "..."}
        #   }

        # Step 2: Determine overall compliance
        bool_vals = [res["compliant"] for res in compliance_results.values() if res["compliant"] is not None]
        # True if *all* are True and not empty:
        all_compliant = bool_vals and all(bool_vals)

        if all_compliant:
            # No debate needed
            return {
                "overall_compliance": True,
                "details": compliance_results
            }
        else:
            # Create a new session_id for debate
            session_id = str(uuid.uuid4())

            # Store these agents in the DebateSession table for the new session
            # so that run_debate() can load them
            for idx, agent_info in enumerate(self.compliance_agents):
                db.add(DebateSession(
                    session_id=session_id,
                    compliance_agent_id=agent_info["id"],
                    debate_order=idx + 1
                ))
            db.commit()

            # Step 3: Run debate with the newly created session
            debate_results = self.run_debate(session_id, data_sample)

            return {
                "overall_compliance": False,
                "details": compliance_results,
                "debate_results": debate_results,
                "session_id": session_id
            }

    def run_parallel_compliance_checks(self, data_sample: str):
        """Run compliance checks in parallel."""
        results = {}
        with ThreadPoolExecutor() as executor:
            futures = {
                executor.submit(self.verify_compliance, agent, data_sample): i
                for i, agent in enumerate(self.compliance_agents)
            }
            for future in as_completed(futures):
                idx = futures[future]
                results[idx] = future.result()
        return results

    def verify_compliance(self, agent: dict, data_sample: str):
        """
        Check compliance using the specified agent.
        Expect the agent to reply with either "Yes" or "No" 
        plus an explanation. We'll parse that into:
            {
                "compliant": bool, 
                "reason": str, 
                "raw_text": str
            }
        """
        if agent["model_name"] == "gpt-4":
            llm = ChatOpenAI(
                model_name="gpt-4",
                openai_api_key=os.getenv("OPEN_AI_API_KEY")
            )
            user_prompt = agent["user_prompt_template"].format(data_sample=data_sample)
            gpt_response = llm.invoke([
                AIMessage(content=agent["system_prompt"]),
                HumanMessage(content=user_prompt)
            ])
            raw_text = gpt_response.content.strip()
        elif agent["model_name"] == "tinyllama":
            raw_text = llm_service.query_llama_via_ollama(prompt=data_sample).strip()
        else:
            raw_text = "Error: Model not recognized."

        # Example parse: we expect the first line to be "Yes" or "No"
        # and subsequent lines to be the reason/explanation.
        lines = raw_text.split("\n", 1)
        first_line = lines[0].lower()

        if "yes" in first_line:
            compliant = True
        elif "no" in first_line:
            compliant = False
        else:
            compliant = None  # Could not parse

        reason = lines[1].strip() if len(lines) > 1 else ""

        return {
            "compliant": compliant,
            "reason": reason,
            "raw_text": raw_text
        }

    def run_debate(self, session_id: str, data_sample: str):
        """
        Always receives a session_id (string) to find the agents 
        that are participating in this debate. 
        Then collects each agent's 'Yes'/'No' plus reasoning.
        """
        # 1) Load the debate agents from the DB in the correct order
        debate_agents = self.load_debate_agents(session_id)

        # 2) For simplicity, we run them in sequence or parallel 
        #    to see if they 'agree' or 'disagree'.
        results = {}
        with ThreadPoolExecutor() as executor:
            futures = {
                executor.submit(self.debate_compliance, agent, data_sample): agent["name"]
                for agent in debate_agents
            }
            for future in as_completed(futures):
                agent_name = futures[future]
                results[agent_name] = future.result()
        return results

    def load_debate_agents(self, session_id: str):
        """Fetch compliance agents for a specific debate session from the database."""
        session = SessionLocal()
        debate_agents = []
        try:
            debate_records = (
                session.query(DebateSession)
                .filter(DebateSession.session_id == session_id)
                .order_by(DebateSession.debate_order)
                .all()
            )
            for record in debate_records:
                agent = record.compliance_agent
                debate_agents.append({
                    "id": agent.id,
                    "name": agent.name,
                    "model_name": agent.model_name,
                    "system_prompt": agent.system_prompt,
                    "user_prompt_template": agent.user_prompt_template
                })
        finally:
            session.close()
        return debate_agents

    def debate_compliance(self, agent: dict, data_sample: str):
        """
        Each debate agent can see the data. 
        For GPT-4, call ChatOpenAI. 
        For tinyllama, call our local service.
        """
        debate_prompt = (
            f"Agent {agent['name']} is evaluating this data again:\n"
            f"{data_sample}\n\n"
            "Do you find this compliant? Answer 'Yes' or 'No' and explain why."
        )

        if agent["model_name"] == "gpt-4":
            llm = ChatOpenAI(
                model_name="gpt-4",
                openai_api_key=os.getenv("OPEN_AI_API_KEY")
            )
            response = llm.invoke([HumanMessage(content=debate_prompt)])
            return response.content.strip()

        elif agent["model_name"] == "tinyllama":
            # Call your local LLaMA or Ollama service
            response_text = llm_service.query_llama_via_ollama(prompt=debate_prompt)
            return response_text

        else:
            return "Error: Model not recognized."

    def run_debate_sequence(self, db: Session, session_id: str | None, agent_ids: list[int], data_sample: str):
        """
        1) If session_id is None, create a new one.
        2) Store these agents in the DebateSession table in the specified order.
        3) Iteratively call each agent, feeding the previous agent's response into the next prompt.
        4) Return the entire chain of results.
        """
        if not session_id:
            session_id = str(uuid.uuid4())

        # 1. Clear out any existing debate records if you want a fresh chain each time,
        #    or skip this if you want to *append* to an existing session.
        #    For now, we do a fresh approach:
        db.query(DebateSession).filter(DebateSession.session_id == session_id).delete()
        db.commit()

        # 2. Insert these agents in order
        for idx, agent_id in enumerate(agent_ids):
            db.add(DebateSession(
                session_id=session_id,
                compliance_agent_id=agent_id,
                debate_order=idx + 1
            ))
        db.commit()

        # 3. Actually run the "sequence" of debates
        #    We'll keep a "context" string that grows after each agent's turn.
        #    Or each agent can produce a "Yes"/"No", but we show how to store it all in "context."
        debate_records = self.load_debate_agents(session_id)
        debate_chain = []  # collect each agent's output

        # We'll store the entire "context" in a string
        # The initial context is the user data, or possibly you want a more structured approach
        context = f"Initial data:\n{data_sample}\n"

        for agent in debate_records:
            # Build a custom prompt that includes the current "context"
            # so the agent sees what happened previously
            agent_prompt = (
                f"{context}\n"
                f"Agent {agent['name']}, please respond with 'Yes' or 'No' plus reasoning.\n"
                "If you are second or later in the sequence, you can see the prior responses above.\n"
            )

            # Actually call the agent
            agent_response = self.single_agent_run(agent, agent_prompt)

            # Update "context" by appending this agent's response
            context += f"\n{agent['name']} responded:\n{agent_response}\n"

            # Store in the chain
            debate_chain.append({
                "agent_id": agent["id"],
                "agent_name": agent["name"],
                "response": agent_response
            })

        return session_id, debate_chain


    def single_agent_run(self, agent: dict, prompt: str) -> str:
        """
        Runs a single agent with the given prompt and returns the raw text.
        """
        if agent["model_name"] == "gpt-4":
            llm = ChatOpenAI(
                model_name="gpt-4",
                openai_api_key=os.getenv("OPEN_AI_API_KEY")
            )
            response = llm.invoke([HumanMessage(content=prompt)])
            return response.content.strip()

        elif agent["model_name"] == "tinyllama":
            # Call your local LLaMA or Ollama service
            response_text = llm_service.query_llama_via_ollama(prompt=prompt)
            return response_text.strip()

        else:
            return "Error: Unknown model_name."
