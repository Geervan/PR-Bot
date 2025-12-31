from typing import Dict, Any, List, Optional
from app.agents.base import BaseAgent
from app.agents.diff import DiffAgent
from app.agents.dependency import DependencyAgent
from app.agents.test import TestAgent
from app.agents.risk import RiskAgent
from app.agents.file_summary import FileSummaryAgent
from app.agents.context import ContextAgent
from app.agents.writer import ReviewWriterAgent
from app.core.security import get_installation_access_token
from app.core.indexer import CodebaseIndexer
from app.core.llm import llm_client
from github import Github


# Risk threshold for blocking PRs
BLOCK_THRESHOLD = 70  # PRs with risk score >= 70 will be blocked


class MasterAgent(BaseAgent):
    """Orchestrates the PR review process using Map-Reduce + RAG strategy."""

    async def process_pr(self, payload: Dict[str, Any]):
        """Main entry point for processing a PR."""
        print("MasterAgent: Processing PR...")
        
        # 1. Extract PR info
        pr_data = payload.get("pull_request")
        if not pr_data:
            return
        
        repo_data = payload.get("repository")
        installation_id = payload.get("installation", {}).get("id")
        head_sha = pr_data.get("head", {}).get("sha")  # For status checks
        
        context = {
            "pr": pr_data,
            "repo": repo_data,
            "installation_id": installation_id,
            "head_sha": head_sha
        }

        # Set initial pending status
        await self._post_status_check(
            context, 
            state="pending", 
            description="AI review in progress..."
        )

        # 2. Run Diff Agent
        print("MasterAgent: Step 1/7 - Fetching diff...")
        diff_agent = DiffAgent(context)
        diff_result = await diff_agent.run()
        if "error" in diff_result:
            print(f"Aborting: {diff_result['error']}")
            await self._post_status_check(
                context,
                state="error",
                description=f"Failed: {diff_result['error']}"
            )
            return
        
        context["diff_data"] = diff_result
        
        # 3. Run Dependency Agent (Tree-sitter analysis)
        print("MasterAgent: Step 2/7 - Analyzing dependencies (Tree-sitter)...")
        dep_agent = DependencyAgent(context)
        dep_result = await dep_agent.run()
        context["dependency_data"] = dep_result
        
        # 4. Run File Summary Agent (MAP step)
        print("MasterAgent: Step 3/7 - Summarizing files (Map)...")
        summary_agent = FileSummaryAgent(context)
        summary_result = await summary_agent.run()
        context["file_summary_data"] = summary_result
        
        # 5. Run Context Agent (RAG)
        print("MasterAgent: Step 4/7 - Retrieving codebase context (RAG)...")
        context_agent = ContextAgent(context)
        context_result = await context_agent.run()
        context["rag_context"] = context_result
        
        # 6. Run Test Agent
        print("MasterAgent: Step 5/7 - Analyzing test impact...")
        test_agent = TestAgent(context)
        test_result = await test_agent.run()
        context["test_data"] = test_result
        
        # 7. Run Risk Agent
        print("MasterAgent: Step 6/7 - Calculating risk...")
        risk_agent = RiskAgent(context)
        risk_result = await risk_agent.run()
        context["risk_data"] = risk_result
        
        # 8. Run Review Writer Agent (REDUCE step)
        print("MasterAgent: Step 7/7 - Writing review (Reduce)...")
        writer_agent = ReviewWriterAgent(context)
        review_comment = await writer_agent.run()
        
        # 9. Generate auto-fix suggestions if there are issues
        auto_fix = await self._generate_auto_fix(context)
        if auto_fix:
            review_comment += f"\n\n---\n\n## 🔧 Suggested Fix\n\n{auto_fix}"
        
        # 10. Post Review
        await self._post_review(context, review_comment)
        
        # 11. Post Status Check (pass/fail based on risk)
        risk_score = risk_result.get("score", 0)
        if risk_score >= BLOCK_THRESHOLD:
            await self._post_status_check(
                context,
                state="failure",
                description=f"High risk PR (score: {risk_score}/100). Please address concerns."
            )
        else:
            await self._post_status_check(
                context,
                state="success",
                description=f"AI review passed (risk: {risk_score}/100)"
            )
        
        # 12. Update index with changed files (incremental)
        await self._update_index(context)
        
        print("MasterAgent: PR processing complete.")
    
    async def _post_status_check(
        self, 
        context: Dict[str, Any], 
        state: str, 
        description: str
    ):
        """
        Posts a commit status check to GitHub.
        
        States: pending, success, failure, error
        """
        try:
            installation_id = context.get("installation_id")
            repo_full_name = context.get("repo", {}).get("full_name")
            sha = context.get("head_sha")
            
            if not sha:
                print("No SHA available for status check")
                return
            
            token = get_installation_access_token(installation_id)
            g = Github(token)
            repo = g.get_repo(repo_full_name)
            
            # Create commit status
            repo.get_commit(sha).create_status(
                state=state,
                target_url="",  # Could link to a dashboard
                description=description[:140],  # GitHub limit
                context="AI PR Reviewer"
            )
            print(f"Status check posted: {state}")
            
        except Exception as e:
            print(f"Failed to post status check: {e}")
    
    async def _generate_auto_fix(self, context: Dict[str, Any]) -> Optional[str]:
        """
        Generates auto-fix suggestions for common issues.
        Returns markdown with suggested fixes.
        """
        risk_data = context.get("risk_data", {})
        test_data = context.get("test_data", {})
        file_summaries = context.get("file_summary_data", {}).get("file_summaries", [])
        
        # Only generate fixes for high-risk PRs or missing tests
        if risk_data.get("score", 0) < 50 and not test_data.get("missing_tests"):
            return None
        
        # Get the actual code changes for context
        files_changed = context.get("diff_data", {}).get("files_changed", [])
        
        code_snippets = []
        for f in files_changed[:3]:  # Limit to 3 files
            patch = f.get("patch", "")[:1000]  # Truncate
            if patch:
                code_snippets.append(f"### {f['filename']}\n```diff\n{patch}\n```")
        
        if not code_snippets:
            return None
        
        prompt = f"""Based on this PR review, suggest specific code fixes.

## Files Changed
{chr(10).join(code_snippets)}

## Issues Found
- Risk Level: {risk_data.get('level')}
- Missing Tests: {test_data.get('missing_tests', False)}
- Reasons: {', '.join(risk_data.get('reasons', []))}

Generate 1-2 specific, actionable fixes with code examples.
Format as markdown with code blocks.

Rules:
- ONLY suggest fixes for ACTUAL bugs or ACTUAL security vulnerabilities.
- Parameterized SQL (?, %s, :param) is SAFE - do NOT suggest changes.
- Basic validation functions are FINE - do NOT suggest improvements.
- If suggesting tests, ONLY suggest them if relevant to the language changed.
- If code is correct and secure, respond with "No fixes needed."
- DO NOT invent issues or suggest "better" implementations.
Keep it under 300 words."""
        
        try:
            fix_suggestion = await llm_client.generate_content(prompt)
            if "no fixes needed" in fix_suggestion.lower():
                return None
            return fix_suggestion
        except Exception as e:
            print(f"Auto-fix generation failed: {e}")
            return None
    
    async def _update_index(self, context: Dict[str, Any]):
        """Update the vector index with files from this PR."""
        try:
            repo_full_name = context.get("repo", {}).get("full_name")
            installation_id = context.get("installation_id")
            files_changed = context.get("diff_data", {}).get("files_changed", [])
            
            if not files_changed:
                return
            
            indexer = CodebaseIndexer(repo_full_name, installation_id)
            file_paths = [f["filename"] for f in files_changed]
            await indexer.index_files(file_paths)
            
        except Exception as e:
            print(f"Index update failed (non-fatal): {e}")

    async def _post_review(self, context: Dict[str, Any], body: str):
        """Posts the review to GitHub."""
        try:
            installation_id = context.get("installation_id")
            repo_full_name = context.get("repo", {}).get("full_name")
            pr_number = context.get("pr", {}).get("number")
            
            token = get_installation_access_token(installation_id)
            g = Github(token)
            repo = g.get_repo(repo_full_name)
            pr = repo.get_pull(pr_number)
            
            pr.create_issue_comment(body)
            print("Review posted successfully.")
        except Exception as e:
            print(f"Failed to post review: {e}")

    async def run(self) -> Any:
        pass


master_agent = MasterAgent({})

