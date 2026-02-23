import streamlit as st
import requests
import pandas as pd
import os
import json

# Configuration
st.set_page_config(page_title="Excel Q&A MVP", page_icon="📊", layout="wide")
API_URL = "http://localhost:8000"

st.title("📊 Excel Q&A Assistant")
st.markdown("Upload your Excel file and ask questions about your data!")

if "messages" not in st.session_state:
    st.session_state.messages = []
if "uploaded_filename" not in st.session_state:
    st.session_state.uploaded_filename = None

with st.sidebar:
    st.header("1. Upload Data")
    uploaded_file = st.file_uploader("Upload Excel File", type=["xls", "xlsx"])
    
    if uploaded_file is not None:
        if st.button("Process File"):
            with st.spinner("Uploading and analyzing..."):
                files = {"file": (uploaded_file.name, uploaded_file.getvalue(), "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")}
                try:
                    response = requests.post(f"{API_URL}/upload/", files=files)
                    if response.status_code == 200:
                        data = response.json()
                        st.success(f"Successfully uploaded: {data['filename']}")
                        st.session_state.uploaded_filename = data['filename']
                        st.write("### Data Summary:")
                        st.json(data['summary'])
                    else:
                        st.error(f"Error: {response.text}")
                except Exception as e:
                    st.error(f"Connection error: {e}. Is the backend running?")

st.header("2. Ask Questions")

for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

if prompt := st.chat_input("Ask a question about your data (e.g., 'How many high risk items?')"):
    st.chat_message("user").markdown(prompt)
    st.session_state.messages.append({"role": "user", "content": prompt})

    if not st.session_state.uploaded_filename:
        st.warning("Please upload and process an Excel file first.")
    else:
        with st.chat_message("assistant"):
            with st.spinner("Thinking..."):
                try:
                    payload = {
                        "filename": st.session_state.uploaded_filename,
                        "query": prompt
                    }
                    res = requests.post(f"{API_URL}/query/", json=payload)
                    if res.status_code == 200:
                        data = res.json()
                        answer = data.get("answer", "No answer provided.")
                        q_type = data.get("type", "unknown")
                        
                        response_text = f"**[{q_type.upper()}]**\n\n{answer}"
                        st.markdown(response_text)
                        
                        st.session_state.messages.append({"role": "assistant", "content": response_text})
                    else:
                        st.error(f"Backend Error: {res.text}")
                except Exception as e:
                    st.error(f"Failed to connect to backend: {e}")
