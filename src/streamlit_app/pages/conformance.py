import streamlit as st
import requests
import torch
torch.classes.__path__ = [] 

# FastAPI endpoint for compliance checking
LLM_API = "http://fastapi:9020"

st.set_page_config(page_title="Compliance Checker", layout="wide")

st.title("🔍 AI Compliance Checker")

# ---- USER INPUT ----
st.header("Enter Data for Compliance Check")
data_sample = st.text_area("Enter Data Sample")

# ---- STANDARD SELECTION ----
dummy_standards = [
    "Standard Section 1: Data should be within the range of 1 to 10.",
    "Standard Section 2: Data should contain only positive numbers.",
    "Standard Section 3: Data should not exceed a length of 100 characters.",
    "Standard Section 4: Data should not include any special characters.",
    "Standard Section 5: Data should contain at least one uppercase letter."
]

st.write("### Compliance Standards:")
for standard in dummy_standards:
    st.write(f"- {standard}")

# ---- COMPLIANCE CHECK BUTTON ----
if st.button("Check Compliance"):
    if not data_sample:
        st.warning("Please enter a data sample.")
    else:
        payload = {
            "data_sample": data_sample,
            "standards": dummy_standards  # Sending standards as list
        }
        
        response = requests.post(f"{LLM_API}/compliance", json=payload)
        
        if response.status_code == 200:
            compliance_result = response.json().get("compliant", False)
            if compliance_result:
                st.success("✅ Data is COMPLIANT with the standards!")
            else:
                st.error("❌ Data is NOT COMPLIANT with the standards.")
        else:
            st.error(f"Error: {response.status_code}, {response.text}")
