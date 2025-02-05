import streamlit as st
import requests

# FastAPI endpoints
CHROMADB_API = "http://chromadb:8000"  
LLM_API = "http://fastapi:9000/chat"  

st.title("JITC GenAI Conformance Chatbot")

# Sidebar for Collection Management
st.sidebar.header("ChromaDB Collections")

# Fetch existing collections
if st.sidebar.button("List Collections"):
    response = requests.get(f"{CHROMADB_API}/collections")
    if response.status_code == 200:
        collections = response.json()
        st.sidebar.write("Available Collections:", collections)
    else:
        st.sidebar.error("Error fetching collections.")

# Create a new collection
new_collection_name = st.sidebar.text_input("New Collection Name")
if st.sidebar.button("Create Collection"):
    response = requests.post(f"{CHROMADB_API}/collection/create", params={"collection_name": new_collection_name})
    if response.status_code == 200:
        st.sidebar.success(f"Collection '{new_collection_name}' created!")
    else:
        st.sidebar.error(response.json()["detail"])

# Delete a collection
delete_collection_name = st.sidebar.text_input("Delete Collection Name")
if st.sidebar.button("Delete Collection"):
    response = requests.delete(f"{CHROMADB_API}/collection", params={"collection_name": delete_collection_name})
    if response.status_code == 200:
        st.sidebar.success(f"Collection '{delete_collection_name}' deleted!")
    else:
        st.sidebar.error(response.json()["detail"])

# Document Management
st.sidebar.subheader("Manage Documents")
collection_name = st.sidebar.text_input("Collection for Documents")
document_id = st.sidebar.text_input("Document ID")
document_content = st.sidebar.text_area("Document Content")

if st.sidebar.button("Add Document"):
    data = {"collection_name": collection_name, "documents": [document_content], "ids": [document_id]}
    response = requests.post(f"{CHROMADB_API}/documents/add", json=data)
    if response.status_code == 200:
        st.sidebar.success("Document added successfully!")
    else:
        st.sidebar.error(response.json()["detail"])

if st.sidebar.button("Remove Document"):
    data = {"collection_name": collection_name, "ids": [document_id]}
    response = requests.post(f"{CHROMADB_API}/documents/remove", json=data)
    if response.status_code == 200:
        st.sidebar.success("Document removed successfully!")
    else:
        st.sidebar.error(response.json()["detail"])

# Chatbot Interface
st.header("Enter your query below:")
user_input = st.text_input("Enter your query:")

# Using a button or Enter key to submit
if st.button("Get Response") or (user_input and user_input != st.session_state.get('previous_input', '')):
    if user_input:  # Only process if there's input
        st.session_state['previous_input'] = user_input  # Store current input
        response = requests.post(LLM_API, json={"query": user_input})
        if response.status_code == 200:
            st.write("🤖 Response:", response.json()["response"])
        else:
            st.error("Error: " + response.json()["detail"])
