# HR & Onboarding AI Assistant (OpenAI Edition)

A RAG-powered chat assistant that answers employee questions about company
policies, benefits, and onboarding, grounded in the company's own HR documents.

**Stack:** Streamlit (UI) + OpenAI `gpt-4o` (chat) + Chroma (vector DB) +
sentence-transformers (free local embeddings).

---

## Step 1: Prerequisites

- Python 3.10 or newer (`python --version`)
- Git (`git --version`)
- VS Code with the **Python** extension
- An OpenAI API key with billing enabled: https://platform.openai.com/api-keys

---

## Step 2: Create the project and initialize Git

```bash
mkdir hr-onboarding-assistant
cd hr-onboarding-assistant
git init
git branch -M main
code .
```

Copy all the project files into this folder (or unzip the download here).

---

## Step 3: Create and activate a virtual environment

**Windows (PowerShell):**
```powershell
python -m venv venv
venv\Scripts\Activate.ps1
```
If PowerShell blocks the script, run once:
`Set-ExecutionPolicy -Scope CurrentUser RemoteSigned`

**macOS / Linux:**
```bash
python3 -m venv venv
source venv/bin/activate
```

Then in VS Code: `Ctrl+Shift+P` (`Cmd+Shift+P` on Mac) -> **Python: Select
Interpreter** -> pick the one inside `venv`. You should see `(venv)` at the
start of your terminal prompt.

---

## Step 4: Install dependencies

```bash
python -m pip install --upgrade pip
pip install -r requirements.txt
```

This installs Streamlit, the OpenAI SDK, LangChain, Chroma, local embeddings,
PDF support, and python-dotenv. The first install can take a few minutes.

---

## Step 5: Add your OpenAI key

```bash
# macOS / Linux
cp .env.example .env
# Windows
copy .env.example .env
```

Open `.env` and fill it in:

```dotenv
OPENAI_API_KEY=sk-your-real-key-here
OPENAI_MODEL=gpt-4o
```

`.env` is in `.gitignore`, so it will never be pushed to GitHub.

---

## Step 6: Run the app

```bash
streamlit run app.py
```

Open http://localhost:8501. On first run it downloads the embedding model
(~90 MB, one time) and builds the vector index from `data/sample_hr_policy.txt`.

**Try these questions:**
- How many PTO days do I get per year?
- What do I need to do in my first two weeks?
- How much of my health insurance does the company pay?
- I'm being harassed by a coworker (it should route you to a human)

---

## Step 7: Commit and push to GitHub

Create an empty repo on github.com first (no README), then:

```bash
git add .
git commit -m "Initial commit: HR onboarding assistant (OpenAI)"
git remote add origin https://github.com/<your-username>/hr-onboarding-assistant.git
git push -u origin main
```

Before pushing, run `git status` and confirm `.env` and `venv/` are NOT listed.

---

## Project structure

```
hr-onboarding-assistant/
├── app.py                     # Streamlit chat UI (entry point)
├── requirements.txt
├── .env.example               # Template: OPENAI_API_KEY, OPENAI_MODEL
├── .gitignore
├── .streamlit/config.toml     # Brand colors / theme
├── data/
│   └── sample_hr_policy.txt   # Replace with a real handbook (.pdf or .txt)
└── src/
    ├── system_prompt.py       # HR persona, tone, guardrails
    └── rag_engine.py          # Load -> chunk -> embed -> store -> retrieve
```

---

## How the RAG pipeline works

1. `rag_engine.py` loads every `.pdf` and `.txt` file in `data/`.
2. Text is split into ~800-character overlapping chunks.
3. Chunks are embedded locally with `all-MiniLM-L6-v2` (free, no API calls).
4. Embeddings are stored in a persistent Chroma DB in `./chroma_db/`.
5. For each question, the top 4 chunks are retrieved and sent to GPT-4o with
   the system prompt, so answers come from the company's documents.

**Using your own documents:** drop PDFs/TXT files into `data/`, then click
**Rebuild knowledge base** in the sidebar (or delete `chroma_db/` and restart).

---

## Customizing

| What | Where |
|---|---|
| Company name | `COMPANY_NAME` in `src/system_prompt.py` |
| AI persona / tone / rules | `SYSTEM_PROMPT` in `src/system_prompt.py` |
| Model (e.g. `gpt-4o-mini` for cheaper) | `OPENAI_MODEL` in `.env` |
| Chunk size / number of retrieved chunks | `CHUNK_SIZE`, `TOP_K` in `src/rag_engine.py` |
| Brand colors | `.streamlit/config.toml` |

---

## Troubleshooting

| Problem | Fix |
|---|---|
| "No OPENAI_API_KEY found" | Check `.env` exists (not `.env.example`) and restart Streamlit |
| `AuthenticationError` / 401 | Key is wrong or revoked; create a new one |
| `RateLimitError` / 429 or quota error | Add billing/credits in your OpenAI account |
| `ModuleNotFoundError` | The venv isn't active; activate it and rerun `pip install -r requirements.txt` |
| Old answers after changing documents | Click **Rebuild knowledge base** |
| Slow first start | Embedding model is downloading; it's cached afterwards |

---

## Making it sellable (next steps)

- **Multi-tenant isolation:** separate `data/` and `chroma_db/` per client.
- **Auth:** add a login (e.g. `streamlit-authenticator`) before real employee data.
- **Admin upload UI:** let HR upload policy PDFs from the browser.
- **Audit logging:** log questions (without sensitive PII) for HR insights.
- **Deployment:** Docker on the client's infrastructure so HR data stays with them.
- **Data privacy:** questions and retrieved policy text are sent to OpenAI; disclose
  this to clients and check their data-processing requirements.
- Have the client's HR/legal team review policy wording before employees use it.
