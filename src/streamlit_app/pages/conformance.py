import streamlit as st
import requests

# FastAPI API endpoint
LLM_API = "http://fastapi:9020"

st.set_page_config(page_title="Compliance Checker", layout="wide")
st.title("🔍 AI Compliance Checker")

# ----------------------------------------------------------------------
# 1) CREATE COMPLIANCE AGENT
# ----------------------------------------------------------------------
st.header("➕ Create a New Compliance Agent")
agent_name = st.text_input("Agent Name")
model_name = st.selectbox("Model Type", ["gpt-4", "tinyllama"])
system_prompt = st.text_area("System Prompt (Define the Agent's Role)")
user_prompt_template = st.text_area("User Prompt Template (Use {data_sample} as a placeholder)")

if st.button("Save Agent"):
    if not agent_name or not model_name or not system_prompt or not user_prompt_template:
        st.warning("Please fill in all fields before saving.")
    else:
        agent_payload = {
            "name": agent_name,
            "model_name": model_name,
            "system_prompt": system_prompt,
            "user_prompt_template": user_prompt_template
        }
        response = requests.post(f"{LLM_API}/create-agent", json=agent_payload)
        
        if response.status_code == 200:
            st.success(f"✅ Compliance Agent '{agent_name}' created successfully!")
        else:
            st.error(f"❌ Error: {response.status_code}, {response.text}")

st.write("---")

# ----------------------------------------------------------------------
# 2) FETCH ALL AGENTS FOR SELECTION
# ----------------------------------------------------------------------
agents_response = requests.get(f"{LLM_API}/get-agents")
if agents_response.status_code == 200:
    agents_data = agents_response.json().get("agents", [])
    # Build a dict: name -> id
    agent_choices = {agent["name"]: agent["id"] for agent in agents_data}
    st.info(f"Loaded {len(agent_choices)} agents from the database.")
else:
    agent_choices = {}
    st.warning("Could not load agents from the server.")

# ----------------------------------------------------------------------
# 3) COMPLIANCE CHECK (AUTO-DEBATE IF ANY FAIL)
# ----------------------------------------------------------------------
st.header("Compliance Check")
data_sample = st.text_area("Data Sample for Compliance", key="compliance_data")
selected_agents_for_check = st.multiselect("Select Agents for Compliance Check",
                                            list(agent_choices.keys()))

if st.button("Check Compliance"):
    if not data_sample or not selected_agents_for_check:
        st.warning("Please provide both data and select at least one agent.")
    else:
        # Convert selected agent names to IDs
        agent_ids = [agent_choices[name] for name in selected_agents_for_check]
        payload = {"data_sample": data_sample, "agent_ids": agent_ids}
        response = requests.post(f"{LLM_API}/compliance-check", json=payload)
        
        if response.status_code == 200:
            result = response.json()
            st.subheader("Compliance Check Results")
            st.json(result)
            
            # If the result includes "debate_results" and "session_id",
            # it means at least one agent said "No" and the server
            # automatically triggered a debate.
            if "overall_compliance" in result and not result["overall_compliance"]:
                st.warning("One or more agents found non-compliance. A debate was triggered.")
                if "session_id" in result:
                    st.write(f"Debate session_id: {result['session_id']}")
                    st.write("Debate Results:")
                    st.json(result.get("debate_results", {}))
        else:
            st.error(f"❌ Error: {response.status_code}, {response.text}")

st.write("---")


# ----------------------------------------------------------------------
# 5) (Optional) MULTI-AGENT DEBATE Endpoint
# ----------------------------------------------------------------------
st.header("🧩 Custom Debate Sequence")
custom_session_id = st.text_input("Optional Session ID (leave blank to generate a new one)")

# We'll let them pick a single agent at a time in order
# For example, user can pick agent1, then agent2, then agent3...
# (You can design a more user-friendly approach if you wish)
sequence_of_agents = []
new_agent_name = st.selectbox("Pick next agent in the sequence", ["--Select--"] + list(agent_choices.keys()))
if st.button("Add Agent to Sequence"):
    if new_agent_name != "--Select--":
        # We'll store them in a session state list
        if "sequence_of_agents" not in st.session_state:
            st.session_state["sequence_of_agents"] = []
        st.session_state["sequence_of_agents"].append(new_agent_name)
        st.success(f"Added {new_agent_name} to the sequence!")
    
if "sequence_of_agents" in st.session_state:
    sequence_of_agents = st.session_state["sequence_of_agents"]
    st.write("Current Sequence of Agents:", sequence_of_agents)

seq_data_sample = st.text_area("Data for the Debate Sequence")

if st.button("Run Debate Sequence"):
    if not sequence_of_agents:
        st.warning("No agents in sequence!")
    else:
        # Convert agent names to IDs
        agent_ids_in_order = [agent_choices[name] for name in sequence_of_agents]
        payload = {
            "session_id": custom_session_id if custom_session_id else None,
            "agent_ids": agent_ids_in_order,
            "data_sample": seq_data_sample
        }
        resp = requests.post(f"{LLM_API}/debate-sequence", json=payload)
        if resp.status_code == 200:
            result = resp.json()
            st.write("**Debate Sequence Results**")
            st.json(result)
        else:
            st.error(f"Error {resp.status_code}: {resp.text}")