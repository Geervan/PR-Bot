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


Act as an advanced code analysis tool. Be direct and factual.

Structure:

### 1. 📝 Summary
Briefly explain the functional changes in this PR.

### 2. 🚨 Critical Issues
(Only if applicable)
- 🔴 **Security**: [Description of vulnerability]
- 🔴 **Bug**: [Description of bug]

### 3. ⚠️ Improvements
(Only if meaningful)
- 🟡 **Code Quality**: [Performance/Reliability issue]
- 🟡 **Tests**: [Mention if missing for new logic]

### 4. 🛠️ Code Suggestions
(Use <details> for code blocks)
<details>
<summary>Fix for [Issue]</summary>

```language
[Code]
```
</details>

Rules:
- If no critical issues, state: "✅ **Code looks safe and correct.**"
- DO NOT complain about style, comments, naming, or code improvements.
- DO NOT suggest "better" ways to do things unless there's an actual bug/vulnerability.
- Parameterized SQL queries (using ?, %s, or :param) are SAFE - do NOT flag them as SQL injection.
- Basic validation functions are fine - do NOT suggest regex improvements.
- Focus ONLY on: actual bugs, actual security vulnerabilities, breaking changes.
- If code works correctly and is secure, say so and move on.
- Do NOT invent issues that don't exist.
- Keep it short.
"""
        
        try:
            review = await llm_client.generate_content(prompt)
            
            # Add risk score badge at the top
            risk_score = risk_data.get('score', 0)
            risk_level = risk_data.get('level', 'Low')
            security_issues = risk_data.get('security_issues', [])
            
            # Create header
            if risk_score >= 70:
                badge = f"## 🔴 Risk Score: {risk_score}/100 ({risk_level})"
            elif risk_score >= 40:
                badge = f"## 🟡 Risk Score: {risk_score}/100 ({risk_level})"
            else:
                badge = f"## 🟢 Risk Score: {risk_score}/100 ({risk_level})"
            
            # Add security issues count if any
            if security_issues:
                badge += f"\n⚠️ **{len(security_issues)} security issue(s) detected**"
            
            full_review = f"{badge}\n\n---\n\n{review}"
            return full_review
            
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

