"""
Agent 4: Risk Evaluation Agent
Evaluates risk level for each classified clause using LLM + rule-based heuristics.
"""

import json
import re
from config import call_llm

# --- Rule-Based Risk Flags ---
RISK_RULES = [
    {
        "flag": "unlimited_liability",
        "label": "Unlimited Liability",
        "patterns": [
            r"unlimited\s+liabilit",
            r"no\s+(?:cap|limit|ceiling)\s+(?:on|to)\s+(?:liability|damages)",
            r"without\s+(?:any\s+)?limit(?:ation)?",
        ],
    },
    {
        "flag": "one_sided_indemnity",
        "label": "One-Sided Indemnification",
        "patterns": [
            r"shall\s+indemnify.*(?:but|however).*(?:not|no)\s+(?:obligation|duty).*indemnif",
            r"(?:sole|entire)\s+(?:expense|cost|risk)\s+of\s+(?:the\s+)?(?:licensee|contractor|vendor|party)",
        ],
    },
    {
        "flag": "auto_renewal",
        "label": "Auto-Renewal Without Notice",
        "patterns": [
            r"(?:auto(?:matic(?:ally)?)?|shall)\s+renew",
            r"renew(?:ed|al)\s+(?:for|by)\s+(?:additional|successive|further)",
        ],
    },
    {
        "flag": "short_notice",
        "label": "Short Termination Notice Period",
        "patterns": [
            r"(\d+)\s*(?:day|business\s+day)(?:s)?(?:\s*(?:prior\s+)?(?:written\s+)?notice)",
        ],
    },
    {
        "flag": "broad_non_compete",
        "label": "Broad Non-Compete Clause",
        "patterns": [
            r"(?:shall\s+not|agree\s+not\s+to)\s+(?:compete|engage|participate)",
            r"non[- ]?compete",
        ],
    },
]


def _apply_rule_checks(text):
    """Run rule-based pattern checks on clause text. Returns list of flag dicts."""
    flags = []
    text_lower = text.lower()

    for rule in RISK_RULES:
        for pattern in rule["patterns"]:
            match = re.search(pattern, text_lower)
            if match:
                # Special handling for short notice — check if days < 30
                if rule["flag"] == "short_notice":
                    try:
                        days = int(match.group(1))
                        if days < 30:
                            flags.append({
                                "flag": rule["flag"],
                                "label": f"{rule['label']} ({days} days)",
                            })
                    except (IndexError, ValueError):
                        pass
                else:
                    flags.append({
                        "flag": rule["flag"],
                        "label": rule["label"],
                    })
                break  # one match per rule is enough

    return flags


def run(clause_output):
    """
    Evaluate risk for each classified clause.

    Input:  dict from clause_agent { query, clauses }
    Output: dict { query, risks: [{ text, page, source, clause_type, risk_level, risk_flags, llm_reasoning }] }
    """
    print("\n===== AGENT 4: RISK EVALUATION =====")

    query = clause_output["query"]
    clauses = clause_output["clauses"]

    if not clauses:
        print("  No clauses to evaluate.")
        return {"query": query, "risks": []}

    # Build prompt for batch risk evaluation
    clause_text_block = ""
    for i, clause in enumerate(clauses):
        clause_text_block += f"\n--- CLAUSE {i+1} (Type: {clause['clause_type']}, Page {clause['page']}) ---\n"
        clause_text_block += clause["text"]
        clause_text_block += "\n"

    prompt = f"""You are a Senior Legal Risk Assessor.

Evaluate the risk of each clause below for the party who is SIGNING/ACCEPTING this document.

CLAUSES:
{clause_text_block}

For each clause, assess:
1. Risk Level: "Low", "Medium", or "High"
2. Brief reasoning (1-2 sentences)

IMPORTANT: Respond with ONLY a valid JSON array. Each element must have:
- "clause_index": the clause number (1-based)
- "risk_level": "Low", "Medium", or "High"
- "reasoning": brief explanation

Example:
[{{"clause_index": 1, "risk_level": "Medium", "reasoning": "Allows termination with only 7 days notice."}}]

Respond with ONLY the JSON array, no other text."""

    print(f"  Evaluating {len(clauses)} clauses...")
    raw_response = call_llm(prompt, temperature=0.0)

    # Parse LLM risk assessments
    llm_risks = _parse_risk_response(raw_response, len(clauses))

    # Combine LLM evaluation with rule-based flags
    risks = []
    for i, clause in enumerate(clauses):
        llm_data = llm_risks.get(i + 1, {"risk_level": "Unknown", "reasoning": "Could not evaluate."})
        rule_flags = _apply_rule_checks(clause["text"])

        # Elevate risk level if critical rule flags are found
        risk_level = llm_data["risk_level"]
        if any(f["flag"] in ("unlimited_liability", "one_sided_indemnity") for f in rule_flags):
            if risk_level == "Low":
                risk_level = "Medium"
            elif risk_level == "Medium":
                risk_level = "High"

        risk_entry = {
            "text": clause["text"],
            "page": clause["page"],
            "source": clause["source"],
            "similarity_score": clause.get("similarity_score", 0),
            "clause_type": clause["clause_type"],
            "risk_level": risk_level,
            "risk_flags": rule_flags,
            "llm_reasoning": llm_data["reasoning"],
        }
        risks.append(risk_entry)

        flag_labels = [f["label"] for f in rule_flags]
        flag_str = f" | Flags: {', '.join(flag_labels)}" if flag_labels else ""
        print(f"  Clause {i+1} ({clause['clause_type']}): {risk_level}{flag_str}")

    return {"query": query, "risks": risks}


def _parse_risk_response(raw_response, num_clauses):
    """Parse LLM JSON response into {clause_index: {risk_level, reasoning}}."""
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
                idx = item.get("clause_index")
                if idx is not None:
                    result[int(idx)] = {
                        "risk_level": item.get("risk_level", "Unknown"),
                        "reasoning": item.get("reasoning", ""),
                    }
    except (json.JSONDecodeError, TypeError):
        print("  Warning: Could not parse risk response as JSON.")

    return result
