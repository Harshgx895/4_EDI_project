# LegalLens — AI Legal Document Reviewer

AI-powered legal document analysis platform that combines multi-agent RAG with rule-based heuristics to identify risky clauses, provide actionable recommendations, and answer questions about legal documents in 100+ languages.

## Features

- **Multi-Agent Risk Analysis** — 4-stage pipeline: Retrieval → Clause Classification → Risk Evaluation → Explanation
- **Hybrid Detection** — LLM reasoning + regex-based rule checks (unlimited liability, auto-renewal, short notice, etc.)
- **Conversational Q&A** — Chat with your documents with context-aware follow-up questions
- **Multilingual Support** — Ask questions and get answers in English, Hindi, Hinglish, and 100+ languages
- **Document Management** — Upload, filter, preview, and delete PDF/DOCX files
- **PDF Export** — Download structured risk reports and Q&A session transcripts as PDFs
- **RAGAS Evaluation** — Built-in pipeline quality metrics (Faithfulness, Relevancy, Precision, Recall)
- **One-Click Scan** — "Scan All Risks" button for comprehensive document analysis without specifying a topic

## Architecture

```
┌──────────────────────────────────────────────────────────────────┐
│                     FastAPI Server (server.py)                   │
├──────────────┬──────────────┬─────────────────┬─────────────────┤
│  /api/upload │ /api/analyze │   /api/chat     │   /api/eval     │
│  /api/docs   │              │  (+ history)    │                 │
└──────┬───────┴──────┬───────┴────────┬────────┴─────────────────┘
       │              │                │
  ┌────▼────┐   ┌─────▼──────────┐  ┌─▼──────────┐
  │ingest.py│   │ Risk Pipeline  │  │ qna_agent   │
  │PDFPlumb.│   │ retrieve →     │  │ (with chat  │
  │BGE-M3   │   │ classify →     │  │  memory)    │
  │ChromaDB │   │ evaluate →     │  └─────────────┘
  └─────────┘   │ explain        │
                └────────────────┘
                     │
              ┌──────▼──────┐
              │  LLM Layer  │
              │ Mistral(1st)│
              │ Gemini(2nd) │
              └─────────────┘
```

## Tech Stack

| Component | Technology |
|-----------|-----------|
| Backend | FastAPI + Uvicorn |
| Frontend | Vanilla HTML/CSS/JS (dark-mode SPA) |
| Embeddings | BGE-M3 (HuggingFace, multilingual) |
| Vector DB | ChromaDB (local, persistent) |
| LLM | Mistral (primary) → Gemini 2.5 Flash (fallback) |
| PDF Parsing | PDFPlumber |
| DOCX Parsing | python-docx |
| Evaluation | RAGAS framework |
| PDF Export | html2pdf.js |
| Markdown Rendering | marked.js |

## Quick Start

### 1. Clone and install

```bash
git clone https://github.com/your-repo/4_EDI_project.git
cd 4_EDI_project
python -m venv venv
venv\Scripts\activate        # Windows
pip install -r requirements.txt
```

### 2. Configure API keys

Create a `.env` file:

```env
MISTRAL_API_KEY=your_mistral_key
GOOGLE_API_KEY=your_google_key
```

### 3. Ingest a document

```bash
python ingest.py path/to/document.pdf
```

### 4. Run the server

```bash
python server.py
```

Open **http://localhost:8000** in your browser.

## Project Structure

```
├── server.py              # FastAPI backend — API routes + orchestration
├── config.py              # Shared config, LLM clients, vector store singletons
├── ingest.py              # Document loading, chunking, embedding, ChromaDB storage
├── agents/
│   ├── retrieval_agent.py # Semantic search over ChromaDB
│   ├── clause_agent.py    # LLM-based clause type classification
│   ├── risk_agent.py      # Hybrid LLM + rule-based risk evaluation
│   ├── explanation_agent.py # Plain-English explanations + recommendations
│   └── qna_agent.py       # Conversational Q&A with chat memory
├── static/
│   ├── index.html         # SPA shell — sidebar, views, overlays
│   ├── style.css          # Design system — dark mode, animations
│   └── app.js             # Client-side state, API calls, PDF export
├── evaluate_ragas.py      # RAGAS evaluation pipeline
├── eval_dataset.json      # 15 curated test Q&A pairs
├── eval_results.json      # Latest RAGAS scores
├── analyze.py             # CLI interface for risk analysis
├── requirements.txt       # Python dependencies
└── .gitignore
```

## Risk Detection Rules

The system uses both LLM analysis and regex-based rules to flag:

| Rule | Pattern Detected |
|------|-----------------|
| Unlimited Liability | "no cap on liability", "without limitation" |
| One-Sided Indemnity | Sole expense of one party |
| Auto-Renewal | Automatic renewal without notice |
| Short Notice Period | Termination notice < 30 days |
| Broad Non-Compete | Non-compete / non-solicitation clauses |

## Evaluation Results

| Metric | Score | Target |
|--------|-------|--------|
| Faithfulness | 97% | 85% ✅ |
| Answer Relevancy | 94% | 80% ✅ |
| Context Precision | 91% | 75% ✅ |
| Context Recall | 100% | 75% ✅ |

## Disclaimer

This tool provides AI-assisted analysis for informational purposes only. It does not constitute legal advice. Always consult a qualified attorney for legal matters.
