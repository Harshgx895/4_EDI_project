"""
Agent 3: Clause Identification Agent
Classifies each retrieved chunk by its legal clause type using the LLM.
"""

import json
from config import call_llm

CLAUSE_TYPES = [
    "Termination",
    "Liability",
    "Indemnification",
    "Payment Terms",
    "Confidentiality",
    "Intellectual Property",
    "Jurisdiction / Governing Law",
    "Force Majeure",
    "Non-Compete / Non-Solicitation",
    "Warranty / Disclaimer",
    "Other",
]


def run(retrieval_output):
    """
    Classify each retrieved chunk by clause type.

    Input:  dict from retrieval_agent { query, chunks }
    Output: dict { query, clauses: [{ text, page, source, similarity_score, clause_type }] }
    """
    print("\n===== AGENT 3: CLAUSE IDENTIFICATION =====")

    query = retrieval_output["query"]
    chunks = retrieval_output["chunks"]

    if not chunks:
        print("  No chunks to classify.")
        return {"query": query, "clauses": []}

    # Build a single prompt that classifies all chunks at once (more efficient)
    chunks_text = ""
    for i, chunk in enumerate(chunks):
        chunks_text += f"\n--- CHUNK {i+1} (Page {chunk['page']}, Source: {chunk['source']}) ---\n"
        chunks_text += chunk["text"]
        chunks_text += "\n"

    prompt = f"""You are a Legal Clause Classifier.

Given the following text chunks from a legal document, classify each chunk into one of these clause types:
{', '.join(CLAUSE_TYPES)}

CHUNKS:
{chunks_text}

IMPORTANT: Respond with ONLY a valid JSON array. Each element must have:
- "chunk_index": the chunk number (1-based)
- "clause_type": one of the types listed above

Example response:
[{{"chunk_index": 1, "clause_type": "Termination"}}, {{"chunk_index": 2, "clause_type": "Liability"}}]

Respond with ONLY the JSON array, no other text."""

    print(f"  Classifying {len(chunks)} chunks...")
    raw_response = call_llm(prompt, temperature=0.0)

    # Parse LLM response
    classifications = _parse_classifications(raw_response, len(chunks))

    # Merge classification into chunk data
    clauses = []
    for i, chunk in enumerate(chunks):
        clause_type = classifications.get(i + 1, "Other")
        clauses.append({
            **chunk,
            "clause_type": clause_type,
        })
        print(f"  Chunk {i+1} (Page {chunk['page']}): {clause_type}")

    return {"query": query, "clauses": clauses}


def _parse_classifications(raw_response, num_chunks):
    """Parse the LLM JSON response into a dict of {chunk_index: clause_type}."""
    classifications = {}

    # Try to extract JSON from the response
    text = raw_response.strip()

    # Remove markdown code fences if present
    if text.startswith("```"):
        lines = text.split("\n")
        text = "\n".join(lines[1:-1]) if lines[-1].strip() == "```" else "\n".join(lines[1:])
        text = text.strip()

    try:
        parsed = json.loads(text)
        if isinstance(parsed, list):
            for item in parsed:
                idx = item.get("chunk_index")
                ctype = item.get("clause_type", "Other")
                if idx is not None:
                    classifications[int(idx)] = ctype
    except (json.JSONDecodeError, TypeError):
        print(f"  Warning: Could not parse LLM response as JSON. Defaulting to 'Other'.")

    return classifications
