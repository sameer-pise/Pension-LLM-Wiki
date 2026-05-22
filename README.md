# OHSERS LLM Wiki Prototype

An **embedding-free LLM Wiki prototype** for the OHSERS Active Members (Retirement focus). It crawls OHSERS webpages, stores them as Obsidian Markdown notes, cleans them, and answers queries using a local Ollama LLM.

## Quick Setup & Run

**1. Setup Environment**
```powershell
cd crawler
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
ollama pull llama3
```

**2. Configure Vault Path**
Ensure `vault_path` in `taxonomy.json` points to your `Obsidian/Vault` folder.

**3. Workflow Commands**
```powershell
# Step 1: Crawl pages and generate raw notes
python crawl.py

# Step 2: Clean raw notes into wiki-ready notes
python smart_clean_to_wiki.py

# Step 3: Ask questions using LLM
python ask-llm-wiki.py "How is pension calculated?"
```

## Key Features
- Maintains separate `raw/` and `wiki/` Markdown layers inside an Obsidian vault.
- Uses YAML frontmatter, keywords, and taxonomy mapping for note selection.
- **No embeddings or vector DBs** (ChromaDB, LangChain, LlamaIndex, etc.) are used.

## Status
- **Completed:** Retirement category setup and query flow.
- **Next Categories:** Service Credit, Disability Benefits, Survivor Benefits, Reemployment.
