import streamlit as st
import requests

# FastAPI endpoint
LLM_API = "http://fastapi:9000/chat"

st.set_page_config(page_title="Chatbot", layout="wide")

st.title("JITC GenAI Chatbot")

# ---- CHATBOT INTERFACE ----
st.header("Enter Your Query Below")
user_input = st.text_input("Ask me something:")

if st.button("Get Response") or (user_input and user_input != st.session_state.get('previous_input', '')):
    if user_input:
        st.session_state['previous_input'] = user_input
        response = requests.post(LLM_API, json={"query": user_input})
        
        if response.status_code == 200:
            st.success("Response:")
            st.write(response.json()["response"])
        else:
            st.error("Error: " + response.json()["detail"])
