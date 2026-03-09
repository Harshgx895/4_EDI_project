"""
Legal Document Reviewer — Main Entry Point
Offers two modes:
  1. Risk Analysis — structured clause-by-clause risk report (Agents 2→3→4→5)
  2. Q&A Chat     — free-form conversational Q&A with documents (Agent 2 + QnA Agent)
"""

import os
import sys

from config import get_embedding_function, DB_DIR
from langchain_chroma import Chroma

from agents import retrieval_agent, clause_agent, risk_agent, explanation_agent, qna_agent
from agents.explanation_agent import format_report
from agents.qna_agent import format_answer


# ──────────────────────────────────────────────
#  Document Selection
# ──────────────────────────────────────────────

def get_ingested_documents():
    """List all unique source documents in the database."""
    if not os.path.exists(DB_DIR):
        return []

    embedding_fn = get_embedding_function()
    db = Chroma(persist_directory=DB_DIR, embedding_function=embedding_fn)
    collection = db.get()

    sources = set()
    for meta in collection.get("metadatas", []):
        if meta and "source" in meta:
            sources.add(meta["source"])

    return sorted(sources)


def select_documents():
    """Interactive prompt to let the user pick one or more documents."""
    sources = get_ingested_documents()

    if not sources:
        print("No documents found in the database. Run ingest.py first.")
        return None

    print("\n  Documents in the database:")
    print("  " + "-" * 40)
    print("   [0] Search ALL documents")
    for i, src in enumerate(sources, 1):
        # Show clean filename (basename only)
        name = os.path.basename(src)
        print(f"   [{i}] {name}")
    print("  " + "-" * 40)
    print("  Tip: You can select multiple documents (e.g. 1,3)")

    choice = input(f"\n  Your choice [0-{len(sources)}]: ").strip()

    if not choice or choice == "0":
        print("  → Searching across ALL documents.\n")
        return "__ALL__"

    selected = []
    for part in choice.split(","):
        part = part.strip()
        try:
            idx = int(part)
            if 1 <= idx <= len(sources):
                selected.append(sources[idx - 1])
            else:
                print(f"  Skipping invalid index: {idx}")
        except ValueError:
            print(f"  Skipping invalid input: '{part}'")

    if not selected:
        print("  No valid selection. Searching all documents.\n")
        return "__ALL__"

    selected = list(dict.fromkeys(selected))
    names = [os.path.basename(s) for s in selected]
    print(f"  → Selected {len(selected)} document(s): {', '.join(names)}\n")
    return selected


# ──────────────────────────────────────────────
#  Mode 1: Risk Analysis Pipeline
# ──────────────────────────────────────────────

def run_risk_analysis(selected_docs):
    """Run the full multi-agent risk analysis pipeline."""
    user_topic = input("What legal topic do you want to analyze? (e.g., 'liability', 'termination'): ")

    # Agent 2 — Retrieval
    retrieval_result = retrieval_agent.run(user_topic, source_filter=selected_docs)
    if not retrieval_result["chunks"]:
        print("\nNo relevant clauses found in the document.")
        return

    # Agent 3 — Clause Identification
    clause_result = clause_agent.run(retrieval_result)

    # Agent 4 — Risk Evaluation
    risk_result = risk_agent.run(clause_result)

    # Agent 5 — Explanation & Report
    report_result = explanation_agent.run(risk_result)

    # Display final report
    format_report(report_result)


# ──────────────────────────────────────────────
#  Mode 2: Q&A Chat Loop
# ──────────────────────────────────────────────

def run_qna_chat(selected_docs):
    """Run a conversational Q&A loop with the documents."""
    print("=" * 60)
    print("  Q&A CHAT MODE")
    print("  Ask any question about your documents in any language.")
    print("  Commands:")
    print("    'analyze' — run full risk analysis on your last topic")
    print("    'exit'    — quit")
    print("=" * 60)

    last_query = None
    last_chunks = None

    while True:
        user_input = input("\n  You: ").strip()

        if not user_input:
            continue

        if user_input.lower() == "exit":
            print("\n  Goodbye!")
            break

        if user_input.lower() == "analyze":
            if last_chunks and last_query:
                print(f"\n  Running full risk analysis on: '{last_query}'...")
                # Build retrieval_result from cached chunks
                retrieval_result = {"query": last_query, "chunks": last_chunks}
                clause_result = clause_agent.run(retrieval_result)
                risk_result = risk_agent.run(clause_result)
                report_result = explanation_agent.run(risk_result)
                format_report(report_result)
            else:
                print("  No previous query to analyze. Ask a question first.")
            continue

        # Retrieve relevant chunks
        retrieval_result = retrieval_agent.run(user_input, source_filter=selected_docs)
        last_query = user_input
        last_chunks = retrieval_result["chunks"]

        # Generate answer via QnA Agent
        qna_result = qna_agent.run(user_input, retrieval_result["chunks"])
        format_answer(qna_result)


# ──────────────────────────────────────────────
#  Main
# ──────────────────────────────────────────────

if __name__ == "__main__":
    print("=" * 60)
    print("  AI LEGAL DOCUMENT REVIEWER")
    print("=" * 60)

    # Step 1: Select documents
    selected_docs = select_documents()
    if selected_docs is None:
        sys.exit(1)

    # Step 2: Choose mode
    print("  Choose a mode:")
    print("   [1] Risk Analysis — analyze legal clauses for risk")
    print("   [2] Q&A Chat     — ask questions about your documents")
    mode = input("\n  Your choice [1/2]: ").strip()

    if mode == "2":
        run_qna_chat(selected_docs)
    else:
        run_risk_analysis(selected_docs)