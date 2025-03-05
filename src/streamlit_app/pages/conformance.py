import streamlit as st
import requests
from utils import fetch_collections
import torch
torch.classes.__path__ = [] 

# FastAPI API endpoint
LLM_API = "http://fastapi:9020"

# Fetch collections from ChromaDB
collections = fetch_collections()



st.set_page_config(page_title="Compliance Checker", layout="wide")
st.title("🔍 AI Compliance Checker")

# ----------------------------------------------------------------------
#  CREATE COMPLIANCE AGENT
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
# FETCH ALL AGENTS FOR SELECTION
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
# COMPLIANCE CHECK
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
# Custom COMPLIANCE CHECK
# ----------------------------------------------------------------------            
st.header("Custom Debate Sequence")
custom_session_id = st.text_input("Optional Session ID (leave blank to generate a new one)")

sequence_of_agents = []
new_agent_name = st.selectbox(
    "Pick next agent in the sequence", 
    ["--Select--"] + list(agent_choices.keys()), 
    key="regular_sequence_select"
)
if st.button("Add Agent to Sequence", key="add_agent_regular"):
    if new_agent_name != "--Select--":
        # We'll store them in a session state list
        if "sequence_of_agents" not in st.session_state:
            st.session_state["sequence_of_agents"] = []
        st.session_state["sequence_of_agents"].append(new_agent_name)
        st.success(f"Added {new_agent_name} to the sequence!")
    
if "sequence_of_agents" in st.session_state:
    sequence_of_agents = st.session_state["sequence_of_agents"]
    st.write("Current Sequence of Agents:", sequence_of_agents)

seq_data_sample = st.text_area("Data for the Debate Sequence", key="debate_seq_data")

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

st.write("---") 
# ----------------------------------------------------------------------
# RAG COMPLIANCE CHECK
# ----------------------------------------------------------------------            
st.header("RAG-Based Check")
rag_query_text = st.text_area("Enter your RAG query (user prompt)")

# Collection selection for RAG modes
rag_mode = st.selectbox("Select RAG Mode:", ["RAG (Chroma + GPT-4)", "RAG (Meta Llama)"], key="rag_mode_select")

collection_name = None
if rag_mode in ["RAG (Chroma + GPT-4)", "RAG (Meta Llama)"] and collections:
    collection_name = st.selectbox("Select a ChromaDB Collection:", collections)
    
selected_rag_agents = st.multiselect(
    "Select Agents for RAG Check", 
    list(agent_choices.keys())
)

if st.button("Run RAG Check"):
    if not rag_query_text or not selected_rag_agents:
        st.warning("Please provide a query and select agents.")
    else:
        agent_ids = [agent_choices[name] for name in selected_rag_agents]
        payload = {
            "query_text": rag_query_text,
            "collection_name": collection_name,
            "agent_ids": agent_ids
        }
        response = requests.post(f"{LLM_API}/rag-check", json=payload)
        
        if response.status_code == 200:
            result = response.json()
            st.json(result)
        else:
            st.error(f"Error {response.status_code}: {response.text}")

st.write("---")

# ----------------------------------------------------------------------
# FETCH ALL AGENTS FOR SELECTION for custom
# ----------------------------------------------------------------------
agents_response_custom = requests.get(f"{LLM_API}/get-agents")
if agents_response_custom.status_code == 200:
    agents_data = agents_response_custom.json().get("agents", [])
    # Build a dict: name -> id
    agent_choices_custom = {agent["name"]: agent["id"] for agent in agents_data}
    st.info(f"Loaded {len(agent_choices_custom)} agents from the database.")
else:
    agent_choices_custom = {}
    st.warning("Could not load agents from the server.")

# ----------------------------------------------------------------------
# Custom RAG COMPLIANCE CHECK
# ----------------------------------------------------------------------            
st.header("Custom RAG Debate Sequence")

custom_sequence_of_agents = []
custom_new_agent_name = st.selectbox(
    "Pick next agent in the sequence (RAG)", 
    ["--Select--"] + list(agent_choices_custom.keys()), 
    key="custom_rag_sequence_select"
)
if st.button("Add Agent to RAG Sequence", key="add_agent_rag"):
    if custom_new_agent_name != "--Select--":
        # We'll store them in a session state list
        if "custom_sequence_of_agents" not in st.session_state:
            st.session_state["custom_sequence_of_agents"] = []
        st.session_state["custom_sequence_of_agents"].append(custom_new_agent_name)
        st.success(f"Added {custom_new_agent_name} to the sequence!")
    
if "custom_sequence_of_agents" in st.session_state:
    custom_sequence_of_agents = st.session_state["custom_sequence_of_agents"]
    st.write("Current Sequence of Agents:", custom_sequence_of_agents)

rag_query_text_custom = st.text_area("Data for the RAG Debate Sequence", key="rag_debate_seq_data")


# Collection selection for RAG modes
custom_rag_mode = st.selectbox("Select RAG Mode:", ["RAG (Chroma + GPT-4)", "RAG (Meta Llama)"], key="custom_rag_mode_select")

custom_collection_name = None
if custom_rag_mode in ["RAG (Chroma + GPT-4)", "RAG (Meta Llama)"] and collections:
    custom_collection_name = st.selectbox(
        "Select a ChromaDB Collection:", 
        collections, 
        key="custom_chromadb_collection"
    )
    
custom_selected_rag_agents = st.multiselect(
    "Select Agents for Custom RAG Check", 
    list(agent_choices.keys()), 
    key="custom_rag_agents_multiselect"
)

if st.button("Run Custom RAG Check"):
    if not rag_query_text_custom or not custom_selected_rag_agents:
        st.warning("Please provide a query and select agents.")
    else:
        custom_agent_ids = [agent_choices_custom[name] for name in custom_selected_rag_agents]
        payload = {
            "query_text": rag_query_text_custom,
            "collection_name": custom_collection_name,
            "agent_ids": custom_agent_ids
        }
        response = requests.post(f"{LLM_API}/rag-debate-sequence", json=payload)
        
        if response.status_code == 200:
            result = response.json()
            st.json(result)
        else:
            st.error(f"Error {response.status_code}: {response.text}")