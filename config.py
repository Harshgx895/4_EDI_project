"""
Shared configuration and utilities for the Legal Document Reviewer.
All agents import from here to avoid duplication.
"""

import os
import sys
import time
from dotenv import load_dotenv
from langchain_chroma import Chroma
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_google_genai import ChatGoogleGenerativeAI

# --- Load Environment ---
load_dotenv()

GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
if not GOOGLE_API_KEY:
    print("Error: GOOGLE_API_KEY not found in .env")
    sys.exit(1)

# --- Constants ---
DB_DIR = "./chroma_db"
EMBEDDING_MODEL = "BAAI/bge-m3"
MODEL_NAME = "gemini-2.5-flash"
MAX_RETRIES = 3
RETRY_DELAY = 5  # seconds, doubles each retry

# --- Singleton Instances ---
_embedding_function = None
_vector_store = None


def get_embedding_function():
    """Returns a shared embedding model instance (loaded once)."""
    global _embedding_function
    if _embedding_function is None:
        print("Loading BGE-M3 embedding model...")
        _embedding_function = HuggingFaceEmbeddings(
            model_name=EMBEDDING_MODEL,
            model_kwargs={"device": "cpu"},
            encode_kwargs={"normalize_embeddings": True},
        )
    return _embedding_function


def get_vector_store():
    """Returns a shared ChromaDB instance."""
    global _vector_store
    if _vector_store is None:
        if not os.path.exists(DB_DIR):
            print(f"Error: Database folder '{DB_DIR}' not found. Run ingest.py first.")
            return None
        _vector_store = Chroma(
            persist_directory=DB_DIR,
            embedding_function=get_embedding_function(),
        )
    return _vector_store

MISTRAL_API_KEY = os.getenv("MISTRAL_API_KEY")
MISTRAL_MODEL = "mistral-small-latest"


def get_llm(temperature=0.1):
    """Returns a configured Gemini LLM instance."""
    return ChatGoogleGenerativeAI(
        model=MODEL_NAME,
        google_api_key=GOOGLE_API_KEY,
        temperature=temperature,
    )


def _call_mistral_fallback(prompt, temperature=0.1):
    """Fallback: call Mistral API when Gemini is rate-limited."""
    if not MISTRAL_API_KEY:
        return "Error: Gemini rate limited and no MISTRAL_API_KEY set for fallback."

    try:
        from langchain_community.chat_models import ChatOpenAI
        mistral_llm = ChatOpenAI(
            model=MISTRAL_MODEL,
            api_key=MISTRAL_API_KEY,
            base_url="https://api.mistral.ai/v1",
            temperature=temperature,
        )
        response = mistral_llm.invoke(prompt)
        return response.content
    except Exception as e:
        return f"Mistral fallback error: {str(e)}"


def call_llm(prompt, temperature=0.1):
    """
    Call the LLM with automatic retry on rate-limit errors.
    Falls back to Mistral if Gemini is exhausted.
    Returns the response text string.
    """
    llm = get_llm(temperature=temperature)

    for attempt in range(1, MAX_RETRIES + 1):
        try:
            response = llm.invoke(prompt)
            return response.content
        except Exception as e:
            error_msg = str(e)
            if "429" in error_msg or "RESOURCE_EXHAUSTED" in error_msg:
                wait_time = RETRY_DELAY * (2 ** (attempt - 1))
                print(f"  Rate limited (attempt {attempt}/{MAX_RETRIES}). Waiting {wait_time}s...")
                time.sleep(wait_time)
            else:
                return f"LLM Error: {error_msg}"

    # Fallback to Mistral
    print("  Gemini exhausted. Falling back to Mistral...")
    return _call_mistral_fallback(prompt, temperature)


def build_source_filter(source_filter):
    """Build a ChromaDB metadata filter dict from a source_filter value."""
    if not source_filter or source_filter == "__ALL__":
        return None

    if isinstance(source_filter, list):
        if len(source_filter) == 1:
            return {"source": source_filter[0]}
        return {"$or": [{"source": s} for s in source_filter]}

    return {"source": source_filter}
