"""
AI Legal Document Reviewer - Streamlit Web Interface
Provides file upload, risk analysis, Q&A chat, and evaluation metrics.
"""

import streamlit as st
import os
import sys
import json
import tempfile
import time

# Memory optimization
os.environ["TOKENIZERS_PARALLELISM"] = "false"
os.environ["OMP_NUM_THREADS"] = "1"

# Pre-import datasets to avoid segfault with sentence_transformers
import datasets  # noqa: F401

from dotenv import load_dotenv
load_dotenv()

# --- Page Config ---
st.set_page_config(
    page_title="AI Legal Document Reviewer",
    page_icon="&#9878;",
    layout="wide",
    initial_sidebar_state="expanded",
)

# --- Custom CSS ---
st.markdown("""
<style>
    /* Global */
    .stApp {
        background: linear-gradient(135deg, #0f0c29 0%, #1a1a3e 50%, #24243e 100%);
    }
    
    /* Header */
    .main-header {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        font-size: 2.5rem;
        font-weight: 800;
        text-align: center;
        margin-bottom: 0.2rem;
    }
    .sub-header {
        text-align: center;
        color: #a0a0c0;
        font-size: 1rem;
        margin-bottom: 2rem;
    }
    
    /* Risk cards */
    .risk-high {
        background: linear-gradient(135deg, #ff416c22, #ff416c11);
        border-left: 4px solid #ff416c;
        padding: 1rem 1.2rem;
        border-radius: 0 8px 8px 0;
        margin-bottom: 1rem;
    }
    .risk-medium {
        background: linear-gradient(135deg, #f7971e22, #f7971e11);
        border-left: 4px solid #f7971e;
        padding: 1rem 1.2rem;
        border-radius: 0 8px 8px 0;
        margin-bottom: 1rem;
    }
    .risk-low {
        background: linear-gradient(135deg, #56ab2f22, #56ab2f11);
        border-left: 4px solid #56ab2f;
        padding: 1rem 1.2rem;
        border-radius: 0 8px 8px 0;
        margin-bottom: 1rem;
    }
    
    .risk-badge {
        display: inline-block;
        padding: 2px 10px;
        border-radius: 12px;
        font-size: 0.75rem;
        font-weight: 700;
        letter-spacing: 0.5px;
    }
    .badge-high { background: #ff416c; color: white; }
    .badge-medium { background: #f7971e; color: white; }
    .badge-low { background: #56ab2f; color: white; }
    
    /* Metric cards */
    .metric-card {
        background: linear-gradient(135deg, #1e1e3f, #2a2a5a);
        border: 1px solid #3a3a6a;
        border-radius: 12px;
        padding: 1.2rem;
        text-align: center;
    }
    .metric-value {
        font-size: 2rem;
        font-weight: 800;
        background: linear-gradient(135deg, #667eea, #764ba2);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
    }
    .metric-label {
        color: #a0a0c0;
        font-size: 0.85rem;
        margin-top: 0.3rem;
    }
    .metric-status {
        font-size: 0.8rem;
        margin-top: 0.3rem;
    }
    
    /* Chat */
    .chat-user {
        background: linear-gradient(135deg, #667eea22, #764ba222);
        border: 1px solid #667eea44;
        padding: 0.8rem 1rem;
        border-radius: 12px 12px 4px 12px;
        margin-bottom: 0.8rem;
    }
    .chat-bot {
        background: linear-gradient(135deg, #1e1e3f, #2a2a5a);
        border: 1px solid #3a3a6a;
        padding: 0.8rem 1rem;
        border-radius: 12px 12px 12px 4px;
        margin-bottom: 0.8rem;
    }
    
    /* Sidebar */
    .sidebar-info {
        background: linear-gradient(135deg, #1e1e3f, #2a2a5a);
        border: 1px solid #3a3a6a;
        border-radius: 8px;
        padding: 1rem;
        margin-bottom: 1rem;
    }
    
    /* Source ref */
    .source-ref {
        color: #667eea;
        font-size: 0.8rem;
        font-style: italic;
    }
</style>
""", unsafe_allow_html=True)


# --- Initialize Session State ---
if "initialized" not in st.session_state:
    st.session_state.initialized = False
    st.session_state.chat_history = []
    st.session_state.documents = []
    st.session_state.selected_docs = []


@st.cache_resource(show_spinner="Loading AI models...")
def load_models():
    """Load embedding model and vector store once (only called when needed)."""
    from config import get_embedding_function, get_vector_store
    ef = get_embedding_function()
    vs = get_vector_store()
    return ef, vs


def get_ingested_documents():
    """Get list of ingested documents from ChromaDB WITHOUT loading embedding model."""
    try:
        db_dir = os.path.join(os.path.dirname(__file__), "chroma_db")
        if not os.path.exists(db_dir):
            return []
        import chromadb
        client = chromadb.PersistentClient(path=db_dir)
        collections = client.list_collections()
        if not collections:
            return []
        col = client.get_collection(collections[0].name)
        data = col.get()
        sources = set()
        for meta in data.get("metadatas", []):
            if meta and "source" in meta:
                sources.add(os.path.basename(meta["source"]))
        return sorted(sources)
    except Exception:
        return []


def ingest_document(file_path):
    """Ingest a PDF into ChromaDB."""
    from ingest import load_document, chunk_document, create_vector_db
    docs = load_document(file_path)
    chunks = chunk_document(docs)
    create_vector_db(chunks)


def run_risk_analysis(query, source_filter=None):
    """Run the full risk analysis pipeline."""
    from agents.retrieval_agent import run as retrieve
    from agents.clause_agent import run as identify_clauses
    from agents.risk_agent import run as evaluate_risk
    from agents.explanation_agent import run as explain_risks

    # Agent 2: Retrieve
    retrieval_result = retrieve(query, source_filter)

    if not retrieval_result.get("chunks"):
        return None

    # Agent 3: Classify clauses
    clause_result = identify_clauses(retrieval_result)

    # Agent 4: Evaluate risk
    risk_result = evaluate_risk(clause_result)

    # Agent 5: Explain
    explanation_result = explain_risks(risk_result)

    return explanation_result


def run_qna(query, source_filter=None):
    """Run Q&A query."""
    from agents.retrieval_agent import run as retrieve
    from agents.qna_agent import run as answer_question

    retrieval_result = retrieve(query, source_filter)

    if not retrieval_result.get("chunks"):
        return {"answer": "No relevant information found in the documents.", "sources": []}

    result = answer_question(query, retrieval_result["chunks"])
    return result


# --- Header ---
st.markdown('<h1 class="main-header">&#9878; AI Legal Document Reviewer</h1>', unsafe_allow_html=True)
st.markdown('<p class="sub-header">Analyze large legal documents in any language with AI-powered risk detection</p>', unsafe_allow_html=True)

# --- Sidebar ---
with st.sidebar:
    st.markdown("### Documents")

    # File uploader
    uploaded_files = st.file_uploader(
        "Upload documents",
        type=["pdf", "docx"],
        accept_multiple_files=True,
        help="Upload PDF or DOCX files for analysis"
    )

    if uploaded_files:
        for uf in uploaded_files:
            # Save to temp and ingest
            temp_dir = os.path.join(os.path.dirname(__file__), "uploads")
            os.makedirs(temp_dir, exist_ok=True)
            file_path = os.path.join(temp_dir, uf.name)

            if not os.path.exists(file_path):
                with open(file_path, "wb") as f:
                    f.write(uf.getbuffer())

                with st.spinner(f"Ingesting {uf.name}..."):
                    try:
                        ingest_document(file_path)
                        st.success(f"Ingested: {uf.name}")
                    except Exception as e:
                        st.error(f"Error: {e}")

    # Show ingested documents
    docs = get_ingested_documents()
    if docs:
        st.markdown('<div class="sidebar-info">', unsafe_allow_html=True)
        st.markdown(f"**{len(docs)} document(s) ingested:**")
        for d in docs:
            st.markdown(f"- {d}")
        st.markdown('</div>', unsafe_allow_html=True)

        # Document filter
        selected = st.multiselect(
            "Filter by documents (leave empty for all)",
            options=docs,
            default=[],
            help="Select specific documents to search, or leave empty to search all"
        )
        st.session_state.selected_docs = selected if selected else None
    else:
        st.info("No documents ingested yet. Upload a PDF to get started.")

    st.markdown("---")
    st.markdown("### About")
    st.markdown("""
    **Multi-agent RAG pipeline:**
    1. Ingestion (BGE-M3)
    2. Retrieval (ChromaDB)
    3. Clause Classification
    4. Risk Evaluation
    5. Explanation Generation
    6. Q&A Conversation
    """)

# --- Main Content ---
if not docs:
    # Welcome screen
    st.markdown("---")
    col1, col2, col3 = st.columns(3)
    with col1:
        st.markdown("""
        ### Upload Documents
        Upload your legal PDFs to get started. The system supports documents in **100+ languages**.
        """)
    with col2:
        st.markdown("""
        ### Analyze Risks
        Get AI-powered risk analysis with clause classification, risk scoring, and actionable suggestions.
        """)
    with col3:
        st.markdown("""
        ### Ask Questions
        Chat with your documents in any language, including Hinglish. Get cited answers with page references.
        """)
else:
    # Tabs
    tab1, tab2, tab3 = st.tabs(["Risk Analysis", "Q&A Chat", "Evaluation Metrics"])

    # --- Tab 1: Risk Analysis ---
    with tab1:
        st.markdown("### Analyze Legal Risks")
        query = st.text_input(
            "Enter a topic to analyze",
            placeholder="e.g., liability, termination, indemnification, non-compete",
            key="risk_query"
        )

        if st.button("Analyze", type="primary", key="analyze_btn"):
            if query:
                with st.spinner("Running analysis pipeline..."):
                    result = run_risk_analysis(query, st.session_state.selected_docs)

                if result and result.get("report"):
                    report = result["report"]

                    # Summary metrics
                    high = sum(1 for r in report if r.get("risk_level", "").lower() == "high")
                    medium = sum(1 for r in report if r.get("risk_level", "").lower() == "medium")
                    low = sum(1 for r in report if r.get("risk_level", "").lower() == "low")

                    col1, col2, col3, col4 = st.columns(4)
                    with col1:
                        st.metric("Total Findings", len(report))
                    with col2:
                        st.metric("High Risk", high)
                    with col3:
                        st.metric("Medium Risk", medium)
                    with col4:
                        st.metric("Low Risk", low)

                    st.markdown("---")

                    # Risk cards
                    for item in report:
                        risk = item.get("risk_level", "Low").lower()
                        css_class = f"risk-{risk}"
                        badge_class = f"badge-{risk}"

                        st.markdown(f"""
                        <div class="{css_class}">
                            <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:0.5rem;">
                                <strong>{item.get('clause_type', 'Unknown')}</strong>
                                <span class="risk-badge {badge_class}">{risk.upper()} RISK</span>
                            </div>
                            <p style="margin:0.3rem 0; font-size:0.9rem;">{item.get('explanation', 'N/A')}</p>
                            <p style="margin:0.3rem 0; font-size:0.85rem;"><strong>Why it matters:</strong> {item.get('why_it_matters', 'N/A')}</p>
                            <p style="margin:0.3rem 0; font-size:0.85rem;"><strong>Suggestion:</strong> {item.get('suggestion', 'N/A')}</p>
                            <p class="source-ref">Source: {item.get('source_ref', 'N/A')}</p>
                        </div>
                        """, unsafe_allow_html=True)

                        # Show flags if any
                        flags = item.get("risk_flags", [])
                        if flags:
                            st.warning(f"Rule-based flags detected: {', '.join(flags)}")
                else:
                    st.warning("No relevant clauses found for this topic. Try a different search term.")
            else:
                st.warning("Please enter a topic to analyze.")

    # --- Tab 2: Q&A Chat ---
    with tab2:
        st.markdown("### Chat with Your Documents")
        st.markdown("*Ask questions in any language, including Hinglish*")

        # Display chat history
        for msg in st.session_state.chat_history:
            if msg["role"] == "user":
                st.markdown(f'<div class="chat-user"><strong>You:</strong> {msg["content"]}</div>', unsafe_allow_html=True)
            else:
                st.markdown(f'<div class="chat-bot"><strong>AI:</strong> {msg["content"]}</div>', unsafe_allow_html=True)
                if msg.get("sources"):
                    sources_str = ", ".join([f"Page {s.get('page', '?')} ({os.path.basename(s.get('source', '?'))})" for s in msg["sources"]])
                    st.markdown(f'<p class="source-ref">Sources: {sources_str}</p>', unsafe_allow_html=True)

        # Chat input
        user_query = st.chat_input("Ask a question about your documents...")

        if user_query:
            st.session_state.chat_history.append({"role": "user", "content": user_query})

            with st.spinner("Searching documents..."):
                result = run_qna(user_query, st.session_state.selected_docs)

            answer = result.get("answer", "Sorry, I couldn't find an answer.")
            sources = result.get("sources", [])

            st.session_state.chat_history.append({
                "role": "assistant",
                "content": answer,
                "sources": sources,
            })
            st.rerun()

        if st.button("Clear Chat", key="clear_chat"):
            st.session_state.chat_history = []
            st.rerun()

    # --- Tab 3: Evaluation Metrics ---
    with tab3:
        st.markdown("### RAG Evaluation Results")
        st.markdown("*Evaluated using RAGAS framework with 15 test questions*")

        eval_path = os.path.join(os.path.dirname(__file__), "eval_results.json")
        if os.path.exists(eval_path):
            with open(eval_path, "r", encoding="utf-8") as f:
                eval_data = json.load(f)

            summary = eval_data.get("summary", {})

            # Metric cards
            col1, col2, col3, col4 = st.columns(4)

            metrics_display = [
                ("Faithfulness", summary.get("faithfulness", 0), 0.85),
                ("Answer Relevancy", summary.get("answer_relevancy", 0), 0.80),
                ("Context Precision", summary.get("context_precision", 0), 0.75),
                ("Context Recall", summary.get("context_recall", 0), 0.75),
            ]

            for col, (name, score, target) in zip([col1, col2, col3, col4], metrics_display):
                with col:
                    if score and score > 0:
                        status = "PASS" if score >= target else "BELOW"
                        status_color = "#56ab2f" if score >= target else "#ff416c"
                        st.markdown(f"""
                        <div class="metric-card">
                            <div class="metric-value">{score:.1%}</div>
                            <div class="metric-label">{name}</div>
                            <div class="metric-status" style="color:{status_color};">
                                Target: {target:.0%} | {status}
                            </div>
                        </div>
                        """, unsafe_allow_html=True)
                    else:
                        st.markdown(f"""
                        <div class="metric-card">
                            <div class="metric-value">N/A</div>
                            <div class="metric-label">{name}</div>
                            <div class="metric-status">Not evaluated</div>
                        </div>
                        """, unsafe_allow_html=True)

            st.markdown("---")

            # Per-question details
            per_q = eval_data.get("per_question", [])
            if per_q:
                st.markdown("### Per-Question Breakdown")
                for i, q in enumerate(per_q):
                    with st.expander(f"Q{i+1}: {q.get('user_input', 'N/A')[:80]}..."):
                        st.markdown(f"**Question:** {q.get('user_input', 'N/A')}")
                        st.markdown(f"**Answer:** {q.get('response', 'N/A')[:300]}...")
                        st.markdown(f"**Ground Truth:** {q.get('reference', 'N/A')}")

                        fcol1, fcol2, fcol3, fcol4 = st.columns(4)
                        with fcol1:
                            f_val = q.get("faithfulness", "N/A")
                            st.metric("Faithfulness", f"{f_val:.2f}" if isinstance(f_val, (int, float)) else "N/A")
                        with fcol2:
                            a_val = q.get("answer_relevancy", "N/A")
                            st.metric("Relevancy", f"{a_val:.2f}" if isinstance(a_val, (int, float)) else "N/A")
                        with fcol3:
                            cp_val = q.get("context_precision", "N/A")
                            st.metric("Ctx Precision", f"{cp_val:.2f}" if isinstance(cp_val, (int, float)) else "N/A")
                        with fcol4:
                            cr_val = q.get("context_recall", "N/A")
                            st.metric("Ctx Recall", f"{cr_val:.2f}" if isinstance(cr_val, (int, float)) else "N/A")
        else:
            st.info("No evaluation results found. Run `python evaluate.py` then `python evaluate_ragas.py` to generate metrics.")
