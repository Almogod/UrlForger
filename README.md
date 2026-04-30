<div align="center">

# ⚡ UrlForge

### The Autonomous SEO Engine

**Crawl → Analyze → Fix → Generate → Deploy — Zero Human Intervention**

[![Live Demo](https://img.shields.io/badge/🚀_Live_Demo-urlforge--engine.onrender.com-0a0a0a?style=for-the-badge&labelColor=7c3aed)](https://urlforge-engine.onrender.com)
[![Python](https://img.shields.io/badge/Python-3.11+-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.100+-009688?style=for-the-badge&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![License](https://img.shields.io/badge/License-MIT-22c55e?style=for-the-badge)](LICENSE)

<br/>

> **UrlForge** is not just a site auditor — it's an end-to-end autonomous SEO engine that crawls your website, runs 20+ deep analysis modules, generates expert-grade content with AI, auto-fixes HTML issues, deploys changes to your hosting platform, and self-heals broken CI/CD pipelines. All from a single browser tab.

<br/>

[**Try It Live →**](https://urlforge-engine.onrender.com) · [Getting Started](#-getting-started) · [Features](#-feature-map) · [API Reference](#-api-reference) · [Architecture](#-architecture)

</div>

---

<br/>

## 🎯 The Problem

AI-generated websites are fast to build but technically fragile. Common issues silently destroy SEO:

| Problem | Impact |
|:---|:---|
| Broken internal links | Crawl budget wasted, user drop-off |
| Missing/duplicate meta tags | Poor SERP appearance, ranking penalties |
| No sitemap.xml | Pages never get indexed |
| Thin content, no FAQ schema | Zero chance at featured snippets |
| Missing Open Graph tags | Social shares look broken |
| No heading hierarchy | Search engines can't understand page structure |

**UrlForge automates the entire remediation pipeline** — from discovery to deployment — so you can ship AI-built sites that actually rank.

<br/>

---

## ✨ Feature Map

<table>
<tr>
<td width="50%">

### 🕷️ Intelligent Web Crawler
- **Playwright + Chromium** — renders JavaScript-heavy SPAs
- **Async worker pool** with configurable concurrency
- `robots.txt` compliance, same-domain enforcement
- Proxy, Basic Auth, and Bearer Token support
- GitHub repo–aware surgical filtering
- Real-time progress streaming to the UI

</td>
<td width="50%">

### 🧠 20+ SEO Analysis Modules
- Meta tags, heading hierarchy, image SEO
- Core Web Vitals estimation (LCP, FID, CLS)
- Page speed, Open Graph, mobile SEO
- Structured Data / JSON-LD validation
- Hreflang verification, broken link probing
- Keyword gap analysis, content quality scoring
- Canonical tag validation, crawl budget analysis
- Internal link structure, robots.txt auditing

</td>
</tr>
<tr>
<td width="50%">

### 🤖 AI Content Engine
- **Provider-Agnostic** — OpenAI, Gemini, OpenRouter, Ollama (local)
- **Cascading fallback chain** — never fails silently
- PMI-scored phrase extraction (not dumb keyword stuffing)
- Competitor gap analysis with LSI term discovery
- Expert FAQ generation with anti-AI-trope filters
- Full page generation: Hero → Sections → FAQs → Schema
- HTML + React JSX output, ready to deploy

</td>
<td width="50%">

### 🏢 Business Intelligence Engine
- **Full-site DNA discovery** — crawls strategic pages
- Extracts services, technologies, brand voice, audience
- Generates deep strategic brand audit reports
- Heuristic fallback when no LLM is available
- Anti-generic validation (rejects "Professional Services")
- All AI content is grounded in real site data

</td>
</tr>
<tr>
<td width="50%">

### 🚀 Multi-Platform Deployment
- **GitHub** — commits directly via API
- **Vercel** — batch deployment via Deployments API
- **Hostinger** — SFTP upload via Paramiko
- **FTP** — standard ftplib upload
- **Webhook** — POST to any endpoint
- **Filesystem** — local output for testing

</td>
<td width="50%">

### 🔄 Self-Healing CI/CD
- Monitors GitHub Actions after deployment
- Pulls failed workflow logs automatically
- Feeds logs + deployed code to LLM fixer
- Redeploys corrected files autonomously
- Loops until CI/CD goes green (configurable retries)
- Zero-human-in-the-loop error recovery

</td>
</tr>
<tr>
<td width="50%">

### 📊 Google Search Console Integration
- URL Inspection API — check indexing status
- Search Analytics — clicks, impressions, CTR, position
- Google Indexing API — submit URLs for re-crawling
- Color-coded Excel reports (indexed vs. unindexed)
- Sitemap gap analysis — find orphaned pages

</td>
<td width="50%">

### 🛡️ Enterprise-Grade Security
- Security headers on every response (CSP, HSTS, X-Frame)
- Per-IP rate limiting via slowapi
- CORS with configurable allowed origins
- Path traversal protection (`is_safe_path()`)
- URL safety validation (`is_safe_url()`)
- Audit logging to `audit.log`
- Enterprise mode — Swagger/errors hidden

</td>
</tr>
</table>

<br/>

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                        Browser UI (Jinja2)                         │
│            Real-time status · Tabbed results · Dark mode           │
└──────────────────────────────┬──────────────────────────────────────┘
                               │
┌──────────────────────────────▼──────────────────────────────────────┐
│                     FastAPI Application (app.py)                    │
│                                                                     │
│  ┌──────────────┐  ┌──────────────┐  ┌────────────┐  ┌──────────┐ │
│  │ router_crawl │  │ router_plugin│  │ router_tasks│  │router_gsc│ │
│  └──────┬───────┘  └──────┬───────┘  └──────┬─────┘  └────┬─────┘ │
└─────────┼─────────────────┼─────────────────┼──────────────┼───────┘
          │                 │                 │              │
┌─────────▼─────────────────▼─────────────────▼──────────────▼───────┐
│                         Core Services                               │
│                                                                     │
│  ┌─────────────────┐  ┌──────────────┐  ┌────────────────────────┐ │
│  │  Crawler Engine  │  │  SEO Engine   │  │   Content Engine       │ │
│  │  ─────────────── │  │  ──────────── │  │   ─────────────────── │ │
│  │  • scheduler.py  │  │  • 20 modules │  │  • page_generator.py  │ │
│  │  • fetcher.py    │  │  • seo_score  │  │  • faq_generator.py   │ │
│  │  • frontier.py   │  │  • fix_exec   │  │  • competitor_analyzer│ │
│  │  • js_crawler.py │  │  • html_rewr  │  │  • phrase_extractor   │ │
│  │  • parser.py     │  │  • audit.py   │  │  • site_analysis_svc  │ │
│  └─────────────────┘  └──────────────┘  └────────────────────────┘ │
│                                                                     │
│  ┌─────────────────┐  ┌──────────────┐  ┌────────────────────────┐ │
│  │    Deployer      │  │  LLM Resolver │  │  GitHub Monitor        │ │
│  │  ─────────────── │  │  ──────────── │  │  ─────────────────── │ │
│  │  GitHub · Vercel │  │  OpenAI       │  │  Workflow polling     │ │
│  │  FTP · Hostinger │  │  Gemini       │  │  Log extraction       │ │
│  │  Webhook · Local │  │  OpenRouter   │  │  LLM-powered fixes    │ │
│  │                  │  │  Ollama       │  │  Auto-redeploy        │ │
│  └─────────────────┘  └──────────────┘  └────────────────────────┘ │
│                                                                     │
│  ┌──────────────────────────────────────────────────────────────┐  │
│  │                      Infrastructure                          │  │
│  │  Rate Limiting · Security Headers · Sentry · Prometheus      │  │
│  │  CORS · SQLAlchemy + Alembic · Redis (or in-memory)          │  │
│  └──────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────┘
```

<br/>

---

## 🚀 Getting Started

### Try It Online

The fastest way to experience UrlForge — no installation required:

> **🌐 [https://urlforge-engine.onrender.com](https://urlforge-engine.onrender.com)**

Just paste a URL and hit **Crawl**. Results appear in real-time.

---

### Local Development

```bash
# Clone the repository
git clone https://github.com/Almogod/UrlForger.git
cd UrlForger

# Create a virtual environment
python -m venv .venv

# Activate it
# Windows:
.venv\Scripts\activate
# macOS/Linux:
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt
playwright install chromium

# Start the server
uvicorn app:app --reload --port 8000
```

Visit **[http://localhost:8000](http://localhost:8000)** — the dashboard is ready.

---

### Docker

```bash
# Build
docker build -t urlforge:latest .

# Run
docker run -p 8000:8000 \
  -e APP_ENV=production \
  -e REDIS_URL=redis://redis:6379/0 \
  -e ALLOWED_ORIGINS=https://yourdomain.com \
  urlforge:latest
```

> The Dockerfile uses a **multi-stage build**: Stage 1 installs dependencies, Stage 2 is a lean runtime image with Playwright's Chromium and all required system libraries pre-installed, running uvicorn with 4 workers.

---

### One-Click Deploy to Render

The repo includes a `render.yaml` blueprint. Connect your GitHub repo to Render and it auto-deploys.

<br/>

---

## 📡 API Reference

### Core Endpoints

| Method | Endpoint | Description |
|:---|:---|:---|
| `GET` | `/` | Dashboard — input form + results UI |
| `GET` | `/health` | Health check (uptime, timestamp) |
| `GET` | `/results?task_id=` | Tabbed results dashboard |
| `GET` | `/metrics` | Prometheus metrics |

### Crawl & Audit

| Method | Endpoint | Description |
|:---|:---|:---|
| `POST` | `/crawl/start` | Start a crawl + full SEO audit |
| `GET` | `/crawl/result/{task_id}` | Fetch completed crawl result |
| `GET` | `/tasks/{task_id}/status` | Poll task state |

### Plugin System (Approval-Gated Workflow)

| Method | Endpoint | Description |
|:---|:---|:---|
| `POST` | `/plugin/run` | Start full pipeline (crawl → analyze → generate) |
| `POST` | `/plugin/approve` | Approve fixes + deploy to target platform |
| `GET` | `/plugin/download_report` | Download PDF SEO report |
| `POST` | `/plugin/generate_content` | Generate content for a specific keyword |
| `POST` | `/plugin/update_content` | Update generated page content |
| `POST` | `/plugin/update_faq` | Edit a specific FAQ entry |
| `POST` | `/plugin/delete_faq` | Remove a FAQ entry |

### Google Search Console

| Method | Endpoint | Description |
|:---|:---|:---|
| `POST` | `/gsc/inspect` | URL Inspection API |
| `POST` | `/gsc/submit` | Submit URL for indexing |

**Task lifecycle:** `pending` → `In Progress` → `complete` / `error`

<br/>

---

## 🔬 SEO Analysis Modules

UrlForge runs **20 independent analysis modules** on every crawled page. Each module returns issues, a weighted score contribution, and actionable fix suggestions.

<table>
<tr><th>Module</th><th>What It Analyzes</th></tr>
<tr><td><code>meta</code></td><td><code>&lt;title&gt;</code> and <code>&lt;meta description&gt;</code> — presence, length, uniqueness, keyword placement</td></tr>
<tr><td><code>heading_structure</code></td><td>Single <code>&lt;h1&gt;</code>, logical H1→H2→H3 cascade, keyword in H1</td></tr>
<tr><td><code>image_seo</code></td><td><code>alt</code> attribute presence and quality, lazy loading, image dimensions</td></tr>
<tr><td><code>core_web_vitals</code></td><td>Estimated LCP, FID, CLS from page weight and render-blocking signals</td></tr>
<tr><td><code>page_speed</code></td><td>Script/stylesheet count, total page weight, unminified resources, preload hints</td></tr>
<tr><td><code>open_graph</code></td><td><code>og:title</code>, <code>og:description</code>, <code>og:image</code>, <code>og:url</code> completeness</td></tr>
<tr><td><code>content_quality</code></td><td>Word count, thin content detection, keyword density, duplicate paragraphs</td></tr>
<tr><td><code>mobile_seo</code></td><td>Viewport meta tag, touch-target size, font legibility</td></tr>
<tr><td><code>page_experience</code></td><td>HTTPS enforcement, intrusive interstitial detection, mixed content</td></tr>
<tr><td><code>structured_data_validator</code></td><td>JSON-LD / Microdata presence, required fields per schema type, FAQ schema injection</td></tr>
<tr><td><code>hreflang</code></td><td>Language tag correctness, return-link verification</td></tr>
<tr><td><code>broken_links</code></td><td>Internal link probing — 404s, redirect loops, broken <code>#anchor</code> targets</td></tr>
<tr><td><code>keyword_gap</code></td><td>Site-wide keyword extraction, cross-page coverage mapping, competitor comparison</td></tr>
<tr><td><code>canonical_advanced</code></td><td>Canonical tag validation, self-referencing checks, pagination hints</td></tr>
<tr><td><code>crawl_budget</code></td><td>Crawl efficiency analysis, wasted budget detection</td></tr>
<tr><td><code>internal_links</code></td><td>Internal link graph structure, orphan page detection</td></tr>
<tr><td><code>robots</code></td><td><code>robots.txt</code> directives validation, crawl rule conflicts</td></tr>
<tr><td><code>schema</code></td><td>Schema.org markup generation (Organization, Article, FAQ)</td></tr>
<tr><td><code>sitemap</code></td><td>Sitemap.xml generation with priority by path depth</td></tr>
<tr><td><code>hardcode_fixer</code></td><td>Regex-based pattern detection for hardcoded values</td></tr>
</table>

<br/>

---

## 🤖 AI Provider Configuration

UrlForge supports **four LLM providers** with automatic cascading fallback. If the primary provider fails, the engine seamlessly tries the next one.

```
OpenAI → Gemini → OpenRouter → Ollama (local)
```

### Provider Setup

| Provider | Required Config | Notes |
|:---|:---|:---|
| **OpenAI** | `OPENAI_API_KEY` | GPT-4o-mini default, configurable model |
| **Gemini** | `GEMINI_API_KEY` | Auto-retries with exponential backoff on 429s |
| **OpenRouter** | `OPENROUTER_API_KEY` | Access 100+ models via unified API |
| **Ollama** | `OLLAMA_HOST` (default: `localhost:11434`) | Fully local, zero API cost, full privacy |

> **No API key? No problem.** UrlForge includes a **heuristic fallback** that uses TF-IDF keyword extraction, PMI-scored phrase analysis, and template-based content synthesis to generate useful output without any LLM.

<br/>

---

## ⚙️ Environment Variables

| Variable | Default | Description |
|:---|:---|:---|
| `APP_ENV` | `enterprise` | `development`, `production`, or `enterprise` for hardened mode |
| `OPENAI_API_KEY` | — | OpenAI API key for content generation |
| `GEMINI_API_KEY` | — | Google Gemini API key |
| `OPENROUTER_API_KEY` | — | OpenRouter API key |
| `OLLAMA_HOST` | `http://localhost:11434` | Ollama server URL |
| `SENTRY_DSN` | — | Sentry DSN — leave unset to disable error tracking |
| `ALLOWED_ORIGINS` | `*` | Comma-separated allowed CORS origins |
| `REDIS_URL` | `redis://localhost:6379/0` | Redis URL for multi-worker task state |
| `DATABASE_URL` | `sqlite:///./database.db` | SQLAlchemy database connection string |
| `GITHUB_TOKEN` | — | GitHub Personal Access Token for deployment |
| `GITHUB_REPO` | `user/repo` | Target repository for GitHub deployment |
| `GITHUB_BRANCH` | `main` | Target branch |
| `GOOGLE_APPLICATION_CREDENTIALS` | — | Path to Google service account JSON |
| `CRAWL_TIMEOUT` | `30` | HTTP request timeout per page (seconds) |
| `CRAWLER_PROXY` | — | Proxy URL for crawl requests |

<br/>

---

## 🗂️ Repository Structure

```
UrlForge/
├── app.py                          # FastAPI application entry point
├── Dockerfile                      # Multi-stage production build
├── render.yaml                     # Render.com deployment blueprint
├── requirements.txt                # Python dependencies
├── robots.txt                      # Crawler directives
│
├── src/
│   ├── api/                        # API route handlers
│   │   ├── router_crawl.py         #   Crawl + audit endpoints
│   │   ├── router_plugin.py        #   Plugin workflow (run → approve → deploy)
│   │   ├── router_tasks.py         #   Task status polling
│   │   └── router_gsc.py           #   Google Search Console integration
│   │
│   ├── crawler_engine/             # Web crawling infrastructure
│   │   ├── scheduler.py            #   Async worker pool orchestrator
│   │   ├── fetcher.py              #   HTTP page fetcher
│   │   ├── frontier.py             #   URL frontier with dedup + priority
│   │   ├── parser.py               #   HTML link/meta/heading extractor
│   │   ├── js_crawler.py           #   Playwright-based JS rendering
│   │   └── graph.py                #   Internal link graph builder
│   │
│   ├── modules/                    # 20 independent SEO analysis modules
│   │   ├── meta.py                 ├── heading_structure.py
│   │   ├── image_seo.py            ├── core_web_vitals.py
│   │   ├── page_speed.py           ├── open_graph.py
│   │   ├── content_quality.py      ├── mobile_seo.py
│   │   ├── page_experience.py      ├── structured_data_validator.py
│   │   ├── hreflang.py             ├── broken_links.py
│   │   ├── keyword_gap.py          ├── canonical_advanced.py
│   │   ├── crawl_budget.py         ├── internal_links.py
│   │   ├── robots.py               ├── schema.py
│   │   ├── sitemap.py              └── hardcode_fixer.py
│   │
│   ├── content/                    # AI content generation pipeline
│   │   ├── engine.py               #   Content orchestrator + keyword discovery
│   │   ├── page_generator.py       #   Full page synthesis (LLM + DNA fallback)
│   │   ├── faq_generator.py        #   Expert FAQ generation
│   │   ├── competitor_analyzer.py  #   Competitor scraping + content brief
│   │   ├── phrase_extractor.py     #   PMI-scored collocation extraction
│   │   └── stopwords.py            #   1200+ curated stopwords
│   │
│   ├── engine/                     # Fix execution pipeline
│   │   ├── fix_executor.py         #   Translates audit → concrete HTML fixes
│   │   ├── fix_strategy.py         #   Module priority ordering
│   │   ├── planner.py              #   Fix planning logic
│   │   └── registry.py             #   Module registry
│   │
│   ├── services/                   # Core business services
│   │   ├── site_analysis_service.py#   Business intelligence synthesizer
│   │   ├── deployer.py             #   6-platform deployment engine
│   │   ├── github_monitor.py       #   CI/CD self-healing loop
│   │   ├── llm_fixer.py            #   LLM-powered code repair
│   │   ├── html_rewriter.py        #   DOM-level HTML fix application
│   │   ├── gsc_service.py          #   Google Search Console client
│   │   ├── seo_score.py            #   Weighted SEO score calculator
│   │   └── task_store.py           #   Task state management (Redis/memory)
│   │
│   ├── utils/                      # Shared utilities
│   │   ├── llm_resolver.py         #   Cascading provider fallback chain
│   │   ├── security.py             #   Path/URL safety validation
│   │   ├── logger.py               #   Structured logging (JSON/text)
│   │   ├── pdf_generator.py        #   SEO report PDF generation
│   │   └── framework_detector.py   #   Frontend framework detection
│   │
│   └── config.py                   # Pydantic settings (env-based)
│
├── templates/
│   └── index.html                  # Single-page Jinja2 dashboard
│
├── static/                         # CSS, JS, images
└── .github/workflows/ci.yml       # GitHub Actions CI pipeline
```

<br/>

---

## 💡 Use Cases

### 🔍 Full-Site SEO Audit
Submit any URL. UrlForge crawls the entire site, runs 20+ modules, and presents a scored results dashboard with per-module issues and prioritized actions. Download the generated `sitemap.xml` and PDF report.

### 🤖 AI-Powered Content Generation
The engine discovers keyword gaps, analyzes competitors, generates expert-grade pages (with FAQs, structured data, hero sections), and renders them as HTML or React components — all grounded in your site's actual brand DNA.

### 🚀 Automated Deployment Pipeline
Approve generated content → it gets committed to GitHub → CI/CD runs → if it fails, the engine reads the logs, asks an LLM to fix the code, redeploys, and loops until it passes. Fully autonomous.

### 📊 Continuous SEO Monitoring
Call `POST /crawl/start` from a cron job after each deployment to maintain a fresh, validated sitemap and catch regressions before they affect rankings.

### 🔗 CMS / Agency Plugin Workflow
Submit proposed changes via `POST /plugin/run`, review the before/after SEO score comparison, approve or reject individual fixes, then deploy — perfect for client review workflows.

<br/>

---

## 🧪 Tech Stack

| Layer | Technology |
|:---|:---|
| **Framework** | FastAPI + Uvicorn (ASGI) |
| **Templating** | Jinja2 |
| **Browser Automation** | Playwright (Chromium) |
| **HTML Parsing** | BeautifulSoup4 + lxml |
| **LLM Providers** | OpenAI · Gemini · OpenRouter · Ollama |
| **Rate Limiting** | slowapi |
| **Metrics** | prometheus-fastapi-instrumentator |
| **Error Tracking** | Sentry SDK |
| **Task Persistence** | Redis (or in-memory fallback) |
| **Data Validation** | Pydantic v2 |
| **Configuration** | pydantic-settings (.env) |
| **Database** | SQLAlchemy + Alembic |
| **Deployment** | Docker (multi-stage) · Render |
| **CI/CD** | GitHub Actions |
| **GSC Integration** | Google APIs (Search Console + Indexing) |
| **Testing** | pytest |

<br/>

---

<div align="center">

### Built for developers who ship AI-powered sites that actually rank.

**[Try UrlForge Live →](https://urlforge-engine.onrender.com)**

<br/>

⭐ **Star this repo** if UrlForge saves you time. It helps others find it.

</div>
