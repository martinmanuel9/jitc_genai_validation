import streamlit as st
import requests
import fitz  
from docx import Document
import io

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

# Document Upload Section
st.sidebar.subheader("Upload Documents")
collection_name = st.sidebar.text_input("Collection for Uploaded Documents")
uploaded_files = st.sidebar.file_uploader("Drop files here", type=["pdf", "docx", "txt"], accept_multiple_files=True)

def extract_text_from_pdf(pdf_file):
    """Extract text from a PDF file."""
    text = ""
    pdf_document = fitz.open(stream=pdf_file.read(), filetype="pdf")
    for page in pdf_document:
        text += page.get_text("text") + "\n"
    return text

def extract_text_from_docx(docx_file):
    """Extract text from a DOCX file."""
    text = ""
    doc = Document(io.BytesIO(docx_file.read()))
    for para in doc.paragraphs:
        text += para.text + "\n"
    return text

# Process and store documents
if uploaded_files and st.sidebar.button("Process & Store Documents"):
    if not collection_name:
        st.sidebar.error("Please specify a collection name.")
    else:
        for uploaded_file in uploaded_files:
            if uploaded_file.type == "application/pdf":
                text_content = extract_text_from_pdf(uploaded_file)
            elif uploaded_file.type == "application/vnd.openxmlformats-officedocument.wordprocessingml.document":
                text_content = extract_text_from_docx(uploaded_file)
            elif uploaded_file.type == "text/plain":
                text_content = uploaded_file.read().decode("utf-8")
            else:
                st.sidebar.warning(f"Unsupported file type: {uploaded_file.name}")
                continue

            # Store extracted text in ChromaDB
            document_id = uploaded_file.name  # Use filename as document ID
            data = {
                "collection_name": collection_name,
                "documents": [text_content],
                "ids": [document_id]
            }
            response = requests.post(f"{CHROMADB_API}/documents/add", json=data)

            if response.status_code == 200:
                st.sidebar.success(f"Stored '{uploaded_file.name}' in '{collection_name}'.")
            else:
                st.sidebar.error(f"Failed to store '{uploaded_file.name}': {response.json()['detail']}")

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
