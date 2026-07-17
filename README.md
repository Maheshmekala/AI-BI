# 📊 Instant BI — Tableau+ Edition

![DuckDB](https://img.shields.io/badge/Engine-DuckDB-FFF000)
![FastAPI](https://img.shields.io/badge/API-FastAPI-009688)
![React](https://img.shields.io/badge/Frontend-React%2BTS-61DAFB)
![SQL](https://img.shields.io/badge/Powered%20By-SQL-blue)
![Python](https://img.shields.io/badge/Python-3.10+-blue)
![Vite](https://img.shields.io/badge/Build-Vite-646CFF)
![License](https://img.shields.io/badge/License-MIT-green)

**Instant BI** is an AI-powered Business Intelligence application that lets you chat with your data in natural language. Upload files (CSV, Excel, PDF), connect to SQL databases (PostgreSQL, MySQL, SQLite), and get instant dashboards, KPIs, insights, and visualizations — all through a conversational interface.

**DuckDB SQL engine** — every chart, filter, and calculation generates SQL queries instead of pandas. The LLM **only reads schema + 10 sample rows**; all heavy lifting (aggregations, joins, correlations) is executed via DuckDB SQL. 10-100x more memory efficient than loading data into pandas.

**Multi-Agent LLM Routing** — different models for different tasks: fast/cheap models for SQL generation, capable models for insights and natural language responses. Configured via environment variables.

**Open-Source Chart Themes** — Tableau 10, ggplot2, Seaborn, Material, Retro, Viridis, Plasma, and Monokai color themes applied to all Plotly charts.

---

## 🎯 Overview

Instant BI bridges the gap between raw data and business decisions:

- **💬 Natural Language Interface** — Ask questions about your data in plain English
- **🤖 RAG-Powered Text-to-SQL** — NL questions generate SQL via retrieval-augmented generation (LLM sees **schema + 10 rows only**, not the full dataset)
- **🤖 Multi-Agent LLM Routing** — Different models for different tasks: fast Groq for SQL, capable Claude/OpenAI for insights and responses
- **📂 Multi-Source Data Support** — CSV, Excel, PDF, PostgreSQL, MySQL, SQLite, and more
- **🔥 DuckDB SQL Engine** — Every operation generates SQL, no pandas DataFrames in the hot path
- **📈 17 Chart Types** — Including Waterfall, Treemap, Gauge, Sankey, Parallel Coordinates, Candlestick
- **🎨 8 Open-Source Chart Themes** — Tableau 10, ggplot2, Seaborn, Material, Retro, Viridis, Plasma, Monokai
- **🔗 Cross-Filtering** — Click chart elements, other charts auto-filter via SQL WHERE clauses
- **📝 Chart + SQL Viewer** — Every chart shows the exact DuckDB query that generated it
- **🧮 Calculated Fields** — User-defined SQL expressions (e.g. `profit = revenue - cost`)
- **🔍 Drill-Down Hierarchies** — Auto-detect date/geo/categorical hierarchies with SQL GROUP BY

---

## 🏗️ Architecture

```
User Action (click, filter, drag, type)
  → Frontend sends intent (chart_type, x, y, agg, filters)
    → (Optional) Multi-Agent Task Router → selects fastest LLM for SQL, capable LLM for insights
    → Backend QueryBuilder generates optimal SQL
      → DuckDB executes SQL (aggregates, filters, joins)
        → Returns only the results needed for the chart
          → Plotly renders with open-source color themes
```

```
instant-bi/
├── sql_engine/                  # DuckDB SQL engine
│   ├── __init__.py              #   Connection manager, ingest, metadata
│   ├── query_builder.py         #   SQL generation from chart/filter specs
│   ├── shelf_to_sql.py          #   Drag-drop shelf → SQL converter
│   └── calculated_fields.py     #   SQL expression validation & views
│
├── rag/                         # RAG pipeline for NL→SQL
│   ├── schema_index.py          #   Index table schemas for retrieval
│   ├── embedder.py              #   Text embeddings
│   ├── retriever.py             #   Retrieve schema + few-shot examples
│   ├── llm_sql.py               #   Build prompt, call LLM, get SQL
│   ├── semantic_cache.py        #   Cache question→SQL pairs
│   ├── few_shot_store.py        #   Store successful Q→SQL examples
│   └── router.py                #   Intent classification
│
├── data_sources/                # Data loading layer (DuckDB-backed)
│   ├── base.py                  #   Dataset with SQL table ref (no DataFrame)
│   ├── file_sources.py          #   CSV/Excel/PDF → DuckDB tables
│   └── sql_sources.py           #   DuckDB ATTACH for PostgreSQL/MySQL/SQLite
│
├── insights/                    # SQL-powered stats engine
│   └── __init__.py              #   CORR(), PERCENTILE_CONT(), REGR_SLOPE() via SQL
│
├── visualization/               # Chart & dashboard rendering
│   ├── __init__.py              #   SQL-powered Plotly rendering (17 chart types)
│   └── advanced_charts.py       #   Waterfall, Treemap, Gauge, Sankey, etc.
│
├── mcp_charts.py                # MCP Chart Bridge — 8 open-source color themes
│
├── llm/                         # Multi-Agent LLM provider abstraction
│   ├── __init__.py              #   10+ providers: OpenAI, Anthropic, Groq, Google, Ollama...
│   └── task_router.py           #   Task-based routing: SQL→fast model, insights→capable model
│
├── query_engine/                # Natural language → SQL translation
│   └── engine.py                #   LLM generates SQL via RAG (schema + 10 rows only)
│
├── config/                      # Centralized configuration
├── utils/                       # Shared utilities
│
├── backend/                     # FastAPI REST API
│   ├── main.py                  #   API entry point with all routers
│   ├── state.py                 #   DuckDB-backed state management
│   ├── schemas.py               #   40+ Pydantic models
│   ├── routers/
│   │   ├── datasets.py          #   CRUD + chart-data + hierarchies endpoints
│   │   ├── query.py             #   NL query → SQL → chart with streaming
│   │   ├── insights.py          #   SQL-powered analysis endpoints
│   │   ├── sources.py           #   File upload + DB connect
│   │   ├── rag.py               #   RAG query endpoint
│   │   ├── calculations.py      #   Calculated fields CRUD
│   │   ├── models.py            #   LLM model listing
│   │   └── settings.py          #   App settings
│   ├── calculations/            #   Calculated field engine
│   ├── hierarchies/             #   Hierarchy detector
│   ├── blending/                #   Data blending engine (JOIN/UNION)
│   └── stories/                 #   Storyboarding engine
│
├── frontend/                    # Vite + React + TypeScript dashboard
│   ├── src/
│   │   ├── App.tsx              #   App shell with routing + DashboardProvider
│   │   ├── context/
│   │   │   └── dashboard-context.tsx  # Cross-filter, params, drill state
│   │   ├── components/charts/
│   │   │   ├── chart-with-sql.tsx     # Tabbed [Chart] + [SQL] viewer
│   │   │   ├── sql-viewer.tsx         # Syntax-highlighted SQL display
│   │   │   ├── interactive-chart-renderer.tsx # Plotly with selection events
│   │   │   └── chart-renderer.tsx     #   Base Plotly rendering
│   │   ├── hooks/
│   │   │   ├── use-chart-sql.ts       #   Track SQL alongside chart data
│   │   │   └── use-cross-filter.ts    #   Cross-filter state management
│   │   ├── pages/
│   │   │   ├── dashboard.tsx          #   Dashboard with SQL viewer
│   │   │   ├── charts.tsx             #   17 chart types with SQL sidebar
│   │   │   ├── chat.tsx               #   NL chat → SQL → chart
│   │   │   ├── insights.tsx           #   SQL-powered insights
│   │   │   ├── sources.tsx            #   Data source management
│   │   │   └── landing.tsx            #   Landing page
│   │   ├── types/index.ts             #   All TypeScript interfaces
│   │   └── lib/api.ts                 #   API client with all endpoints
│   ├── package.json
│   └── vite.config.ts
│
├── uploads/                     # Uploaded file storage
├── data/                        # Sample data
│   └── sample_sales_data.csv
├── requirements.txt             # Python dependencies
├── .env.example                 # Environment variable template
└── DOCKER.md                    # Docker deployment guide
```

---

## ✨ Key Features

### 🔥 DuckDB SQL Engine — The Core
| Capability | Old (pandas) | New (SQL) |
|-----------|--------------|-----------|
| Data loading | `pd.read_csv()` → RAM | DuckDB reads CSV/Parquet/JSON directly |
| Aggregation | `df.groupby().agg()` | `SELECT ... GROUP BY` |
| Filtering | Boolean masks | `WHERE` clauses |
| Joins | `pd.merge()` in RAM | SQL `JOIN` (hash join) |
| Correlations | `df.corr()` | `SELECT CORR(col1, col2)` |
| Trends | `scipy.linregress()` | `REGR_SLOPE(y, x)` |
| Memory | Loads entire dataset | Only returns aggregated results |

### 📂 Multi-Source Data Loading
| Source | Method |
|--------|--------|
| **CSV** | DuckDB `read_csv_auto()` — zero-copy, auto-detect types |
| **Excel** | openpyxl → DuckDB table |
| **PDF** | pdfplumber extraction → DuckDB table |
| **PostgreSQL** | DuckDB `ATTACH` — push-down SQL queries |
| **MySQL** | DuckDB `ATTACH` — push-down SQL queries |
| **SQLite** | DuckDB `ATTACH` — push-down SQL queries |

### 📈 17 Chart Types
| Category | Chart Types |
|----------|-------------|
| **Standard** | Bar, Line, Scatter, Pie, Area, Histogram |
| **Statistical** | Box, Violin, Heatmap |
| **Part-to-whole** | Sunburst, Funnel, Treemap |
| **Advanced ★** | **Waterfall, Gauge, Sankey, Parallel Coordinates, Candlestick** |

### 💬 Natural Language Interface
**Data Exploration:**
- *"What does this dataset contain? Give me a summary."*
- *"Show me the first 20 rows"*
- *"How many missing values are in each column?"*

**NL → SQL (RAG-Powered):**
- *"What were our top 5 products by revenue in Q4?"* → Generates SQL `SELECT p.name, SUM(s.revenue)...`
- *"Show me sales by region as a bar chart"* → Generates chart spec + SQL query
- *"Is there a correlation between advertising spend and revenue?"* → `SELECT CORR(ad_spend, revenue)`

**Dashboard Creation:**
- *"Build a complete dashboard for this data"*
- *"What KPIs should I track?"*
- *"Give me an executive summary"*

### 📝 Chart + SQL Viewer
Every chart card shows two tabs:
```
┌──────────────────────────────────────────────┐
│  [📊 Chart]  [📝 SQL]                        │
├──────────────────────────────────────────────┤
│                                              │
│  SELECT region, SUM(sales) AS _y             │
│  FROM sales_data                             │
│  GROUP BY region                             │
│  ORDER BY _y DESC                            │
│  LIMIT 5000                                  │
│                                              │
└──────────────────────────────────────────────┘
```

### 🔗 Cross-Filtering
Click a bar/point in one chart → all other charts update with `WHERE` clauses added to their SQL queries. Shift-click for compound selections.

### 🧮 Calculated Fields
Define new columns using SQL expressions:
- `profit_margin = (revenue - cost) / revenue * 100`
- `full_name = first_name || ' ' || last_name`
- `year = EXTRACT('year' FROM order_date)`

### 🔍 Auto-Insights (SQL-Powered)
| Insight | SQL Function |
|---------|-------------|
| Descriptive stats | `COUNT, AVG, STDDEV_SAMP, MIN, MAX, PERCENTILE_CONT` |
| Correlations | `CORR(col1, col2)` |
| Outliers | `PERCENTILE_CONT(0.25/0.75)` → IQR in SQL |
| Trends | `REGR_SLOPE(y, x)` |
| Seasonality | `DATE_TRUNC('month', date)` |

---

## 🚀 Quick Start

### Prerequisites
- **Python 3.10+**
- **Node.js 18+**
- **pip** / **npm**

### 1. Setup

```bash
git clone <repository-url>
cd instant-bi

# Create virtual environment & install dependencies
python -m venv venv
# Windows
venv\Scripts\activate
# macOS / Linux
# source venv/bin/activate

pip install -r requirements.txt
```

### 2. Configure API Keys

Copy `.env.example` to `.env` and add your LLM API keys (at least one required):

```env
GROQ_API_KEY=gsk-your-groq-key
OPENAI_API_KEY=sk-your-openai-key
ANTHROPIC_API_KEY=sk-ant-your-anthropic-key

# Ollama for local models (no API key needed)
# OLLAMA_BASE_URL=http://localhost:11434
# OLLAMA_DEFAULT_MODEL=llama3.1
```

### 3. Run the Application

```bash
# Terminal 1: FastAPI backend
uvicorn backend.main:app --reload --port 8000

# Terminal 2: React frontend (Vite dev server)
cd frontend
npm install
npm run dev
```

### Access Points
| Service | URL |
|---------|-----|
| **React Dashboard** | http://localhost:3000 |
| **FastAPI (API)** | http://localhost:8000 |
| **API Docs (Swagger)** | http://localhost:8000/docs |
| **Health Check** | http://localhost:8000/api/health |

> The Vite dev server proxies `/api/*` requests to the FastAPI backend at `localhost:8000`.

---

## 🧭 UI Navigation

| Section | Description |
|---------|-------------|
| **💬 Chat & Analyze** | Natural language → SQL queries against your data |
| **📊 Dashboard Builder** | Auto-generated dashboards with cross-filtering + SQL viewer |
| **💡 Auto Insights** | SQL-powered statistical analysis & KPI detection |
| **🗄️ Data Sources** | Upload files / manage database connections |
| **🎨 Chart Builder** | Custom visualization builder (17 chart types) with SQL sidebar |
| **⚙️ Settings** | LLM model selection & app configuration |

---

## 🔧 Tech Stack

| Layer | Technology |
|-------|-----------|
| **SQL Engine** | DuckDB — embedded OLAP, columnar, zero-config |
| **Frontend (Dashboard)** | React 19, TypeScript, Vite 8, Tailwind CSS v4, Plotly.js, Recharts |
| **Backend API** | FastAPI, Uvicorn |
| **LLM Integration** | Multi-Agent Router: OpenAI, Anthropic, Google Gemini, Groq, Ollama, DeepSeek, xAI, Together, OpenRouter, LiteLLM |
| **RAG Pipeline** | Schema indexing, semantic caching, few-shot retrieval, sample row context |
| **Data Processing** | DuckDB SQL (no pandas/scipy in hot path) |
| **Database** | DuckDB ATTACH — PostgreSQL, MySQL, SQLite |
| **File Parsing** | DuckDB read_csv_auto, pdfplumber, openpyxl |
| **Visualization** | Plotly + MCP Chart Bridge (8 open-source color themes: Tableau, ggplot2, Seaborn, Material, Retro, Viridis, Plasma, Monokai) |

---

## 📊 Performance

| Operation | pandas approach | SQL (DuckDB) approach |
|-----------|----------------|----------------------|
| Load 1M CSV rows | ~3s, 500MB RAM | ~0.5s, zero-copy |
| Aggregate by group | In-memory grouping | Vectorized GROUP BY |
| Filter on 5 columns | Create boolean mask | SQL WHERE + index |
| Join 2 datasets | pd.merge() in RAM | Hash join in DuckDB |
| Correlation matrix | All numeric cols in RAM | On-demand CORR() |
| 100 concurrent queries | Can't share DataFrame | DuckDB handles concurrently |

**10-100x more memory efficient** — only aggregated results are returned, not entire datasets.

---

## 📖 Example Use Cases

### Business Analytics
Load sales data and ask: *"What are the top 10 products by revenue? Show me trends over the last 6 months. Create a dashboard with profit margins and customer segments."*

### Data Investigation
Upload a CSV and query: *"What columns have the most missing data? Show me correlations between numeric columns. Generate a histogram for each key metric."*

### Report Generation
Connect to your database and request: *"Create a comprehensive executive summary with KPIs, trend analysis, and key insights for Q4 performance."*

### NL → SQL with RAG (Schema + 10 Rows Only)
*"What were our top 5 products by revenue in Q4?"*
→ System retrieves schema context + few-shot examples + **first 5 sample rows**
→ LLM reads only **schema + ~10 rows** (not the full dataset)
→ Multi-Agent Router picks the best model for SQL generation
→ LLM generates: `SELECT p.name, SUM(s.revenue) FROM sales s JOIN products p...`
→ DuckDB executes the SQL against the **full dataset** (millions of rows)
→ Returns only the aggregated result → Plotly renders with open-source color theme
→ You see both the chart AND the SQL query side-by-side

---

## ⚙️ Configuration

All configuration is managed through environment variables (see [.env.example](.env.example)):

| Variable | Default | Description |
|----------|---------|-------------|
| `GROQ_API_KEY` | — | Groq API key (fastest for queries) |
| `OPENAI_API_KEY` | — | OpenAI API key |
| `ANTHROPIC_API_KEY` | — | Anthropic API key |
| `GOOGLE_API_KEY` | — | Google Gemini API key |
| `OLLAMA_BASE_URL` | `http://localhost:11434` | Ollama server URL |
| `OLLAMA_DEFAULT_MODEL` | `llama3.1` | Default Ollama model |
| `APP_NAME` | `Instant BI` | Application display name |
| `MAX_UPLOAD_SIZE_MB` | `200` | Max file upload size |
| `CACHE_TTL_SECONDS` | `3600` | Cache expiry |

### 🤖 Multi-Agent LLM Routing

Route different LLM tasks to different models via environment variables:

| Variable | Default | Description |
|----------|---------|-------------|
| `LLM_TASK_SQLGEN` | — | Fast model for SQL generation (e.g. `groq:llama-3.3-70b-versatile`) |
| `LLM_TASK_CHART` | — | Model for chart recommendations (e.g. `openai:gpt-4o-mini`) |
| `LLM_TASK_RESPONSE` | — | Capable model for natural language response (e.g. `anthropic:claude-sonnet-4-6`) |
| `LLM_TASK_INSIGHT` | — | Model for deep analysis (e.g. `anthropic:claude-sonnet-4-6`) |
| `LLM_TASK_CHAT` | — | Fast model for general chat (e.g. `google:gemini-2.0-flash`) |

When not configured, falls back to the user's selected model in the UI.

---

## 🤝 Contributing

We welcome contributions! Please:
1. Report bugs via GitHub Issues
2. Suggest features through Discussions
3. Submit pull requests with tests
4. Follow existing code style & add documentation

---

## 📝 License

MIT License — Free for personal and commercial use.

---

<div align="center">
  <em>Built with ❤️ for data teams who want instant insights.</em>
</div>

---

*Version: 3.1.1 | Last Updated: July 16, 2026*
