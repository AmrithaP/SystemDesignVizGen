# SDVG — System Design Visual Generator

**SDVG (System Design Visual Generator)** is a project that aims to automatically generate **clear, visually appealing High-Level Design (HLD) and Low-Level Design (LLD) architecture diagrams** from simple text inputs.

The motivation is to make system design **easier to learn, understand, and visualize**, going beyond traditional tools like draw.io by producing structured, readable, and well-layered diagrams similar in quality to ByteByteGo-style visuals.

---

## 🚩 Problem Statement

Learning system design is hard because:
- Most explanations are text-heavy and scattered across blogs
- Existing diagrams are often cluttered, inconsistent, or manually drawn
- There is no automated way to convert *conceptual explanations* into *clean architecture visuals*

**SDVG solves this by converting system design knowledge into diagrams automatically.**

---

## 🎯 Goal (Level 1)

Given two inputs:
1. **Topic** (e.g., Uber, WhatsApp, URL Shortener)
2. **Design Level** (HLD or LLD)

Generate a **sensible system design architecture image** by:
- Discovering relevant system design articles
- Scraping and cleaning the content
- Extracting architectural components and relationships
- Rendering a clean architecture diagram

---

## 🧠 Current Status (Implemented)

### ✅ Step 1: Project Setup
- Python-based modular pipeline
- Virtual environment and dependency management

### ✅ Step 2: Intelligent Link Discovery
- Uses DuckDuckGo search
- Multiple targeted queries per topic
- Filters:
  - Video/social content
  - Templates/tools
  - Paywalled or noisy domains
- Ranks links based on relevance to system design

### ✅ Step 3: Robust Web Scraping & Normalization
For each discovered URL:
- Fetches HTML content
- Handles:
  - Lazy-loaded images
  - OpenGraph images
  - Blocked / 403 pages gracefully
- Extracts:
  - Clean article text (using Readability + BeautifulSoup)
  - Architecture-relevant images
- Scores pages based on diagram relevance

**Output:**  
Structured `PageContent` objects containing:
- Clean text
- Image references
- Diagram relevance score

---

## 🧱 Architecture (Current Pipeline)

User Input (Topic + HLD/LLD) -> Link Discovery (DuckDuckGo + Scoring) ->  Web Scraping & Cleaning  -> Normalized Content (Text + Images)


---

## 🔜 Next Steps

### 🚀 Step 4: Information Extraction (LLM)
- Convert scraped text into structured JSON:
  - Components (services, databases, caches, queues)
  - Relationships (data flow, request flow)
  - Logical grouping (client, backend, storage, async)

### 🎨 Step 5: Diagram Generation
- Convert extracted graph into:
  - Graphviz / Mermaid spec
- Apply consistent styling rules (colors, shapes, layers)

### 🖼 Step 6: Rendering
- Generate final diagram as SVG/PNG

### 🌐 Step 7: Minimal UI
- Local UI (Streamlit or simple web app)
- Inputs → Diagram output
- Later: deploy on AWS (EC2)

---

## 🛠 Tech Stack

- **Python**
- **DuckDuckGo Search (ddgs)**
- **Requests**
- **BeautifulSoup**
- **Readability-lxml**
- **Playwright (fallback for blocked sites)**
- *(Planned)* LLM API for extraction
- *(Planned)* Graphviz / Mermaid for rendering

---

## 🧪 How to Run (Current)

```bash
# activate venv
python test_scrape.py


