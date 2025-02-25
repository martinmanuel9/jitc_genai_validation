import streamlit as st
import requests
from utils import fetch_collections

# FastAPI endpoints
HISTORY_ENDPOINT = "http://fastapi:9020/chat-history"
LLM_API = "http://fastapi:9020/chat"
RAG_API = "http://fastapi:9020/chat-rag"
CHROMADB_API = "http://chromadb:8020"

st.set_page_config(page_title="Chatbot", layout="wide")

st.title("JITC GenAI Chatbot with RAG")

# Fetch collections from ChromaDB
collections = fetch_collections()

# Let user choose "Direct GPT-4" vs. "GPT-4 with Retrieval"
mode = st.selectbox("Select Mode:", ["Direct GPT-4", "RAG (Chroma + GPT-4)"])

# Collection selection for RAG mode
collection_name = None
if mode == "RAG (Chroma + GPT-4)" and collections:
    collection_name = st.selectbox("Select a ChromaDB Collection:", collections)

user_input = st.text_input("Ask me something:")

if st.button("Get Response"):
    if user_input:
        if mode == "RAG (Chroma + GPT-4)" and not collection_name:
            st.error("Please select a collection for RAG mode.")
        else:
            api_url = RAG_API if mode == "RAG (Chroma + GPT-4)" else LLM_API
            payload = {"query": user_input}

            if mode == "RAG (Chroma + GPT-4)":
                payload["collection_name"] = collection_name  # Include collection

            response = requests.post(api_url, json=payload)

            if response.status_code == 200:
                st.success("Response:")
                st.write(response.json()["response"])
            else:
                st.error("Error: " + response.text)

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
            st.error("Failed to load chat history.")
    except Exception as e:
        st.error(str(e))
