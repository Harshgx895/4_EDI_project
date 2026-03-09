"""
Agent 6: Q&A Agent
Conversational RAG agent for free-form document questions.
Responds in the same language as the user's query with source references.
"""

from config import call_llm
from agents import retrieval_agent


def run(query, chunks):
    """
    Answer a user question using retrieved document chunks.

    Input:  query (str), chunks (list of chunk dicts from retrieval_agent)
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

DOCUMENT CONTEXT:
{context_block}

USER QUESTION: {query}

Respond naturally and helpfully:"""

    print(f"  Generating answer...")
    answer = call_llm(prompt, temperature=0.3)

    return {"answer": answer, "sources": sources}


def format_answer(qna_result):
    """Pretty-print a Q&A response."""
    print("\n" + "-" * 60)
    print(qna_result["answer"])
    print("-" * 60)
