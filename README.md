# FeedbackIQ

**Turn unstructured customer feedback into actionable business intelligence.**

FeedbackIQ ingests raw customer reviews — pasted text, CSV, or Excel — classifies each one across seven dimensions using a large language model, and produces a live analytics dashboard, a RAG-grounded AI action plan, and a professional PDF report. Built for businesses that receive customer feedback and want to know exactly what to fix first.

---

## What It Does

Upload your customer reviews and within a minute FeedbackIQ delivers:

- **Seven-dimensional classification** of every review: sentiment, primary and secondary category, aspect-level breakdown, urgency, emotion, core issue, and confidence
- **Custom categories per business** — you define your own feedback categories during setup, so classification is specific to your business rather than generic buckets
- **A visual analytics dashboard** — sentiment distribution, emotion breakdown, category volumes, an urgency heatmap, and top negative issues
- **A RAG-grounded AI action plan** — prioritised, specific recommendations drawn from a curated knowledge base of proven business solutions, each tied to your actual data
- **Trend analysis** across multiple analyses — sentiment trajectory, category drift, and emerging versus resolved issues over time
- **Anonymous industry benchmarking** — see how your sentiment and critical-issue rates compare to other businesses in your industry
- **A professional PDF report** — a six-section downloadable report suitable for sharing with stakeholders
- **Webhook alerts** — get notified when critical issues spike, sentiment drops, or a new top issue emerges

---

## Supported Industries

FeedbackIQ's AI action plan is built and validated for five industries, each with a dedicated curated knowledge base of proven solutions:

- **E-commerce** — delivery, fulfilment, product quality, pricing, checkout, returns
- **SaaS** — onboarding, activation, churn, billing, performance, feature adoption
- **Hospitality** — check-in, cleanliness, food quality, staff service, amenities
- **Retail** — staff helpfulness, queues, stock availability, store experience, loyalty
- **Logistics** — delivery accuracy, tracking, damage prevention, driver professionalism

Businesses outside these five can still use the full platform — classification, dashboard, trends, and benchmarking all work for any industry. The action plan falls back to a general business-solutions knowledge base for unsupported industries.

---

## Architecture

FeedbackIQ is a Python backend with a React frontend, designed so the core engine is fully decoupled from any interface.

```
feedbackiq/
├── core/                      # Pure Python business logic (no web framework)
│   ├── preprocessing.py       # 11-stage text cleaning pipeline
│   ├── classifier.py          # Groq + Gemini classification engine
│   ├── classifier_async.py    # Concurrent classification with semaphore
│   ├── prompt_builder.py      # Dynamic classification prompt assembly
│   ├── validator.py           # Pydantic output validation
│   ├── aggregator.py          # Single source of truth for all metrics
│   ├── action_plan.py         # RAG-grounded action plan generation
│   ├── trend_engine.py        # Cross-session trend analysis
│   ├── benchmark_engine.py    # Anonymised industry benchmarking
│   ├── webhook_engine.py      # Alert detection and webhook delivery
│   ├── charts.py              # Plotly chart builders (no Streamlit imports)
│   ├── pdf_report.py          # WeasyPrint + Jinja2 PDF generation
│   ├── results.py             # Results DataFrame assembly
│   └── rag/                   # Retrieval-augmented generation pipeline
│       ├── embedder.py        # sentence-transformers embeddings
│       ├── knowledge_base.py  # ChromaDB vector store + retrieval
│       └── documents/         # Curated industry solution knowledge base
│
├── api/                       # FastAPI layer
│   ├── main.py                # App factory, middleware, lifespan
│   ├── models.py              # Request/response schemas
│   ├── auth/                  # JWT auth, password hashing, dependencies
│   ├── storage/               # Disk-based user and session stores
│   ├── routes/                # Auth, sessions, analyse, dashboard,
│   │                          #   action-plan, report, export, trends,
│   │                          #   benchmarks, webhooks
│   └── middleware/            # Rate limiting, error handlers
│
├── frontend/                  # React + TypeScript + Tailwind
│
├── templates/                 # Jinja2 PDF templates
├── config.py                  # Configuration constants
└── test_pipeline.py           # 25-section test suite
```

### Design Principles

- **`aggregator.py` is the single source of truth.** Every chart, the action plan, and the PDF read from one aggregated dictionary. Nothing recomputes metrics independently.
- **`core/` has zero web-framework dependencies.** The business logic is importable in pure Python, fully testable without a server, and was migrated from Streamlit to FastAPI without a single change to the classification engine.
- **Storage is abstracted behind an interface.** Development uses disk-based JSON; swapping to PostgreSQL or Redis for production requires changing only the storage layer, not routes or logic.
- **Two-provider LLM with automatic fallback.** Groq is primary; Gemini takes over automatically on rate-limit errors, with exponential backoff.

---

## How the AI Action Plan Works

The action plan is the platform's most distinctive feature and the hardest to replicate with a raw LLM call.

1. **Zero raw review text reaches the action-plan LLM call.** It receives only computed statistics from `aggregator.py` — counts, percentages, top issues, emotion distribution. This is the primary anti-hallucination control: the model cannot misattribute or confabulate because it is given grounded facts, not 2000 reviews to interpret.

2. **Per-issue RAG retrieval.** For each top issue, FeedbackIQ embeds the actual customer complaint text and retrieves the most relevant proven solutions from a curated ChromaDB knowledge base, filtered by industry and a relevance threshold. A delivery complaint retrieves delivery solutions; a pricing complaint retrieves pricing solutions.

3. **Grounded generation.** The retrieved solutions are injected into the prompt, matched to their specific issue category. The model is instructed to cite the proven approaches and the real numbers, and is explicitly forbidden from generic business language.

4. **Self-verification.** Before the plan reaches the user, a Python verification pass confirms each recommendation cites real numbers, references the actual issue categories, and avoids generic filler. Failures trigger a regeneration within the existing retry budget.

The result is recommendations like *"5 negative reviews cite inconsistent tracking — implement automated SMS updates at each shipping stage using your courier's API; target zero where-is-my-order complaints within 30 days"* rather than *"improve your delivery processes."*

---

## Anti-Hallucination Stack

Classification reliability comes from five active layers on every call:

1. Temperature 0.0 — classification is deterministic, not creative
2. Controlled vocabulary — every allowed value for every field is listed explicitly in the prompt
3. Five few-shot examples covering edge cases
4. Pre-validation normalisation — labels lowercased and stripped before validation
5. Pydantic validation with retry — invalid output triggers a correction-prefixed retry; categories outside the allowed list are fixed rather than failing

---

## Tech Stack

**Backend:** Python, FastAPI, Pydantic, Pandas
**LLMs:** Groq (Llama 3.1) primary, Google Gemini fallback
**RAG:** sentence-transformers (all-MiniLM-L6-v2), ChromaDB
**PDF:** WeasyPrint + Jinja2
**Auth:** JWT (python-jose), Argon2 password hashing (pwdlib)
**Frontend:** React, TypeScript, Tailwind CSS, Recharts
**Storage:** Disk-based JSON (PostgreSQL-ready via interface)

All components run free of charge — local embeddings, free LLM tiers, no paid infrastructure.

---

## Running Locally

### Prerequisites

- Python 3.11+
- Node.js 18+
- Free API keys from [Groq](https://console.groq.com) and [Google AI Studio](https://aistudio.google.com)

### Backend

```bash
git clone https://github.com/JhanviBarot/FeedBackIQ.git
cd feedbackiq
python -m venv venv
source venv/bin/activate        # macOS/Linux
venv\Scripts\activate           # Windows
pip install -r requirements.txt
```

Create a `.env` file:

```
GROQ_API_KEY=your_groq_key
GEMINI_API_KEY=your_gemini_key
JWT_SECRET_KEY=run_python_-c_"import secrets; print(secrets.token_hex(32))"
```

Run the test suite (zero API cost):

```bash
python test_pipeline.py
```

Start the API:

```bash
uvicorn api.main:app --reload --port 8000
```

Interactive API docs are available at `http://localhost:8000/docs`.

### Frontend

```bash
cd frontend
npm install
npm run dev
```

The app runs at `http://localhost:5173`.

---

## Testing

The project includes a 25-section test suite covering the full pipeline — preprocessing, classification logic, aggregation, file parsing, PDF generation, authentication, all API endpoints, trend analysis, benchmarking, webhooks, and the RAG pipeline. Every section runs with zero API cost using mocked LLM responses.

```bash
python test_pipeline.py
```

---

## What Makes FeedbackIQ Different

A raw LLM call can classify a handful of reviews. FeedbackIQ does three things a single LLM call cannot:

1. **Consistent structured classification at scale** — 2000 reviews classified into your custom categories with zero hallucination, via controlled vocabulary and a Pydantic validation-and-retry pipeline that a raw prompt cannot guarantee.

2. **Longitudinal intelligence** — it tracks your feedback across analyses and tells you whether your fixes are working: sentiment trajectory, emerging issues, resolved issues. A stateless LLM call has no memory and cannot do this.

3. **RAG-grounded recommendations** — action-plan advice is retrieved from a curated knowledge base of proven, quantified business solutions and matched to each specific issue, rather than generated from the model's general priors.

---

## Roadmap

- Review clustering for large datasets — group similar reviews and surface the most representative quote per cluster
- Predictive alerts — detect early-warning signals (rising frustration, medium-urgency growth) before they become critical
- Expanded industry coverage for the action-plan knowledge base
- PostgreSQL storage backend for production scale

---

## License

This project is for portfolio and demonstration purposes.

---

*FeedbackIQ — upload your reviews, get a complete intelligence report in under a minute.*