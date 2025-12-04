"""
Context Agent - Retrieves relevant context from the codebase for PR review.
Uses RAG to find code related to the changes being reviewed.
"""

from typing import Any, Dict, List
from app.agents.base import BaseAgent
from app.core.vector_store import get_vector_store
from app.core.embeddings import embeddings_client


class ContextAgent(BaseAgent):
    """
    Retrieves relevant context from the indexed codebase.
    
    This is what makes the bot "understand" code beyond just the diff.
    It can answer questions like:
    - "Where else is this function used?"
    - "What does the codebase do with this pattern?"
    - "Are there similar implementations elsewhere?"
    """
    
    async def run(self) -> Dict[str, Any]:
        """Retrieves relevant context for the changed files."""
        print("ContextAgent: Retrieving codebase context (RAG)...")
        
        repo_full_name = self.context.get("repo", {}).get("full_name")
        file_summaries = self.context.get("file_summary_data", {}).get("file_summaries", [])
        dependency_data = self.context.get("dependency_data", {})
        
        if not repo_full_name:
            return {"context_chunks": [], "error": "No repo name"}
        
        vector_store = get_vector_store(repo_full_name)
        
        # Check if we have any indexed data
        stats = vector_store.get_stats()
        if stats["total_chunks"] == 0:
            print("ContextAgent: No indexed data available. Run indexing first.")
            return {"context_chunks": [], "needs_indexing": True}
        
        # Build a query from the changes
        query_text = self._build_query(file_summaries, dependency_data)
        
        if not query_text:
            return {"context_chunks": []}
        
        # Get embedding for the query
        query_embedding = await embeddings_client.embed(query_text)
        
        if not query_embedding:
            return {"context_chunks": [], "error": "Failed to generate embedding"}
        
        # Query the vector store
        results = vector_store.query(
            query_embedding=query_embedding,
            n_results=5
        )
        
        # Filter out chunks from the files being changed
        changed_files = set(fs.get("filename", "") for fs in file_summaries)
        filtered_results = [
            r for r in results 
            if r.get("metadata", {}).get("file_path") not in changed_files
        ]
        
        # Format for LLM consumption
        context_chunks = []
        for r in filtered_results[:3]:  # Limit to top 3
            context_chunks.append({
                "file": r.get("metadata", {}).get("file_path", "unknown"),
                "content": r.get("content", "")[:500],  # Truncate
                "relevance": 1 - r.get("distance", 0)  # Convert distance to similarity
            })
        
        print(f"ContextAgent: Found {len(context_chunks)} relevant context chunks")
        
        return {
            "context_chunks": context_chunks,
            "index_stats": stats
        }
    
    def _build_query(self, file_summaries: List[Dict], dependency_data: Dict) -> str:
        """Builds a query string from the PR changes."""
        parts = []
        
        # Add function/class names from dependency data
        defined_functions = dependency_data.get("defined_functions", [])
        defined_classes = dependency_data.get("defined_classes", [])
        
        if defined_functions:
            parts.append(f"Functions: {', '.join(defined_functions[:5])}")
        
        if defined_classes:
            parts.append(f"Classes: {', '.join(defined_classes[:5])}")
        
        # Add file summaries
        for fs in file_summaries[:3]:
            summary = fs.get("summary", "")
            if summary:
                # Extract just the key parts
                parts.append(summary[:200])
        
        return "\n".join(parts)
