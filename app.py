"""
HR & Onboarding AI Assistant — Streamlit entry point (OpenAI version).

Run with:
    streamlit run app.py
"""

import os
import sys
from pathlib import Path

import streamlit as st
from dotenv import load_dotenv
from openai import OpenAI

sys.path.append(str(Path(__file__).resolve().parent))
from src.system_prompt import SYSTEM_PROMPT, COMPANY_NAME
from src.rag_engine import build_or_load_vectorstore, retrieve_context, rebuild_index

load_dotenv()

OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o")
API_KEY = os.getenv("OPENAI_API_KEY")

st.set_page_config(
    page_title=f"{COMPANY_NAME} HR Assistant",
    page_icon="💼",
    layout="centered",
)


# ---------- Cached resources (loaded once per server process) ----------

@st.cache_resource(show_spinner="Loading HR knowledge base...")
def get_vectorstore():
    return build_or_load_vectorstore()


@st.cache_resource
def get_client():
    if not API_KEY:
        return None
    return OpenAI(api_key=API_KEY)


# ---------- Sidebar ----------

with st.sidebar:
    st.markdown(f"### 💼 {COMPANY_NAME} HR Assistant")
    st.caption("Ask about PTO, benefits, remote work, onboarding steps, and more.")
    st.divider()

    if st.button("🔄 Rebuild knowledge base", help="Run this after replacing files in data/"):
        with st.spinner("Rebuilding index from documents in data/..."):
            rebuild_index()
        st.cache_resource.clear()
        st.success("Knowledge base rebuilt. Reloading...")
        st.rerun()

    st.divider()
    st.caption(
        "This assistant answers from the company's own HR documents. "
        "For pay disputes, disciplinary matters, or harassment/safety "
        "concerns, it will direct you to a human in HR."
    )

    if st.button("🗑️ Clear chat"):
        st.session_state.pop("messages", None)
        st.rerun()


# ---------- Main chat UI ----------

st.title(f"💼 {COMPANY_NAME} HR & Onboarding Assistant")
st.caption("Grounded in your company's HR policy documents · Powered by OpenAI")

if not API_KEY:
    st.error(
        "No OPENAI_API_KEY found. Copy `.env.example` to `.env`, add your "
        "key, then restart the app."
    )
    st.stop()

if "messages" not in st.session_state:
    st.session_state.messages = [
        {
            "role": "assistant",
            "content": (
                f"Hi! I'm Ada, your {COMPANY_NAME} HR assistant. Ask me about "
                "PTO, benefits, remote work, or your onboarding checklist."
            ),
        }
    ]

for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

user_question = st.chat_input("Ask about a policy, benefit, or onboarding step...")

if user_question:
    st.session_state.messages.append({"role": "user", "content": user_question})
    with st.chat_message("user"):
        st.markdown(user_question)

    with st.chat_message("assistant"):
        try:
            vectorstore = get_vectorstore()
            context = retrieve_context(vectorstore, user_question)
        except FileNotFoundError as e:
            st.error(str(e))
            st.stop()

        client = get_client()

        context_block = (
            f"CONTEXT (retrieved from company HR documents):\n{context}"
            if context
            else "CONTEXT: (no relevant document chunks were found for this question)"
        )

        # Short rolling history for conversational context (excludes the
        # question we just appended; it's re-added below with the context).
        history = [
            {"role": m["role"], "content": m["content"]}
            for m in st.session_state.messages[-8:-1]
            if m["role"] in ("user", "assistant")
        ]

        messages = (
            [{"role": "system", "content": SYSTEM_PROMPT}]
            + history
            + [
                {
                    "role": "user",
                    "content": f"{context_block}\n\nEMPLOYEE QUESTION: {user_question}",
                }
            ]
        )

        def stream_answer():
            stream = client.chat.completions.create(
                model=OPENAI_MODEL,
                messages=messages,
                temperature=0.2,  # low = more faithful to the policy text
                max_tokens=800,
                stream=True,
            )
            for chunk in stream:
                if chunk.choices and chunk.choices[0].delta.content:
                    yield chunk.choices[0].delta.content

        try:
            answer = st.write_stream(stream_answer())
        except Exception as e:
            answer = (
                "Sorry, I couldn't reach the AI service. Please check your "
                f"OPENAI_API_KEY, billing, and internet connection.\n\n`{e}`"
            )
            st.error(answer)

    st.session_state.messages.append({"role": "assistant", "content": answer})
