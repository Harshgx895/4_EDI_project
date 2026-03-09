"""
Agent 2: Retrieval Agent
Retrieves relevant document chunks from ChromaDB with metadata and similarity scores.
"""

from config import get_vector_store, build_source_filter


def run(query, source_filter=None):
    """
    Retrieve relevant chunks for the given query.

    Input:  query (str), source_filter (str|list|None)
    Output: dict with keys: query, chunks (list of dicts)
    """
    print("\n===== AGENT 2: RETRIEVAL =====")
    print(f"  Query: '{query}'")

    vector_store = get_vector_store()
    if vector_store is None:
        return {"query": query, "chunks": []}

    # Build filter
    chroma_filter = build_source_filter(source_filter)
    if chroma_filter:
        filter_desc = source_filter if isinstance(source_filter, str) else ", ".join(source_filter)
        print(f"  Filtering to: {filter_desc}")
    else:
        print("  Searching across ALL documents")

    # Retrieve with similarity scores (lower distance = more similar)
    results_with_scores = vector_store.similarity_search_with_relevance_scores(
        query, k=5, filter=chroma_filter
    )

    chunks = []
    for doc, score in results_with_scores:
        chunks.append({
            "text": doc.page_content,
            "page": doc.metadata.get("page", 0) + 1,  # 0-indexed to 1-indexed
            "source": doc.metadata.get("source", "unknown"),
            "similarity_score": round(score, 4),
        })

    print(f"  Retrieved {len(chunks)} chunks (scores: {[c['similarity_score'] for c in chunks]})")

    return {"query": query, "chunks": chunks}
