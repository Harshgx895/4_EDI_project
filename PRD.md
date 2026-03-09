# Product Requirements Document (PRD)

## Product Title

**AI Agent–Based Legal Document Reviewer**
*"Since you can't upload large docs in normal LLMs like ChatGPT, our system helps you analyze large docs in any language."*

---

## 1. Product Overview

The **AI Agent–Based Legal Document Reviewer** is an intelligent system that analyzes legal documents such as contracts, agreements, and policies — regardless of their size or language.

Modern LLMs like ChatGPT impose file size and token limits that make it impossible to analyze large legal contracts in full. This system solves that by using **Retrieval-Augmented Generation (RAG)** to ingest documents of any size into a local vector database, then intelligently retrieve and analyze only the relevant sections using a **multi-agent pipeline**.

Each stage of the analysis — retrieval, clause classification, risk evaluation, and explanation — is handled by a dedicated AI agent, creating a transparent, modular, and explainable workflow. The system also offers a **conversational Q&A mode** for free-form document questioning in any language.

The platform supports **multilingual document analysis and cross-lingual user interaction** using the BGE-M3 multilingual embedding model. Users can upload documents in one language and query them in another.

> **Disclaimer:** All output is informational and not a substitute for professional legal advice.

---

## 2. Problem Statement

Legal documents contain critical information affecting contractual obligations, liabilities, and rights. However:

- They are written in complex legal language
- They can span dozens or hundreds of pages
- They contain clauses that may be unfavorable or risky
- They require legal expertise to interpret accurately
- **Existing LLMs (ChatGPT, Gemini, Claude) have file size / token limits** that prevent full-document analysis

Individuals and small organizations frequently lack access to professional legal review due to cost or time constraints.

---

## 3. Product Goals

1. Enable automated analysis of **large legal documents** (any size)
2. Identify potentially risky clauses within contracts
3. Provide clear, plain-language explanations of complex legal text
4. Allow users to query documents using natural language
5. Support **multilingual** document understanding and **cross-language** queries
6. Demonstrate a **modular multi-agent AI architecture** using LangChain
7. Provide **explainable output** with source references (page numbers, excerpts)

---

## 4. Target Users

### Primary Users
- Students studying law or business
- Small business owners reviewing agreements
- Non-legal professionals handling contracts

### Secondary Users
- Researchers studying legal document analysis
- Developers exploring AI-based document understanding
- Legal professionals performing preliminary reviews

---

## 5. Key Novelty

### 1. Multi-Agent Pipeline Architecture
The system uses **6 specialized AI agents**, each responsible for a distinct stage:

| Agent | Responsibility |
|-------|---------------|
| **Ingestion Agent** | Extract text, chunk, embed, store in vector DB |
| **Retrieval Agent** | Semantic search with similarity scoring |
| **Clause Identification Agent** | Classify clause types using LLM |
| **Risk Evaluation Agent** | LLM risk assessment + rule-based heuristic flags |
| **Explanation Agent** | Plain-English explanations with source references |
| **Q&A Agent** | Conversational document Q&A in any language |

### 2. Large Document Support
Unlike ChatGPT/Gemini/Claude which have upload limits, this system:
- Ingests documents of **any size** into a local vector database
- Retrieves only the most relevant chunks per query
- Each agent processes chunks efficiently in batch

### 3. Hybrid Risk Detection (LLM + Rules)
The Risk Evaluation Agent combines:
- **LLM-based** contextual risk assessment
- **Rule-based** pattern matching for critical flags:
  - Unlimited liability
  - One-sided indemnification
  - Auto-renewal without notice
  - Short termination notice periods (< 30 days)
  - Broad non-compete clauses

Rule-based flags can **elevate** the LLM's risk level for critical findings.

### 4. Cross-Lingual Interaction
Using the **BGE-M3** multilingual embedding model (supports 100+ languages):
- Documents can be in any language
- Users can query in a different language
- The system retrieves correct clauses regardless of language mismatch

### 5. Explainable Output with Source References
Every finding includes:
- Clause type classification
- Risk level (Low / Medium / High)
- Page number and source file reference
- Original text excerpt
- Plain-English explanation
- Practical suggestion for negotiation

---

## 6. System Architecture

### Pipeline Flow

```
Document (PDF) → Ingestion Agent → ChromaDB (Vector Store)
                                        ↓
Mode 1 (Risk Analysis):
  User Query → Retrieval Agent → Clause ID Agent → Risk Eval Agent → Explanation Agent → Report

Mode 2 (Q&A Chat):
  User Query → Retrieval Agent → Q&A Agent → Answer (in user's language)
              ↘ User types 'analyze' → triggers Mode 1 on last query
```

### Data Flow Between Agents

Each agent receives structured data (Python dict) and returns structured data:

```
Agent 2 (Retrieval)    → { query, chunks: [{ text, page, source, similarity_score }] }
Agent 3 (Clause ID)    → { query, clauses: [{ ...chunk, clause_type }] }
Agent 4 (Risk Eval)    → { query, risks: [{ ...clause, risk_level, risk_flags, llm_reasoning }] }
Agent 5 (Explanation)  → { query, report: [{ clause_type, risk_level, source_ref, explanation, suggestion }] }
Agent 6 (Q&A)          → { answer, sources: [{ page, source }] }
```

---

## 7. Technology Stack

| Component | Technology |
|-----------|-----------|
| Language | Python |
| AI Framework | LangChain |
| Vector Database | ChromaDB |
| Embedding Model | BGE-M3 (BAAI/bge-m3) — multilingual, 100+ languages |
| LLM | Google Gemini 2.5 Flash (via Google AI Studio) |
| Document Processing | pdfplumber |
| Environment | python-dotenv |
| Frontend | Streamlit (planned) |

---

## 8. Project Structure

```
4_EDI_project/
├── .env                          # API keys
├── config.py                     # Shared configuration & utilities
├── ingest.py                     # Agent 1: Document Ingestion
├── analyze.py                    # Orchestrator: dual-mode (Risk Analysis / Q&A Chat)
├── requirements.txt              # Python dependencies
├── agents/
│   ├── __init__.py
│   ├── retrieval_agent.py        # Agent 2: Semantic retrieval
│   ├── clause_agent.py           # Agent 3: Clause classification
│   ├── risk_agent.py             # Agent 4: Risk evaluation
│   ├── explanation_agent.py      # Agent 5: Explanation generation
│   └── qna_agent.py              # Agent 6: Conversational Q&A
├── chroma_db/                    # Vector database (auto-generated)
└── venv/                         # Python virtual environment
```

---

## 9. Functional Requirements

- Upload legal documents in **PDF** format
- Extract text and split into semantic chunks
- Generate multilingual embeddings and store in vector database
- Retrieve relevant chunks using semantic similarity search
- Classify retrieved chunks by clause type
- Evaluate risk using LLM analysis + rule-based heuristics
- Generate plain-language explanations with source references
- Support multi-document ingestion and per-document filtering
- Support cross-language queries (e.g., Hindi query on English document)
- **Conversational Q&A** mode for free-form document questioning
- **Dual-mode interface**: structured risk analysis or conversational Q&A
- Q&A responses in the **user's query language** (auto-detected)

---

## 10. Non-Functional Requirements

- **Scalability:** Handle large documents (100+ pages) without performance degradation
- **Explainability:** All outputs include page references and original text excerpts
- **Modularity:** Each agent is independently developed and testable
- **Security:** Documents processed locally, never sent to external services (except LLM API)
- **Performance:** Return results within acceptable response times

---

## 11. Success Metrics

- Retrieval accuracy (relevant chunks returned)
- Clause classification accuracy
- Risk detection accuracy (including rule-based flag precision)
- Response clarity (user comprehension)
- Query response time
- User feedback

---

## 12. Limitations

- Incorrect interpretation of complex or ambiguous legal language
- LLM hallucination risks (mitigated by source references)
- Variation in legal standards across jurisdictions
- Currently supports PDF only (DOCX planned)

---

## 13. Ethical Considerations

> The information provided by this system is for **informational purposes only** and should not be considered legal advice. Users should consult qualified legal professionals before making legal decisions.

---

## 14. Future Enhancements

- **DOCX support** via python-docx
- **Scanned PDF OCR** via pytesseract
- **Streamlit web interface** for file upload and interactive analysis
- **Map-Reduce full document scan** — analyze ALL chunks for a complete risk report
- **Contract comparison** across multiple documents
- **Auto language detection** with explicit response-language control
- **Risk heatmap** — visual page-by-page risk overview
- **Legal knowledge graph** integration
