# AI Legal Document Reviewer

> *"Since you can't upload large docs in normal LLMs like ChatGPT, our system helps you analyze large docs in any language."*

An AI agent-based system that analyzes legal documents of **any size** in **any language** using RAG (Retrieval-Augmented Generation) and a multi-agent pipeline.

---

## Features

- **Large Document Support** — ingest documents of any size (no token limits)
- **PDF + DOCX Support** — upload both file formats via CLI or web UI
- **6 Specialized AI Agents** — modular pipeline for retrieval, clause classification, risk evaluation, and explanation
- **Hybrid Risk Detection** — LLM analysis + rule-based heuristic flags (unlimited liability, one-sided indemnity, short notice, etc.)
- **Cross-Lingual Queries** — ask questions in Hindi, English, Hinglish, or 100+ other languages
- **Dual Mode Interface**:
  - **Risk Analysis** — structured clause-by-clause risk report with color-coded risk cards
  - **Q&A Chat** — conversational document Q&A in any language
- **Streamlit Web Frontend** — file upload, risk analysis, chat, and evaluation metrics dashboard
- **Explainable Output** — every finding includes page number, source file, original excerpt, and practical suggestions
- **Resilient LLM Backend** — Mistral (primary) with Gemini (fallback), automatic failover
- **RAGAS Evaluation** — all 4 metrics passing (97% faithful, 94% relevant, 91% precise, 100% recall)

---

## Architecture

```
Document (PDF/DOCX) → Ingestion Agent → ChromaDB (Vector Store)
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
| Primary LLM | Mistral Small (Mistral AI) |
| Fallback LLM | Google Gemini 2.5 Flash |
| Document Processing | pdfplumber, python-docx |
| Frontend | Streamlit |
| Evaluation | RAGAS |

---

## RAG Evaluation Results

| Metric | Score | Target | Status |
|--------|-------|--------|--------|
| **Faithfulness** | 0.9731 | 0.85 | ✅ PASS |
| **Answer Relevancy** | 0.9411 | 0.80 | ✅ PASS |
| **Context Precision** | 0.9149 | 0.75 | ✅ PASS |
| **Context Recall** | 1.0000 | 0.75 | ✅ PASS |

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

### 2. Configure API Keys

Create a `.env` file:
```
GOOGLE_API_KEY=your_google_ai_studio_key_here
MISTRAL_API_KEY=your_mistral_api_key_here
```

- Google key: [Google AI Studio](https://aistudio.google.com/apikey)
- Mistral key: [Mistral AI Console](https://console.mistral.ai/api-keys)

### 3. Ingest a Document

```bash
python ingest.py path/to/your/legal-document.pdf
# or
python ingest.py path/to/your/contract.docx
```

### 4. Run the Web App

```bash
streamlit run app.py
```

Opens at `http://localhost:8501` with file upload, risk analysis, Q&A chat, and evaluation metrics.

### 5. Run CLI Mode (Alternative)

```bash
python analyze.py
```

Choose your mode:
- **[1] Risk Analysis** — structured risk report with clause classification
- **[2] Q&A Chat** — ask free-form questions in any language

---

## Project Structure

```
├── .env                          # API keys (GOOGLE_API_KEY, MISTRAL_API_KEY)
├── config.py                     # Shared config, LLM fallback (Mistral → Gemini)
├── ingest.py                     # Agent 1: Document Ingestion (PDF + DOCX)
├── analyze.py                    # CLI Orchestrator (dual-mode)
├── app.py                        # Streamlit Web Frontend
├── evaluate.py                   # RAG evaluation pipeline (Step 1)
├── evaluate_ragas.py             # RAGAS metric computation (Step 2)
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
