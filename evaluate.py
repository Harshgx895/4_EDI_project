"""
RAG Evaluation - Step 1: Generate pipeline outputs
Runs test questions through the RAG pipeline and saves results.
Run this FIRST, then run evaluate_ragas.py to compute metrics.

Usage: python evaluate.py
"""

import os
import sys
import json
import time

# Memory optimization
os.environ["TOKENIZERS_PARALLELISM"] = "false"
os.environ["OMP_NUM_THREADS"] = "1"

# Pre-import datasets to avoid conflict with sentence_transformers
# (ragas installs datasets + pyarrow which can crash if imported after ST)
import datasets  # noqa: F401

from dotenv import load_dotenv
load_dotenv()


def generate_outputs():
    """Run test questions through the RAG pipeline and save outputs."""

    print("=" * 60)
    print("  STEP 1: Generate RAG Pipeline Outputs")
    print("=" * 60)

    # Load test dataset
    script_dir = os.path.dirname(os.path.abspath(__file__))
    dataset_path = os.path.join(script_dir, "eval_dataset.json")
    with open(dataset_path, "r", encoding="utf-8") as f:
        test_data = json.load(f)

    print(f"\n  Loaded {len(test_data)} test questions")
    print("  Loading embedding model + vector store...\n")

    from config import get_embedding_function, DB_DIR, call_llm
    from langchain_chroma import Chroma

    embedding_fn = get_embedding_function()
    vs = Chroma(persist_directory=DB_DIR, embedding_function=embedding_fn)

    print("  Running pipeline...\n")

    eval_samples = []
    for i, item in enumerate(test_data):
        question = item["question"]
        ground_truth = item["ground_truth"]

        print(f"  [{i+1}/{len(test_data)}] {question[:60]}...")

        # Retrieve chunks
        results_with_scores = vs.similarity_search_with_relevance_scores(question, k=5)

        contexts = []
        for doc, score in results_with_scores:
            contexts.append(doc.page_content)

        # Generate answer
        context_block = "\n\n".join([f"[Chunk {j+1}]: {ctx}" for j, ctx in enumerate(contexts)])
        prompt = f"""You are a helpful legal document assistant. Answer the question based ONLY on the provided context.
If the context doesn't contain enough information, say so.

CONTEXT:
{context_block}

QUESTION: {question}

Answer concisely and accurately:"""

        answer = call_llm(prompt, temperature=0.1)
        time.sleep(1)

        eval_samples.append({
            "user_input": question,
            "response": answer,
            "retrieved_contexts": contexts,
            "reference": ground_truth,
        })

        print(f"    OK: {answer[:70]}...")

    # Save results
    output_path = os.path.join(script_dir, "eval_intermediate.json")
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(eval_samples, f, indent=2, ensure_ascii=False)

    print(f"\n  Saved {len(eval_samples)} results to eval_intermediate.json")
    print("  Next: python evaluate_ragas.py")
    print("=" * 60)


if __name__ == "__main__":
    try:
        generate_outputs()
    except Exception as e:
        import traceback
        print(f"\nERROR: {e}")
        traceback.print_exc()
        sys.exit(1)
