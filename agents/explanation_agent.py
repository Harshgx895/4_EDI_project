"""
Agent 5: Explanation Agent
Generates plain-language explanations, source references, and suggested improvements.
"""

from config import call_llm


def run(risk_output):
    """
    Generate human-readable explanations for each risk finding.

    Input:  dict from risk_agent { query, risks }
    Output: dict { query, report: list of report entries }
    """
    print("\n===== AGENT 5: EXPLANATION =====")

    query = risk_output["query"]
    risks = risk_output["risks"]

    if not risks:
        print("  No risks to explain.")
        return {"query": query, "report": []}

    # Build a prompt with all risk findings for the LLM to explain
    findings_block = ""
    for i, risk in enumerate(risks):
        flag_labels = [f["label"] for f in risk["risk_flags"]]
        flags_str = ", ".join(flag_labels) if flag_labels else "None"

        findings_block += f"""
--- FINDING {i+1} ---
Clause Type: {risk['clause_type']}
Risk Level: {risk['risk_level']}
Rule-Based Flags: {flags_str}
Source: Page {risk['page']}, {risk['source']}
Original Text: "{risk['text'][:500]}"
LLM Reasoning: {risk['llm_reasoning']}
"""

    prompt = f"""You are a Legal Advisor writing a clear risk report for a non-lawyer.

The user asked about: "{query}"

Below are the analyzed findings from a legal document. For each finding, write:
1. A plain-English explanation of what the clause means (2-3 sentences)
2. Why it matters — what could go wrong for the person signing this
3. A practical suggestion for how to negotiate or improve the clause

FINDINGS:
{findings_block}

IMPORTANT: Respond with ONLY a valid JSON array. Each element must have:
- "finding_index": the finding number (1-based)
- "explanation": plain-English explanation
- "why_it_matters": what could go wrong
- "suggestion": how to improve or negotiate

Respond with ONLY the JSON array, no other text."""

    print(f"  Generating explanations for {len(risks)} findings...")
    raw_response = call_llm(prompt, temperature=0.2)

    # Parse the explanations
    explanations = _parse_explanations(raw_response, len(risks))

    # Build the final report
    report = []
    for i, risk in enumerate(risks):
        explanation_data = explanations.get(i + 1, {
            "explanation": risk["llm_reasoning"],
            "why_it_matters": "Could not generate detailed explanation.",
            "suggestion": "Consult a legal professional for guidance.",
        })

        flag_labels = [f["label"] for f in risk["risk_flags"]]

        report_entry = {
            "clause_type": risk["clause_type"],
            "risk_level": risk["risk_level"],
            "source_ref": f"Page {risk['page']}, {risk['source']}",
            "original_excerpt": risk["text"][:200] + ("..." if len(risk["text"]) > 200 else ""),
            "risk_flags": flag_labels,
            "explanation": explanation_data.get("explanation", ""),
            "why_it_matters": explanation_data.get("why_it_matters", ""),
            "suggestion": explanation_data.get("suggestion", ""),
        }
        report.append(report_entry)

    print(f"  Report generated with {len(report)} entries.")
    return {"query": query, "report": report}


def _parse_explanations(raw_response, num_findings):
    """Parse LLM JSON response into {finding_index: {explanation, why_it_matters, suggestion}}."""
    import json

    result = {}
    text = raw_response.strip()

    if text.startswith("```"):
        lines = text.split("\n")
        text = "\n".join(lines[1:-1]) if lines[-1].strip() == "```" else "\n".join(lines[1:])
        text = text.strip()

    try:
        parsed = json.loads(text)
        if isinstance(parsed, list):
            for item in parsed:
                idx = item.get("finding_index")
                if idx is not None:
                    result[int(idx)] = {
                        "explanation": item.get("explanation", ""),
                        "why_it_matters": item.get("why_it_matters", ""),
                        "suggestion": item.get("suggestion", ""),
                    }
    except (json.JSONDecodeError, TypeError):
        print("  Warning: Could not parse explanation response as JSON.")

    return result


def format_report(report_output):
    """Pretty-print the final report to the console."""
    query = report_output["query"]
    report = report_output["report"]

    print("\n" + "=" * 60)
    print(f"  LEGAL RISK ANALYSIS REPORT")
    print(f"  Query: \"{query}\"")
    print("=" * 60)

    if not report:
        print("\n  No findings to report.\n")
        return

    for i, entry in enumerate(report):
        # Risk level indicator
        level = entry["risk_level"]
        if level == "High":
            indicator = "[!!!]"
        elif level == "Medium":
            indicator = "[!!] "
        else:
            indicator = "[!]  "

        print(f"\n{indicator} Finding {i+1}: {entry['clause_type']}")
        print(f"  Risk Level : {level}")
        print(f"  Source     : {entry['source_ref']}")

        if entry["risk_flags"]:
            print(f"  Flags      : {', '.join(entry['risk_flags'])}")

        print(f"\n  Excerpt:")
        print(f"    \"{entry['original_excerpt']}\"")

        print(f"\n  Explanation:")
        print(f"    {entry['explanation']}")

        print(f"\n  Why It Matters:")
        print(f"    {entry['why_it_matters']}")

        print(f"\n  Suggestion:")
        print(f"    {entry['suggestion']}")

        print("-" * 60)

    print("\n  DISCLAIMER: This analysis is for informational purposes only")
    print("  and should not be considered legal advice.")
    print("=" * 60)
