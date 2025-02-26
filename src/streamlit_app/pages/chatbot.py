import streamlit as st
import requests
import nest_asyncio
from utils import fetch_collections
import torch
torch.classes.__path__ = [] 

# Apply asyncio patch to prevent runtime errors
nest_asyncio.apply()

# FastAPI endpoints
HISTORY_ENDPOINT = "http://fastapi:9020/chat-history"
LLM_API = "http://fastapi:9020/chat"
RAG_API = "http://fastapi:9020/chat-rag"
CHROMADB_API = "http://chromadb:8020"

st.set_page_config(page_title="Chatbot", layout="wide")
st.title("JITC GenAI Chatbot with RAG")

# Fetch collections from ChromaDB
collections = fetch_collections()

# Let user choose between "Direct GPT-4" and "GPT-4 with Retrieval"
mode = st.selectbox("Select Mode:", ["Direct GPT-4", "RAG (Chroma + GPT-4)"])

# Collection selection for RAG mode
collection_name = None
if mode == "RAG (Chroma + GPT-4)" and collections:
    collection_name = st.selectbox("Select a ChromaDB Collection:", collections)

user_input = st.text_input("Ask me something:")

if st.button("Get Response"):
    if user_input:
        # Ensure valid input for RAG mode
        if mode == "RAG (Chroma + GPT-4)" and not collection_name:
            st.error("Please select a collection for RAG mode.")
        else:
            api_url = RAG_API if mode == "RAG (Chroma + GPT-4)" else LLM_API

            payload = {"query": user_input}
            if mode == "RAG (Chroma + GPT-4)":
                payload["collection_name"] = collection_name

            try:
                response = requests.post(api_url, json=payload)
                response_json = response.json()

                if response.status_code == 200:
                    st.success("Response:")
                    st.write(response_json.get("response", "No response received."))
                else:
                    st.error(f"Error {response.status_code}: {response_json.get('detail', response.text)}")

            except requests.exceptions.RequestException as e:
                st.error(f"Request failed: {e}")

# ---- LOAD CHAT HISTORY ----
st.header("Chat History")
if st.button("Load Chat History"):
    try:
        response = requests.get(HISTORY_ENDPOINT)
        if response.status_code == 200:
            data = response.json()
            if not data:
                st.info("No chat history found.")
            else:
                for record in data:
                    st.write(f"**User**: {record['user_query']}")
                    st.write(f"**Assistant**: {record['response']}")
                    st.write(f"_Timestamp_: {record['timestamp']}")
                    st.write("---")
        else:
            st.error(f"Failed to load chat history. Status: {response.status_code}")

    except requests.exceptions.RequestException as e:
        st.error(f"Request failed: {e}")
