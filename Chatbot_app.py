import streamlit as st
from dotenv import load_dotenv
import os

# Import your chatbot function
from Chatbot import chatbot   # assuming you saved your code in chatbot.py

# Load environment variables
load_dotenv()

# --- Page Configuration ---
st.set_page_config(page_title="AllOfTech's Chatbot", page_icon="🍁", layout="centered")
st.title("Welcome TO AllOfTech's Chatbot")

# --- Sidebar Settings ---
with st.sidebar:
    st.title("Chat Settings")
    def clear_chat_history():
        st.session_state.messages = [{
            "role": "assistant",
            "content": "Assalamu alaikum! 🌟 Welcome to AllOfTech’s chatbot! I’m here to answer your questions about our innovative solutions in AI/ML, blockchain, web and mobile app development, UX/UI design, and branding. How can we help bring your ideas to life?"
        }]
    st.button("Clear Chat History", on_click=clear_chat_history)

# --- Initialize Chat History ---
if "messages" not in st.session_state:
    st.session_state.messages = [{
        "role": "assistant",
        "content": "Assalamu alaikum! 🌟 Welcome to AllOfTech’s chatbot! I’m here to answer your questions about our innovative solutions in AI/ML, blockchain, web and mobile app development, UX/UI design, and branding. How can we help bring your ideas to life?"
    }]

# --- Display Chat Messages ---
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# --- Chat Input Handling ---
if prompt := st.chat_input("Type your message..."):
    # Append user message
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    # Generate and display bot response
    with st.chat_message("assistant"):
        with st.spinner("Generating response..."):
            response = chatbot(prompt, product="AllOfTech")
            st.markdown(response)

    # Append assistant response
    st.session_state.messages.append({"role": "assistant", "content": response})
