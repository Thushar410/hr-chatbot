"""
RAG engine for the HR & Onboarding Assistant.

Responsibilities:
1. Load HR documents (PDF or TXT) from the `data/` folder.
2. Split them into overlapping chunks.
3. Embed chunks locally (free, no API key needed for this step) and store
   them in a persistent Chroma vector database.
4. Retrieve the most relevant chunks for a given user question.

This is intentionally provider-agnostic on the embeddings side (local model)
so a client demo doesn't rack up embedding-API costs, while the *chat*
model (OpenAI) is what actually reasons over the retrieved text.
"""

import os
from pathlib import Path

from langchain_community.document_loaders import PyPDFLoader, TextLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_community.vectorstores import Chroma

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
PERSIST_DIR = Path(__file__).resolve().parent.parent / "chroma_db"

EMBEDDING_MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"
CHUNK_SIZE = 800
CHUNK_OVERLAP = 120
TOP_K = 4  # how many chunks to retrieve per question


def _load_documents():
    """Load every .pdf and .txt file in the data/ directory."""
    docs = []
    for path in DATA_DIR.glob("**/*"):
        if path.suffix.lower() == ".pdf":
            docs.extend(PyPDFLoader(str(path)).load())
        elif path.suffix.lower() == ".txt":
            docs.extend(TextLoader(str(path), encoding="utf-8").load())
    return docs


def _get_embeddings():
    return HuggingFaceEmbeddings(model_name=EMBEDDING_MODEL_NAME)


def build_or_load_vectorstore():
    """
    Build the Chroma vector store from scratch if it doesn't exist yet,
    otherwise load the existing persisted one. Call this once at app startup
    (it's cached in app.py via st.cache_resource).
    """
    embeddings = _get_embeddings()

    if PERSIST_DIR.exists() and any(PERSIST_DIR.iterdir()):
        return Chroma(persist_directory=str(PERSIST_DIR), embedding_function=embeddings)

    raw_docs = _load_documents()
    if not raw_docs:
        raise FileNotFoundError(
            f"No .pdf or .txt files found in {DATA_DIR}. "
            "Add at least one HR document before running the app."
        )

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=CHUNK_SIZE,
        chunk_overlap=CHUNK_OVERLAP,
    )
    chunks = splitter.split_documents(raw_docs)

    vectorstore = Chroma.from_documents(
        documents=chunks,
        embedding=embeddings,
        persist_directory=str(PERSIST_DIR),
    )
    vectorstore.persist()
    return vectorstore


def retrieve_context(vectorstore, question: str, k: int = TOP_K) -> str:
    """
    Return the top-k most relevant chunks for `question`, formatted as a
    single string ready to inject into the LLM prompt, with each chunk
    labeled by its source file so the assistant can cite it.
    """
    results = vectorstore.similarity_search(question, k=k)
    if not results:
        return ""

    formatted = []
    for i, doc in enumerate(results, start=1):
        source = os.path.basename(doc.metadata.get("source", "unknown document"))
        formatted.append(f"[Chunk {i} — source: {source}]\n{doc.page_content}")
    return "\n\n".join(formatted)


def rebuild_index():
    """
    Force a full rebuild of the vector store — call this after swapping in
    a new client's HR documents in data/.
    """
    import shutil

    if PERSIST_DIR.exists():
        shutil.rmtree(PERSIST_DIR)
    return build_or_load_vectorstore()
