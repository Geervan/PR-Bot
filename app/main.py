from fastapi import FastAPI, Request, HTTPException, BackgroundTasks
import hmac
import hashlib
from app.core.config import settings
from app.agents.master import master_agent
from app.core.indexer import CodebaseIndexer

app = FastAPI(title="AI PR Reviewer", description="AI-powered PR reviews with RAG")

def verify_signature(request: Request, body: bytes):
    """Verifies the GitHub webhook signature."""
    signature = request.headers.get("X-Hub-Signature-256")
    if not signature:
        raise HTTPException(status_code=403, detail="Missing signature")
    
    expected_signature = "sha256=" + hmac.new(
        settings.WEBHOOK_SECRET.encode(),
        body,
        hashlib.sha256
    ).hexdigest()
    
    if not hmac.compare_digest(signature, expected_signature):
        raise HTTPException(status_code=403, detail="Invalid signature")


async def index_repository(repo_full_name: str, installation_id: int):
    """Background task to index a repository."""
    print(f"Starting full index for {repo_full_name}...")
    try:
        indexer = CodebaseIndexer(repo_full_name, installation_id)
        stats = await indexer.index_full()
        print(f"Indexing complete for {repo_full_name}: {stats}")
    except Exception as e:
        print(f"Indexing failed for {repo_full_name}: {e}")


@app.post("/webhook")
async def webhook_handler(request: Request, background_tasks: BackgroundTasks):
    body = await request.body()
    verify_signature(request, body)
    
    payload = await request.json()
    event_type = request.headers.get("X-GitHub-Event")
    
    # Handle PR events
    if event_type == "pull_request":
        action = payload.get("action")
        if action in ["opened", "synchronize"]:
            background_tasks.add_task(master_agent.process_pr, payload)
            print(f"Received PR event: {action}")
            return {"status": "processing"}
    
    # Handle installation events (trigger initial indexing)
    elif event_type == "installation":
        action = payload.get("action")
        if action == "created":
            installation_id = payload.get("installation", {}).get("id")
            repositories = payload.get("repositories", [])
            
            for repo in repositories:
                repo_full_name = repo.get("full_name")
                if repo_full_name:
                    background_tasks.add_task(index_repository, repo_full_name, installation_id)
            
            return {"status": "indexing"}
    
    # Handle repository added to installation
    elif event_type == "installation_repositories":
        action = payload.get("action")
        if action == "added":
            installation_id = payload.get("installation", {}).get("id")
            repositories = payload.get("repositories_added", [])
            
            for repo in repositories:
                repo_full_name = repo.get("full_name")
                if repo_full_name:
                    background_tasks.add_task(index_repository, repo_full_name, installation_id)
            
            return {"status": "indexing"}
            
    return {"status": "ignored"}


@app.get("/")
def health_check():
    return {"status": "ok", "features": ["pr_review", "rag_indexing", "map_reduce"]}


@app.get("/stats/{owner}/{repo}")
async def get_index_stats(owner: str, repo: str):
    """Get indexing statistics for a repository."""
    from app.core.vector_store import get_vector_store
    
    repo_full_name = f"{owner}/{repo}"
    vector_store = get_vector_store(repo_full_name)
    stats = vector_store.get_stats()
    
    return stats

