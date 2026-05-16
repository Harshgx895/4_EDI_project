"""
RAG Evaluation - Step 2: Compute RAGAS metrics
Reads pipeline outputs from eval_intermediate.json and runs RAGAS evaluation.
Run evaluate.py FIRST to generate the intermediate results.
"""

import os
import sys
import json
import warnings
from dotenv import load_dotenv

load_dotenv()
warnings.filterwarnings("ignore", category=DeprecationWarning)


def run_ragas():
    """Compute RAGAS metrics from pre-generated pipeline outputs."""

    print("=" * 60)
    print("  STEP 2: RAGAS Evaluation")
    print("=" * 60)

    # Load intermediate results
    script_dir = os.path.dirname(os.path.abspath(__file__))
    intermediate_path = os.path.join(script_dir, "eval_intermediate.json")
    if not os.path.exists(intermediate_path):
        print("  ERROR: eval_intermediate.json not found.")
        print("  Run 'python evaluate.py' first to generate pipeline outputs.")
        sys.exit(1)

    with open(intermediate_path, "r", encoding="utf-8") as f:
        eval_samples = json.load(f)

    print(f"\n  Loaded {len(eval_samples)} pre-computed results")

    # Setup RAGAS with Gemini
    from ragas import evaluate, EvaluationDataset
    from ragas.metrics import (
        faithfulness,
        answer_relevancy,
        context_precision,
        context_recall,
    )
    from ragas.llms import LangchainLLMWrapper
    from ragas.embeddings import LangchainEmbeddingsWrapper
    from langchain_community.chat_models import ChatOpenAI
    from langchain_community.embeddings import HuggingFaceInferenceAPIEmbeddings

    mistral_key = os.getenv("MISTRAL_API_KEY")
    google_key = os.getenv("GOOGLE_API_KEY")

    if not mistral_key:
        print("  ERROR: MISTRAL_API_KEY not set in .env")
        sys.exit(1)

    # Use Mistral as the evaluator LLM (avoids Gemini rate limits)
    print("  Setting up Mistral evaluator LLM...")
    mistral_llm = ChatOpenAI(
        model="mistral-small-latest",
        api_key=mistral_key,
        base_url="https://api.mistral.ai/v1",
        temperature=0.1,
    )
    evaluator_llm = LangchainLLMWrapper(mistral_llm)

    # Use Mistral embeddings for answer relevancy
    print("  Setting up Mistral embeddings...")
    from langchain_mistralai import MistralAIEmbeddings
    from ragas.embeddings import LangchainEmbeddingsWrapper
    lc_embeddings = MistralAIEmbeddings(
        model="mistral-embed",
        api_key=mistral_key,
    )
    evaluator_embeddings = LangchainEmbeddingsWrapper(lc_embeddings)

    # Create RAGAS dataset
    eval_dataset = EvaluationDataset.from_list(eval_samples)

    # Define metrics
    metrics = [faithfulness, answer_relevancy, context_precision, context_recall]

    print("  Running RAGAS evaluation (this may take a few minutes)...\n")

    # Run evaluation
    results = evaluate(
        dataset=eval_dataset,
        metrics=metrics,
        llm=evaluator_llm,
        embeddings=evaluator_embeddings,
    )

    # Display results
    print("\n" + "=" * 60)
    print("  EVALUATION RESULTS")
    print("=" * 60)

    # Extract scores from results DataFrame
    try:
        df = results.to_pandas()
        metric_columns = [c for c in df.columns if c not in ["user_input", "response", "retrieved_contexts", "reference"]]
        scores = {}
        for col in metric_columns:
            vals = df[col].dropna()
            if len(vals) > 0:
                scores[col] = vals.mean()
    except Exception:
        scores = {}

    print(f"\n  {'Metric':<30} {'Score':<10} {'Target':<10} {'Status'}")
    print("  " + "-" * 65)

    metric_targets = {
        "faithfulness": 0.85,
        "answer_relevancy": 0.80,
        "context_precision": 0.75,
        "context_recall": 0.75,
    }

    for metric_name, target in metric_targets.items():
        score = scores.get(metric_name, None)

        if score is not None and isinstance(score, (int, float)):
            status = "PASS" if score >= target else "BELOW TARGET"
            display_name = metric_name.replace("_", " ").title()
            print(f"  {display_name:<30} {score:<10.4f} {target:<10.2f} {status}")
        else:
            display_name = metric_name.replace("_", " ").title()
            print(f"  {display_name:<30} {'N/A':<10} {target:<10.2f} {'?'}")

    # Save detailed results
    results_path = os.path.join(script_dir, "eval_results.json")
    try:
        detailed = df.to_dict(orient="records")
        with open(results_path, "w", encoding="utf-8") as f:
            json.dump({
                "summary": {k: float(v) for k, v in scores.items()},
                "per_question": detailed,
            }, f, indent=2, default=str)
        print(f"\n  Detailed results saved to: eval_results.json")
    except Exception as e:
        print(f"\n  Could not save detailed results: {e}")

    print("\n" + "=" * 60)
    print("  EVALUATION COMPLETE")
    print("=" * 60)

    return results


if __name__ == "__main__":
    try:
        run_ragas()
    except Exception as e:
        import traceback
        print(f"\nERROR: {e}")
        traceback.print_exc()
