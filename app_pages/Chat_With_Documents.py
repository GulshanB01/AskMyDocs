import streamlit as st

from frontend.api_client import ApiClientError, get, post
from frontend.auth import require_login


st.title("Chat With Documents")

current_user = require_login()

if "messages" not in st.session_state:
    st.session_state["messages"] = []
if "selected_doc" not in st.session_state:
    st.session_state["selected_doc"] = None
if "selected_doc_id" not in st.session_state:
    st.session_state["selected_doc_id"] = None
if "chat_active" not in st.session_state:
    st.session_state["chat_active"] = False


def load_chat_history(selected_doc_name: str):
    try:
        st.session_state["messages"] = get(
            "/chat/history",
            {"selected_document_name": selected_doc_name},
        )
    except ApiClientError as exc:
        st.error(str(exc))
        st.session_state["messages"] = []


def start_chat(doc_name: str, doc_id):
    st.session_state["selected_doc"] = doc_name
    st.session_state["selected_doc_id"] = doc_id
    st.session_state["chat_active"] = True
    load_chat_history(doc_name)


def close_chat():
    st.session_state["selected_doc"] = None
    st.session_state["selected_doc_id"] = None
    st.session_state["chat_active"] = False
    st.session_state["messages"] = []


def send_message(input_message: str):
    try:
        post(
            "/chat/ask",
            {
                "question": input_message,
                "document_id": st.session_state["selected_doc_id"],
                "selected_document_name": st.session_state["selected_doc"],
            },
        )
        load_chat_history(st.session_state["selected_doc"])
        st.rerun()
    except ApiClientError as exc:
        st.error(str(exc))


try:
    quota = get("/chat/quota")
except ApiClientError as exc:
    st.error(str(exc))
    quota = {"daily_limit": 0, "remaining_questions": 0}

remaining = quota["remaining_questions"]
st.caption(f"{remaining} of {quota['daily_limit']} questions remaining today")

if not st.session_state["chat_active"]:
    st.subheader("Select a document to chat with")
    try:
        documents = get("/documents")
    except ApiClientError as exc:
        st.error(str(exc))
        documents = []

    doc_options = {"All Documents": None}
    doc_options.update({document["name"]: document["id"] for document in documents})

    selected = st.selectbox("Choose document", list(doc_options.keys()))
    if st.button("Start Chat"):
        start_chat(selected, doc_options[selected])
        st.rerun()
else:
    col1, col2 = st.columns([4, 1])
    with col1:
        st.caption(f"Chatting with: **{st.session_state['selected_doc']}**")
    with col2:
        if st.button("Close Chat"):
            close_chat()
            st.rerun()

    for message in st.session_state["messages"]:
        with st.chat_message(message["role"]):
            st.write(message["content"])
            if message["groundedness_label"]:
                label = message["groundedness_label"]
                score = message["groundedness_score"] or 0
                if label == "Grounded":
                    st.success(f"{label} · Faithfulness {score:.0%}")
                else:
                    st.warning(f"{label} · Faithfulness {score:.0%}")
                if message["groundedness_reason"]:
                    st.caption(message["groundedness_reason"])
            if message["references"]:
                with st.expander("References"):
                    for reference in message["references"]:
                        st.write(reference)

    input_message = st.chat_input("Ask a question", disabled=remaining <= 0)
    if input_message:
        send_message(input_message)
