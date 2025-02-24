import streamlit as st
import requests

# FastAPI endpoints
CHAT_ENDPOINT = "http://fastapi:9020/chat"
HISTORY_ENDPOINT = "http://fastapi:9020/chat-history"

st.set_page_config(page_title="Chatbot", layout="wide")
st.title("JITC GenAI Chatbot")

# ---- CHATBOT INTERFACE ----
st.header("Enter Your Query Below")
user_input = st.text_input("Ask me something:")

if st.button("Get Response") or (user_input and user_input != st.session_state.get('previous_input', '')):
    if user_input:
        st.session_state['previous_input'] = user_input

        response = requests.post(CHAT_ENDPOINT, json={"query": user_input})
        if response.status_code == 200:
            st.success("Response:")
            st.write(response.json()["response"])
        else:
            st.error("Error: " + response.json()["detail"])

# ---- LOAD CHAT HISTORY ----
st.header("Chat History")
if st.button("Load Chat History"):
    try:
        response = requests.get(HISTORY_ENDPOINT)
        if response.status_code == 200:
            data = response.json()  # This should be a list of chat records
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
