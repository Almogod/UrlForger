# UrlForge | Autonomous SEO Engine

UrlForge is a professional utility designed to identify, normalize, and repair URL structures for modern websites. It specializes in hardening SEO foundations by ensuring clean, consistent, and crawlable site architectures—especially for AI-generated or dynamically scaled platforms.

## Core Features

*   **Autonomous SEO Auditing**: Deep-scans site structures to identify "loopholes" such as broken internal links, malformed paths, and keyword gaps.
*   **Intelligent URL Normalization**: Automatically repairs malformed or inconsistent links (standardizing casing, trailing slashes, and removing redundant query parameters).
*   **Keyword-Driven Page Generation**: Analyzes competitor domains and search intent to generate new, high-ranking pages that fill specific content voids.
*   **Enterprise-Grade Crawling**: Features a high-concurrency crawler capable of scanning HTML as well as deep assets (CSS, JS, PDFs) to ensure site-wide integrity.
*   **Automated Deployment**: Seamlessly applies SEO fixes and pushes new generated content back to the host repository or site.

## How It Helps You

### 1. Hardening SEO Foundations
By enforcing strict URL normalization, UrlForge eliminates "duplicate content" issues caused by inconsistent link patterns (e.g., mixing `/page` and `/page/`). This ensures search engine bots prioritize your most important URLs.

### 2. Identifying Content Gaps
The engine doesn't just find errors; it finds opportunities. By comparing your site against competitors, it identifies high-value keywords you are missing and prepares optimized pages to target them.

### 3. Improving Crawl Efficiency
Broken links and deep-nested redirects waste "crawl budget." UrlForge identifies these bottlenecks, allowing you to fix them and ensure that bots can index your content faster and more effectively.

### 4. Cleaning AI-Generated Links
AI-generated content often produces inconsistent or "hallucinated" internal linking structures. UrlForge acts as a filter, validating and cleaning these links before they impact your site's reputation.

## Usage & Workflow

1.  **Initialize the Engine**:
    ```bash
    python -m uvicorn app:app --reload
    ```
2.  **Run Autonomous Analysis**: Input your site URL and competitor domains. Use the "Autonomous Plugin" to start a deep audit.
3.  **Review SEO Loopholes**: Inspect the identified broken links and malformed structures.
4.  **Approve & Deploy**: Select the recommended fixes and generated content to push them live to your site.

## Project Architecture

*   `app.py`: The central engine and API entry point.
*   `src/crawler_engine/`: Logic for high-concurrency site scanning.
*   `src/automation/`: Modules for SEO repair and content generation.
*   `static/`: Core performance-optimized assets.
*   `templates/`: The interactive audit dashboard.

---
*UrlForge - Optimizing site architecture for the age of AI.*
