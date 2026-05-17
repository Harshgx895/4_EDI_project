"""
LegalLens — FastAPI Backend
Serves the static frontend and provides API endpoints for the RAG pipeline.
"""

import os
import sys
import json
import uuid
import asyncio
from pathlib import Path
from contextlib import asynccontextmanager

# Environment setup (must be before any ML imports)
os.environ["TOKENIZERS_PARALLELISM"] = "false"
os.environ["OMP_NUM_THREADS"] = "1"

import datasets  # noqa: F401  — pre-import to avoid segfault
from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel


# ── Lifespan ─────────────────────────────────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Pre-load models on startup so first query is fast."""
    print("Pre-loading BGE-M3 embedding model...")
    from config import get_embedding_function, get_vector_store
    get_embedding_function()
    get_vector_store()
    print("Models loaded. Server ready.")
    yield

app = FastAPI(title="LegalLens API", lifespan=lifespan)


# ── Request Models ───────────────────────────────────────────────────────
class AnalyzeRequest(BaseModel):
    query: str
    source_filter: list[str] | None = None

class ChatMessage(BaseModel):
    role: str
    content: str

class ChatRequest(BaseModel):
    query: str
    source_filter: list[str] | None = None
    chat_history: list[ChatMessage] | None = None

MAX_UPLOAD_SIZE = 50 * 1024 * 1024  # 50 MB


# ── Helper: Retrieval ────────────────────────────────────────────────────
def _retrieve_chunks(query: str, source_filter: list[str] | None = None):
    from config import get_vector_store, build_source_filter
    vs = get_vector_store()
    if vs is None:
        return {"query": query, "chunks": []}
    chroma_filter = build_source_filter(source_filter)
    results = vs.similarity_search_with_relevance_scores(query, k=5, filter=chroma_filter)
    return {
        "query": query,
        "chunks": [
            {
                "text": doc.page_content,
                "page": doc.metadata.get("page", 0) + 1,
                "source": doc.metadata.get("source", "unknown"),
                "similarity_score": round(score, 4),
            }
            for doc, score in results
        ],
    }


# ── API Endpoints ────────────────────────────────────────────────────────

@app.get("/api/documents")
async def list_documents():
    """List all ingested documents."""
    try:
        db_dir = os.path.join(os.path.dirname(__file__), "chroma_db")
        if not os.path.exists(db_dir):
            return {"documents": []}
        import chromadb
        client = chromadb.PersistentClient(path=db_dir)
        cols = client.list_collections()
        if not cols:
            return {"documents": []}
        data = client.get_collection(cols[0].name).get()
        sources = set()
        for m in data.get("metadatas", []):
            if m and "source" in m:
                sources.add(os.path.basename(m["source"]))
        return {"documents": sorted(sources)}
    except Exception as e:
        return {"documents": [], "error": str(e)}


@app.delete("/api/documents/{filename}")
async def delete_document(filename: str):
    """Delete a document from ChromaDB and disk."""
    try:
        import config
        db_dir = os.path.join(os.path.dirname(__file__), "chroma_db")
        if not os.path.exists(db_dir):
            raise HTTPException(404, "No database found")

        import chromadb
        client = chromadb.PersistentClient(path=db_dir)
        cols = client.list_collections()
        if not cols:
            raise HTTPException(404, "No collections found")

        collection = client.get_collection(cols[0].name)
        data = collection.get()

        # Find all IDs where source basename matches the filename
        ids_to_delete = []
        for i, m in enumerate(data.get("metadatas", [])):
            if m and "source" in m:
                if os.path.basename(m["source"]) == filename:
                    ids_to_delete.append(data["ids"][i])

        if not ids_to_delete:
            raise HTTPException(404, f"Document '{filename}' not found in database")

        # Delete from ChromaDB
        collection.delete(ids=ids_to_delete)

        # Delete from uploads/ folder if it exists
        upload_dir = os.path.join(os.path.dirname(__file__), "uploads")
        upload_path = os.path.join(upload_dir, filename)
        if os.path.exists(upload_path):
            os.remove(upload_path)

        # Also check project root
        root_path = os.path.join(os.path.dirname(__file__), filename)
        if os.path.exists(root_path):
            os.remove(root_path)

        # Reset vector store singleton
        config._vector_store = None

        return {"status": "ok", "deleted": filename, "chunks_removed": len(ids_to_delete)}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(500, f"Delete failed: {str(e)}")


@app.post("/api/upload")
async def upload_document(file: UploadFile = File(...)):
    """Upload and ingest a PDF or DOCX file."""
    if not file.filename:
        raise HTTPException(400, "No file provided")

    ext = Path(file.filename).suffix.lower()
    if ext not in (".pdf", ".docx"):
        raise HTTPException(400, f"Unsupported file type: {ext}")

    # Read file with size check
    content = await file.read()
    if len(content) > MAX_UPLOAD_SIZE:
        raise HTTPException(413, f"File too large ({len(content) // (1024*1024)}MB). Maximum is 50MB.")

    # Sanitize filename: UUID prefix + original basename (no path traversal)
    safe_name = Path(file.filename).name  # strip any directory components
    unique_name = f"{uuid.uuid4().hex[:8]}_{safe_name}"
    upload_dir = os.path.join(os.path.dirname(__file__), "uploads")
    os.makedirs(upload_dir, exist_ok=True)
    file_path = os.path.join(upload_dir, unique_name)

    with open(file_path, "wb") as f:
        f.write(content)

    # Ingest (run in thread to not block event loop)
    try:
        from ingest import load_document, chunk_document, create_vector_db
        import config

        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, lambda: _ingest_sync(file_path))

        # Reset vector store singleton so it picks up new docs
        config._vector_store = None

        return {"status": "ok", "filename": unique_name}
    except Exception as e:
        # Clean up file on failure
        if os.path.exists(file_path):
            os.remove(file_path)
        raise HTTPException(500, f"Ingestion failed: {str(e)}")


def _ingest_sync(file_path: str):
    from ingest import load_document, chunk_document, create_vector_db
    docs = load_document(file_path)
    chunks = chunk_document(docs)
    create_vector_db(chunks)


@app.post("/api/analyze")
async def analyze(req: AnalyzeRequest):
    """Run the full risk analysis pipeline."""
    loop = asyncio.get_event_loop()
    result = await loop.run_in_executor(None, lambda: _analyze_sync(req.query, req.source_filter))
    if result is None:
        return {"report": [], "query": req.query}
    return result


def _analyze_sync(query: str, source_filter: list[str] | None):
    from agents.clause_agent import run as classify
    from agents.risk_agent import run as evaluate
    from agents.explanation_agent import run as explain

    ret = _retrieve_chunks(query, source_filter)
    if not ret.get("chunks"):
        return None
    clauses = classify(ret)
    risks = evaluate(clauses)
    return explain(risks)


@app.post("/api/chat")
async def chat(req: ChatRequest):
    """Run Q&A query with conversation history."""
    history = [m.model_dump() for m in req.chat_history] if req.chat_history else None
    loop = asyncio.get_event_loop()
    result = await loop.run_in_executor(None, lambda: _chat_sync(req.query, req.source_filter, history))
    return result


def _chat_sync(query: str, source_filter: list[str] | None, chat_history: list | None = None):
    from agents.qna_agent import run as answer
    ret = _retrieve_chunks(query, source_filter)
    if not ret.get("chunks"):
        return {"answer": "I couldn't find relevant information in the uploaded documents.", "sources": []}
    return answer(query, ret["chunks"], chat_history=chat_history)


@app.get("/api/eval")
async def get_eval():
    """Return RAGAS evaluation results."""
    eval_path = os.path.join(os.path.dirname(__file__), "eval_results.json")
    if not os.path.exists(eval_path):
        return {"summary": {}, "per_question": []}
    with open(eval_path, "r", encoding="utf-8") as f:
        return json.load(f)


# ── File Serving (for PDF viewer) ────────────────────────────────────────
@app.get("/api/file/{filename}")
async def serve_file(filename: str):
    """Serve an uploaded document for in-browser preview (inline, not download)."""
    safe_name = Path(filename).name  # prevent traversal
    inline_headers = {"Content-Disposition": f"inline; filename=\"{safe_name}\""}

    # Check uploads/ directory
    upload_path = os.path.join(os.path.dirname(__file__), "uploads", safe_name)
    if os.path.exists(upload_path):
        return FileResponse(upload_path, media_type="application/pdf", headers=inline_headers)
    # Check project root (for initially ingested docs)
    root_path = os.path.join(os.path.dirname(__file__), safe_name)
    if os.path.exists(root_path):
        return FileResponse(root_path, media_type="application/pdf", headers=inline_headers)
    raise HTTPException(404, f"File '{safe_name}' not found")


# ── Serve Static Files ───────────────────────────────────────────────────
static_dir = os.path.join(os.path.dirname(__file__), "static")
if os.path.exists(static_dir):
    app.mount("/static", StaticFiles(directory=static_dir), name="static")

@app.get("/")
async def root():
    return FileResponse(os.path.join(static_dir, "index.html"))


# ── Run ──────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("server:app", host="0.0.0.0", port=8000, reload=True)
