import time

import streamlit as st

from frontend.api_client import ApiClientError, delete, get, upload
from frontend.auth import require_login


st.title("Manage Documents")

require_login()


def delete_document(document_id: int):
    try:
        delete(f"/documents/{document_id}")
    except ApiClientError as exc:
        st.error(str(exc))


@st.dialog("Upload document")
def upload_document_dialog_open():
    pdf_file = st.file_uploader("Upload PDF file", type="pdf")
    if pdf_file is not None:
        if st.button("Upload", key="confirm-upload-document-button"):
            try:
                upload("/documents/upload", pdf_file.name, pdf_file.getvalue())
                st.success("Document added to the processing queue.")
                st.rerun()
            except ApiClientError as exc:
                st.error(str(exc))


st.button("Upload Document", key="upload-document-button", on_click=upload_document_dialog_open)

try:
    jobs = [
        job
        for job in get("/jobs")
        if job["status"] in ["queued", "processing", "failed"]
    ][:5]
except ApiClientError as exc:
    st.error(str(exc))
    jobs = []

if jobs:
    st.subheader("Processing Queue")
    for job in jobs:
        with st.container(border=True):
            st.write(job["document_name"])
            st.progress(job["progress"], text=f"{job['status'].title()}: {job['message']}")
            if job["error"]:
                st.error(job["error"])
    if any(job["status"] in ["queued", "processing"] for job in jobs):
        time.sleep(2)
        st.rerun()

try:
    documents = get("/documents")
except ApiClientError as exc:
    st.error(str(exc))
    documents = []

if documents:
    st.subheader("Your Documents")
    for document in documents:
        document_container = st.container(border=True)
        document_container.write(document["name"])
        if document["tags"]:
            document_container.write(f"Tags: {', '.join(document['tags'])}")
        document_container.button(
            "Delete",
            key=f"{document['id']}-delete-button",
            on_click=delete_document,
            args=(document["id"],),
        )
else:
    st.info("No documents created yet. Upload a PDF to get started.")
