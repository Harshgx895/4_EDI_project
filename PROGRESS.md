# Project Progress & Walkthrough

## Overview

This document tracks the development progress of the **AI Agent–Based Legal Document Reviewer** — a multi-agent RAG system for analyzing large legal documents in any language.

---

## Current Status: All Agents Implemented & Tested ✅

All 6 agents are implemented and **verified working end-to-end**. Both modes — Risk Analysis and Q&A Chat — have been tested successfully against the sample deed PDF.

---

## What Has Been Built

### Agent 1: Ingestion Agent (`ingest.py`)

**Purpose:** Loads a PDF, splits it into semantic chunks, embeds them using BGE-M3, and stores in ChromaDB.

**How it works:**
1. Accepts a PDF path via command-line argument or interactive input
2. Extracts text using `pdfplumber` (page-by-page)
3. Splits into chunks of ~800 characters with 150-char overlap using `RecursiveCharacterTextSplitter`
4. Generates multilingual embeddings using **BGE-M3** (BAAI/bge-m3)
5. **Appends** to existing ChromaDB (doesn't overwrite — supports multi-document ingestion)
6. Lists all ingested documents after completion

**Key Design Decision:** Appending mode allows multiple PDFs to be ingested into the same database. Each chunk retains its `source` metadata for filtering during analysis.

**Usage:**
```bash
.\venv\Scripts\python.exe ingest.py path\to\document.pdf
```

---

### Shared Configuration (`config.py`)

**Purpose:** Centralizes all configuration and shared utility functions.

**Provides:**
- `GOOGLE_API_KEY`, `DB_DIR`, `EMBEDDING_MODEL`, `MODEL_NAME` constants
- `get_embedding_function()` — singleton BGE-M3 instance
- `get_vector_store()` — singleton ChromaDB connection
- `get_llm()` — creates a Gemini 2.5 Flash instance
- `call_llm(prompt)` — calls the LLM with automatic retry on rate limits (429 / RESOURCE_EXHAUSTED), exponential backoff
- `build_source_filter()` — converts document selection into ChromaDB filter syntax (supports single, multiple via `$or`, or all)

---

### Agent 2: Retrieval Agent (`agents/retrieval_agent.py`)

**Purpose:** Takes a user query and retrieves the most relevant document chunks from ChromaDB.

**Input:** `{ query, source_filter }`
**Output:** `{ query, chunks: [{ text, page, source, similarity_score }] }`

**How it works:**
1. Uses `similarity_search_with_relevance_scores()` to get both content and confidence
2. Returns top-5 chunks with:
   - Full text content
   - Page number (converted from 0-indexed to 1-indexed)
   - Source filename
   - Similarity score (for confidence indication)
3. Supports multi-document filtering via ChromaDB `$or` operator

---

### Agent 3: Clause Identification Agent (`agents/clause_agent.py`)

**Purpose:** Classifies each retrieved chunk by its legal clause type using the LLM.

**Input:** `{ query, chunks }` (from Agent 2)
**Output:** `{ query, clauses: [{ ...chunk, clause_type }] }`

**Supported clause types:**
- Termination
- Liability
- Indemnification
- Payment Terms
- Confidentiality
- Intellectual Property
- Jurisdiction / Governing Law
- Force Majeure
- Non-Compete / Non-Solicitation
- Warranty / Disclaimer
- Other

**How it works:**
1. Builds a single batch prompt containing all chunks
2. Requests **JSON-only** output from Gemini for reliable parsing
3. Parses the JSON array and merges clause types into the chunk data
4. Falls back to "Other" if JSON parsing fails

---

### Agent 4: Risk Evaluation Agent (`agents/risk_agent.py`)

**Purpose:** Evaluates risk level for each classified clause using a **hybrid approach** — LLM analysis + rule-based heuristics.

**Input:** `{ query, clauses }` (from Agent 3)
**Output:** `{ query, risks: [{ ...clause, risk_level, risk_flags, llm_reasoning }] }`

**LLM Component:**
- Evaluates each clause as Low / Medium / High risk
- Provides brief reasoning for each assessment

**Rule-Based Component — 5 heuristic checks:**

| Flag | What it detects | Pattern |
|------|----------------|---------|
| `unlimited_liability` | No cap on liability | "unlimited liability", "no limit on damages" |
| `one_sided_indemnity` | Only one party indemnifies | "sole expense of the licensee" |
| `auto_renewal` | Contract auto-renews | "shall automatically renew" |
| `short_notice` | Notice period < 30 days | "7 days prior written notice" |
| `broad_non_compete` | Restrictive non-compete | "shall not compete" |

**Risk Elevation:** If critical flags (unlimited liability, one-sided indemnity) are detected, the rule engine can **upgrade** the LLM's risk level (Low→Medium, Medium→High).

---

### Agent 5: Explanation Agent (`agents/explanation_agent.py`)

**Purpose:** Generates a plain-language risk report with source references and practical suggestions.

**Input:** `{ query, risks }` (from Agent 4)
**Output:** `{ query, report: [{ clause_type, risk_level, source_ref, original_excerpt, risk_flags, explanation, why_it_matters, suggestion }] }`

**Each report entry includes:**
- **Clause type** — what kind of clause it is
- **Risk level** — Low / Medium / High
- **Source reference** — page number and source filename
- **Original excerpt** — first 200 characters of the original text
- **Risk flags** — any rule-based flags that were triggered
- **Explanation** — plain-English description of the clause
- **Why it matters** — what could go wrong for the signer
- **Suggestion** — how to negotiate or improve the clause

**Also provides** `format_report()` — pretty-prints the full report to the console with visual indicators (`[!!!]` High, `[!!]` Medium, `[!]` Low).

---

### Orchestrator (`analyze.py`)

**Purpose:** Entry point offering two modes — Risk Analysis and Q&A Chat.

**Mode 1: Risk Analysis**
1. Lists ingested documents → user selects one, multiple (comma-separated), or all
2. User enters a topic (e.g., "liability", "termination")
3. Calls Agent 2 → Agent 3 → Agent 4 → Agent 5
4. Displays formatted risk report

**Mode 2: Q&A Chat**
1. Same document selection as above
2. Enters a chat loop — user asks free-form questions
3. Retrieves relevant chunks → QnA Agent generates answer in user's language
4. User can type `analyze` to trigger full risk pipeline on last topic
5. User types `exit` to quit

**Usage:**
```bash
.\venv\Scripts\python.exe analyze.py
```

---

### Agent 6: Q&A Agent (`agents/qna_agent.py`)

**Purpose:** Conversational RAG agent for free-form document questions.

**Input:** `query (str)`, `chunks (list)`
**Output:** `{ answer, sources: [{ page, source }] }`

**How it works:**
1. Receives chunks from Retrieval Agent
2. Builds a context block with source references
3. Sends a "helpful legal assistant" prompt to Gemini that:
   - Answers based ONLY on document context
   - Auto-detects query language and responds in the same language
   - Cites page numbers and source files
4. Returns the answer with source metadata

---

## Technology Choices

| Decision | Choice | Reasoning |
|----------|--------|-----------|
| Embedding Model | BGE-M3 | Multilingual (100+ languages), strong on legal text, supports cross-lingual retrieval |
| Vector DB | ChromaDB | Lightweight, local, supports metadata filtering, easy to set up |
| LLM | Gemini 2.5 Flash | Free tier via Google AI Studio, fast, good at structured JSON output |
| Chunking | RecursiveCharacterTextSplitter (800 chars, 150 overlap) | Preserves paragraph boundaries, overlap prevents cutting clauses |
| Agent communication | Python dicts | Simple, debuggable, no serialization overhead |

---

## RAG Evaluation (RAGAS Metrics)

The system has been evaluated using the **RAGAS** framework with 15 hand-crafted test questions against the sample deed PDF. Mistral is used as the evaluator LLM to avoid Gemini rate limits.

### Results

| Metric | Score | Target | Status |
|--------|-------|--------|--------|
| **Faithfulness** | 0.9731 | 0.85 | PASS |
| **Answer Relevancy** | 0.9411 | 0.80 | PASS |
| **Context Precision** | 0.9149 | 0.75 | PASS |
| **Context Recall** | 1.0000 | 0.75 | PASS |

### What These Mean

- **Faithfulness (97%)** - Nearly zero hallucinations. All LLM claims are grounded in retrieved document context.
- **Answer Relevancy (94%)** - Answers directly address the user's question.
- **Context Precision (91%)** - Retrieved chunks are highly relevant to the query.
- **Context Recall (100%)** - The system finds all relevant information from the documents.

### Evaluation Architecture

- **Step 1** (`evaluate.py`): Runs 15 test questions through the RAG pipeline (BGE-M3 retrieval + Gemini generation), saves outputs to `eval_intermediate.json`
- **Step 2** (`evaluate_ragas.py`): Computes RAGAS metrics using Mistral as evaluator LLM + Mistral embeddings, saves detailed per-question results to `eval_results.json`

### Mistral Fallback

Added Mistral (mistral-small-latest) as an automatic fallback LLM in `config.py`. When Gemini hits rate limits (429 / RESOURCE_EXHAUSTED) after 3 retries with exponential backoff, the system seamlessly switches to Mistral for uninterrupted operation.

---

## What Remains (Future Work)

| Feature | Priority | Status |
|---------|----------|--------|
| Streamlit web interface | High | Not started |
| DOCX file support | Medium | Not started |
| Map-Reduce full document scan | High | Not started |
| Auto language detection | Medium | Not started |
| Contract comparison (multi-doc diff) | Low | Not started |
| Risk heatmap visualization | Low | Not started |
| Scanned PDF OCR (pytesseract) | Low | Not started |
