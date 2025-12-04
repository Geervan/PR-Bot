from typing import Any, Dict, List
from app.agents.base import BaseAgent
from github import Github
from app.core.security import get_installation_access_token

class DiffAgent(BaseAgent):
    """Fetches and analyzes the PR diff."""

    async def run(self) -> Dict[str, Any]:
        """Fetches PR diff and returns structured changes."""
        print("DiffAgent: Fetching diff...")
        
        installation_id = self.context.get("installation_id")
        repo_full_name = self.context.get("repo", {}).get("full_name")
        pr_number = self.context.get("pr", {}).get("number")
        
        if not all([installation_id, repo_full_name, pr_number]):
            return {"error": "Missing context data"}

        try:
            token = get_installation_access_token(installation_id)
            g = Github(token)
            repo = g.get_repo(repo_full_name)
            pr = repo.get_pull(pr_number)
            
            files_changed = []
            for file in pr.get_files():
                files_changed.append({
                    "filename": file.filename,
                    "status": file.status,
                    "patch": file.patch,
                    "additions": file.additions,
                    "deletions": file.deletions
                })
            
            return {
                "files_changed": files_changed,
                "total_additions": pr.additions,
                "total_deletions": pr.deletions,
                "changed_files_count": pr.changed_files
            }
            
        except Exception as e:
            print(f"DiffAgent Error: {e}")
            return {"error": str(e)}
