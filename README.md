# AI-Powered PR Reviewer

A GitHub App that uses a multi-agent architecture to review Pull Requests with cross-file reasoning and codebase memory.

## 🌟 What Makes This Different

Unlike other AI reviewers that only see the diff, this bot **understands your entire codebase**:
- Indexes your repo on installation
- Finds related code across files you didn't change
- Learns patterns from your codebase
- Self-hosted = your code never leaves your infrastructure

## Features
- **🚫 Block Bad PRs**: High-risk PRs get a failing status check (can't merge!)
- **🔧 Auto-Fix Suggestions**: AI generates code fixes for issues found
- **🌐 Multi-Language**: Python, JavaScript/TypeScript, Java, C/C++, Go, Rust
- **🧠 RAG Context**: Indexes your codebase for smarter reviews
- **📊 Map-Reduce**: Handles large PRs by summarizing files individually
- **🌳 Tree-sitter**: Parses code structure (functions, classes, imports)
- **🔗 Cross-File Impact**: Identifies files affected by your changes
- **🔑 Multi-Key Manager**: Rotates Gemini API keys with rate-limit handling
- **⚠️ Risk Scoring**: Assigns risk based on size, tests, and impact

## Setup

1. **Install Dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

2. **Configure Environment**:
   Copy `.env.example` to `.env` and fill in:
   - `APP_ID`: Your GitHub App ID
   - `PRIVATE_KEY_PATH`: Path to your GitHub App private key
   - `WEBHOOK_SECRET`: Your webhook secret
   - `GEMINI_API_KEYS`: Comma-separated list of Gemini API keys

3. **Run the Server**:
   ```bash
   uvicorn app.main:app --reload
   ```

## How It Works

### On GitHub App Installation
1. Receives `installation` webhook
2. Indexes entire repository in background
3. Stores embeddings in local vector store

### On Pull Request
1. **Status: Pending** → Shows "AI review in progress"
2. **Diff Analysis** → Fetch changed files
3. **Tree-sitter** → Parse code structure (7 languages)
4. **Map** → Summarize each file
5. **RAG** → Find related code in codebase
6. **Risk** → Calculate risk score (0-100)
7. **Reduce** → Generate final review
8. **Auto-Fix** → Generate code suggestions if issues found
9. **Status: Pass/Fail** → Block merge if risk ≥ 70

## Architecture
```
app/
├── main.py                  # FastAPI + webhooks
├── core/
│   ├── config.py            # Settings
│   ├── security.py          # GitHub App JWT auth
│   ├── llm.py               # Gemini client
│   ├── key_manager.py       # Multi-key rotation
│   ├── embeddings.py        # Gemini embeddings
│   ├── vector_store.py      # ChromaDB wrapper
│   ├── indexer.py           # Codebase indexer
│   └── code_parser.py       # Tree-sitter parser
└── agents/
    ├── master.py            # Orchestrator
    ├── diff.py              # PR diff analysis
    ├── dependency.py        # Cross-file dependencies
    ├── file_summary.py      # File summarizer (MAP)
    ├── context.py           # RAG context retrieval
    ├── test.py              # Test impact
    ├── risk.py              # Risk scoring
    └── writer.py            # Review composer (REDUCE)
```

## API Endpoints

| Endpoint | Description |
|----------|-------------|
| `POST /webhook` | GitHub webhook handler |
| `GET /` | Health check |
| `GET /stats/{owner}/{repo}` | Index statistics |

## Configuration

| Variable | Description |
|----------|-------------|
| `APP_ID` | GitHub App ID |
| `PRIVATE_KEY_PATH` | Path to private key file |
| `WEBHOOK_SECRET` | Webhook signature secret |
| `GEMINI_API_KEYS` | Comma-separated API keys |

## License
MIT
