"""
Agent 6: Q&A Agent
Conversational RAG agent for free-form document questions.
Responds in the same language as the user's query with source references.
"""

from config import call_llm
from agents import retrieval_agent


def run(query, chunks, chat_history=None):
    """
    Answer a user question using retrieved document chunks.

    Input:  query (str), chunks (list of chunk dicts), chat_history (optional list of {role, content})
    Output: dict { answer, sources: [{ page, source }] }
    """
    print("\n===== AGENT: Q&A =====")

    if not chunks:
        return {
            "answer": "I couldn't find any relevant information in the documents for your question.",
            "sources": [],
        }

    # Build context block from chunks
    context_block = ""
    sources = []
    for i, chunk in enumerate(chunks):
        context_block += f"\n--- Source {i+1}: Page {chunk['page']}, {chunk['source']} ---\n"
        context_block += chunk["text"]
        context_block += "\n"
        sources.append({"page": chunk["page"], "source": chunk["source"]})

    # Build conversation history block (last 6 turns max)
    history_block = ""
    if chat_history and len(chat_history) > 0:
        recent = chat_history[-6:]  # last 6 messages for context
        history_block = "\nCONVERSATION HISTORY (use this to understand context and references like 'this', 'that', etc.):\n"
        for msg in recent:
            role = "User" if msg.get("role") == "user" else "Assistant"
            content = msg.get("content", "")[:300]  # truncate to save tokens
            history_block += f"{role}: {content}\n"
        history_block += "\n"

    prompt = f"""You are a helpful legal document assistant. A user has uploaded legal documents and is asking questions about them.

IMPORTANT RULES:
1. Answer ONLY based on the provided document context below. Do NOT make up information.
2. Detect the language of the user's question and RESPOND IN THE SAME LANGUAGE.
   - If the user asks in Hindi, respond in Hindi.
   - If the user asks in English, respond in English.
   - If the user asks in Spanish, respond in Spanish.
3. Explain legal concepts in simple, easy-to-understand language.
4. At the end of your answer, cite which source(s) you used (e.g., "Source: Page 14, contract.pdf").
5. If the context doesn't contain enough information to answer, say so honestly.
6. If there is conversation history, use it to understand what the user is referring to.

DOCUMENT CONTEXT:
{context_block}
{history_block}USER QUESTION: {query}

Respond naturally and helpfully:"""

    print(f"  Generating answer...")
    answer = call_llm(prompt, temperature=0.3)

    return {"answer": answer, "sources": sources}


def format_answer(qna_result):
    """Pretty-print a Q&A response."""
    print("\n" + "-" * 60)
    print(qna_result["answer"])
    print("-" * 60)
