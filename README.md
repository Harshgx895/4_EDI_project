# AI Legal Document Reviewer

> *"Since you can't upload large docs in normal LLMs like ChatGPT, our system helps you analyze large docs in any language."*

An AI agent-based system that analyzes legal documents of **any size** in **any language** using RAG (Retrieval-Augmented Generation) and a multi-agent pipeline.

---

## Features

- **Large Document Support** — ingest documents of any size (no token limits)
- **6 Specialized AI Agents** — modular pipeline for retrieval, clause classification, risk evaluation, and explanation
- **Hybrid Risk Detection** — LLM analysis + rule-based heuristic flags (unlimited liability, one-sided indemnity, short notice, etc.)
- **Cross-Lingual Queries** — ask questions in Hindi, English, Hinglish, or 100+ other languages
- **Dual Mode Interface**:
  - **Risk Analysis** — structured clause-by-clause risk report
  - **Q&A Chat** — conversational document Q&A in any language
- **Explainable Output** — every finding includes page number, source file, original excerpt, and practical suggestions

---

## Architecture

```
Document (PDF) → Ingestion Agent → ChromaDB (Vector Store)
                                        ↓
Mode 1 (Risk Analysis):
  Query → Retrieval → Clause ID → Risk Eval → Explanation → Report

Mode 2 (Q&A Chat):
  Query → Retrieval → Q&A Agent → Answer (in user's language)
```

---

## Tech Stack

| Component | Technology |
|-----------|-----------|
| AI Framework | LangChain |
| Vector Database | ChromaDB |
| Embedding Model | BGE-M3 (100+ languages) |
| LLM | Google Gemini 2.5 Flash |
| Document Processing | pdfplumber |

---

## Setup

### 1. Clone & Install

```bash
git clone https://github.com/Harshgx895/4_EDI_project.git
cd 4_EDI_project
python -m venv venv
.\venv\Scripts\activate      # Windows
pip install -r requirements.txt
```

### 2. Configure API Key

Create a `.env` file:
```
GOOGLE_API_KEY=your_google_ai_studio_key_here
```

Get a free key at [Google AI Studio](https://aistudio.google.com/apikey).

### 3. Ingest a Document

```bash
python ingest.py path/to/your/legal-document.pdf
```

### 4. Run Analysis

```bash
python analyze.py
```

Choose your mode:
- **[1] Risk Analysis** — structured risk report with clause classification
- **[2] Q&A Chat** — ask free-form questions in any language

---

## Project Structure

```
├── config.py                     # Shared configuration & utilities
├── ingest.py                     # Agent 1: Document Ingestion
├── analyze.py                    # Orchestrator (dual-mode)
├── requirements.txt
├── agents/
│   ├── retrieval_agent.py        # Agent 2: Semantic retrieval
│   ├── clause_agent.py           # Agent 3: Clause classification
│   ├── risk_agent.py             # Agent 4: Risk evaluation
│   ├── explanation_agent.py      # Agent 5: Explanation generation
│   └── qna_agent.py              # Agent 6: Conversational Q&A
```

---

## Documentation

- [PRD.md](PRD.md) — Product Requirements Document
- [PROGRESS.md](PROGRESS.md) — Development Progress & Walkthrough

---

## Disclaimer

> This tool is for **informational purposes only** and should not be considered legal advice. Consult qualified legal professionals before making legal decisions.
