"""
File Summary Agent - The "Map" step in our Map-Reduce strategy.
Summarizes individual files to reduce token usage.
"""

from typing import Any, Dict, List
from app.agents.base import BaseAgent
from app.core.llm import llm_client
from app.core.code_parser import python_parser


class FileSummaryAgent(BaseAgent):
    """Summarizes individual file changes to reduce token usage."""
    
    # Maximum characters of diff to send to LLM per file
    MAX_DIFF_CHARS = 2000
    
    async def run(self) -> Dict[str, Any]:
        """Summarizes each changed file."""
        print("FileSummaryAgent: Summarizing files (Map step)...")
        
        files_changed = self.context.get("diff_data", {}).get("files_changed", [])
        dependency_data = self.context.get("dependency_data", {})
        
        file_summaries = []
        
        for file_info in files_changed:
            filename = file_info.get("filename", "")
            patch = file_info.get("patch", "")
            additions = file_info.get("additions", 0)
            deletions = file_info.get("deletions", 0)
            
            # Get Tree-sitter summary if available
            tree_sitter_summary = dependency_data.get("summaries", {}).get(filename, "")
            
            # Truncate large patches
            truncated = False
            if len(patch) > self.MAX_DIFF_CHARS:
                patch = patch[:self.MAX_DIFF_CHARS]
                truncated = True
            
            # For small changes, use a simple summary without LLM
            if additions + deletions < 10:
                summary = self._create_simple_summary(filename, patch, additions, deletions, tree_sitter_summary)
            else:
                # For larger changes, use LLM to summarize
                summary = await self._create_llm_summary(filename, patch, additions, deletions, tree_sitter_summary, truncated)
            
            file_summaries.append({
                "filename": filename,
                "additions": additions,
                "deletions": deletions,
                "summary": summary
            })
        
        return {"file_summaries": file_summaries}
    
    def _create_simple_summary(
        self, 
        filename: str, 
        patch: str, 
        additions: int, 
        deletions: int,
        tree_sitter_summary: str
    ) -> str:
        """Creates a simple summary for small changes without using LLM."""
        summary = f"**{filename}** (+{additions}/-{deletions})"
        
        if tree_sitter_summary:
            summary += f"\n{tree_sitter_summary}"
        
        return summary
    
    async def _create_llm_summary(
        self, 
        filename: str, 
        patch: str, 
        additions: int, 
        deletions: int,
        tree_sitter_summary: str,
        truncated: bool
    ) -> str:
        """Uses LLM to summarize larger changes."""
        
        truncation_note = " (truncated)" if truncated else ""
        
        prompt = f"""Summarize this code change in 2-3 bullet points. Be specific about what changed. No fluff.

File: {filename} (+{additions}/-{deletions}){truncation_note}

Code Structure:
{tree_sitter_summary if tree_sitter_summary else "N/A"}

Diff:
```
{patch}
```

Output format:
- [Change type]: [Specific description]"""
        
        try:
            summary = await llm_client.generate_content(prompt)
            return f"**{filename}** (+{additions}/-{deletions})\n{summary}"
        except Exception as e:
            print(f"FileSummaryAgent: LLM failed for {filename}: {e}")
            return self._create_simple_summary(filename, patch, additions, deletions, tree_sitter_summary)
