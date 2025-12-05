"""
Review Writer Agent - The "Reduce" step in our Map-Reduce strategy.
Combines file summaries into a final review, enhanced with RAG context.
"""

from typing import Any, Dict, List
from app.agents.base import BaseAgent
from app.core.llm import llm_client


class ReviewWriterAgent(BaseAgent):
    """Composes the final review from aggregated summaries and RAG context."""

    async def run(self) -> str:
        print("ReviewWriterAgent: Writing review (Reduce step)...")
        
        # Get all the data from other agents
        file_summaries = self.context.get("file_summary_data", {}).get("file_summaries", [])
        risk_data = self.context.get("risk_data", {})
        test_data = self.context.get("test_data", {})
        dependency_data = self.context.get("dependency_data", {})
        diff_data = self.context.get("diff_data", {})
        rag_context = self.context.get("rag_context", {})
        
        # Format file summaries
        summaries_text = self._format_summaries(file_summaries)
        
        # Format impact analysis
        impact_text = self._format_impact(dependency_data)
        
        # Format RAG context (related code from the codebase)
        rag_text = self._format_rag_context(rag_context)
        
        # Build the prompt
        prompt = f"""You are an expert code reviewer. Write a structured PR review.

## PR Statistics
- Files Changed: {diff_data.get('changed_files_count', len(file_summaries))}
- Total Additions: {diff_data.get('total_additions', 'N/A')}
- Total Deletions: {diff_data.get('total_deletions', 'N/A')}

## Risk Assessment
- Risk Level: **{risk_data.get('level', 'Unknown')}** (Score: {risk_data.get('score', 'N/A')}/100)
- Tests Modified: {test_data.get('tests_modified', False)}
- Missing Tests: {test_data.get('missing_tests', False)}

## Security Issues Found
{self._format_security_issues(risk_data)}

## File Changes
{summaries_text}

## Potential Impact
{impact_text}

## Related Codebase Context
{rag_text}

---

Write a review with these sections:
1. **Summary**: One sentence overview
2. **Key Changes**: Bullet points of significant changes
3. **Security Alerts**: If any security issues were found, highlight them prominently with ⚠️
4. **Concerns**: Only mention actual bugs, security issues, or breaking changes (if none, say "None identified")
5. **Suggestions**: Only suggest fixes for real problems

Rules:
- Be concise and specific
- Focus ONLY on: bugs, security issues, breaking changes, missing error handling
- DO NOT comment on: code style, variable naming, formatting, comments, personal preferences
- Everyone has their own coding style - respect it
- PRIORITIZE security issues
- If no real issues found, just say "Looks good! No issues found."
- Keep it short - developers are busy"""
        
        try:
            review = await llm_client.generate_content(prompt)
            return review
        except Exception as e:
            print(f"ReviewWriterAgent: LLM failed: {e}")
            return self._generate_fallback_review(file_summaries, risk_data, test_data)
    
    def _format_summaries(self, file_summaries: List[Dict]) -> str:
        """Formats file summaries for the prompt."""
        if not file_summaries:
            return "No file summaries available."
        
        lines = []
        for fs in file_summaries:
            lines.append(fs.get("summary", f"**{fs.get('filename', 'Unknown')}**"))
        
        return "\n\n".join(lines)
    
    def _format_impact(self, dependency_data: Dict) -> str:
        """Formats impact analysis for the prompt."""
        impact_analysis = dependency_data.get("impact_analysis", [])
        
        if not impact_analysis:
            return "No cross-file impacts detected."
        
        lines = []
        for item in impact_analysis[:5]:  # Limit to 5
            lines.append(f"- `{item.get('file')}` may be affected by changes to `{item.get('symbol')}`")
        
        return "\n".join(lines)
    
    def _format_rag_context(self, rag_context: Dict) -> str:
        """Formats RAG context for the prompt."""
        context_chunks = rag_context.get("context_chunks", [])
        
        if not context_chunks:
            if rag_context.get("needs_indexing"):
                return "⚠️ Codebase not indexed yet. Run indexing for better context."
            return "No additional context found."
        
        lines = ["The following related code was found in the codebase:"]
        for chunk in context_chunks:
            file_path = chunk.get("file", "unknown")
            content = chunk.get("content", "")[:300]  # Truncate
            relevance = chunk.get("relevance", 0)
            lines.append(f"\n**`{file_path}`** (relevance: {relevance:.2f})")
            lines.append(f"```\n{content}\n```")
        
        return "\n".join(lines)
    
    def _format_security_issues(self, risk_data: Dict) -> str:
        """Formats security issues for the prompt."""
        security_issues = risk_data.get("security_issues", [])
        
        if not security_issues:
            return "✅ No security issues detected."
        
        lines = ["⚠️ **SECURITY ISSUES FOUND:**"]
        for issue in security_issues:
            lines.append(f"- {issue}")
        
        return "\n".join(lines)
    
    def _generate_fallback_review(
        self, 
        file_summaries: List[Dict], 
        risk_data: Dict, 
        test_data: Dict
    ) -> str:
        """Generates a basic review if LLM fails."""
        review = f"""## PR Review (Fallback Mode)

**Risk Level**: {risk_data.get('level', 'Unknown')}

### Files Changed
"""
        for fs in file_summaries:
            review += f"- {fs.get('filename', 'Unknown')} (+{fs.get('additions', 0)}/-{fs.get('deletions', 0)})\n"
        
        if test_data.get('missing_tests'):
            review += "\n⚠️ **Warning**: No tests were modified. Consider adding tests for the new code."
        
        return review

