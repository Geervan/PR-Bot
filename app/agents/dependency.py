import re
from typing import Any, Dict, List, Set
from app.agents.base import BaseAgent
from github import Github
from app.core.security import get_installation_access_token
from app.core.code_parser import code_parser, CodeSymbols


class DependencyAgent(BaseAgent):
    """Analyzes cross-file dependencies using Tree-sitter."""

    async def run(self) -> Dict[str, Any]:
        """Identifies related files and their impact."""
        print("DependencyAgent: Analyzing dependencies with Tree-sitter...")
        
        files_changed = self.context.get("diff_data", {}).get("files_changed", [])
        installation_id = self.context.get("installation_id")
        repo_full_name = self.context.get("repo", {}).get("full_name")
        
        if not files_changed or not installation_id:
            return {"related_files": [], "summaries": {}, "impact_analysis": []}

        try:
            token = get_installation_access_token(installation_id)
            g = Github(token)
            repo = g.get_repo(repo_full_name)
        except Exception as e:
            print(f"DependencyAgent: Failed to connect to GitHub: {e}")
            return {"related_files": [], "summaries": {}, "impact_analysis": [], "error": str(e)}
        
        # Track all symbols defined and used in changed files
        all_defined_functions: Set[str] = set()
        all_defined_classes: Set[str] = set()
        all_imports: Set[str] = set()
        file_summaries: Dict[str, str] = {}
        
        for file_info in files_changed:
            filename = file_info['filename']
            
            # Skip unsupported files
            if not code_parser.is_supported(filename):
                continue
            
            # Fetch full file content from the repo
            try:
                file_content = repo.get_contents(filename).decoded_content.decode('utf-8')
            except Exception as e:
                print(f"DependencyAgent: Could not fetch {filename}: {e}")
                continue
            
            # Parse with Tree-sitter (multi-language)
            symbols = code_parser.parse(file_content, filename)
            
            # Collect defined symbols
            all_defined_functions.update(symbols.functions)
            all_defined_classes.update(symbols.classes)
            
            # Collect imports (these are dependencies of the changed file)
            all_imports.update(symbols.imports)
            for fi in symbols.from_imports:
                all_imports.add(fi['module'])
            
            # Generate compact summary for LLM
            file_summaries[filename] = code_parser.get_summary(file_content, filename)
        
        # Find files that might be affected (reverse dependency lookup)
        # Search for files that import or call the modified functions/classes
        impact_analysis = []
        
        if all_defined_functions or all_defined_classes:
            impact_analysis = await self._find_impacted_files(
                repo, 
                all_defined_functions, 
                all_defined_classes,
                [f['filename'] for f in files_changed]
            )
        
        return {
            "related_files": list(all_imports),
            "summaries": file_summaries,
            "defined_functions": list(all_defined_functions),
            "defined_classes": list(all_defined_classes),
            "impact_analysis": impact_analysis
        }
    
    async def _find_impacted_files(
        self, 
        repo, 
        functions: Set[str], 
        classes: Set[str],
        exclude_files: List[str]
    ) -> List[Dict[str, Any]]:
        """Finds files that might be impacted by changes to the given functions/classes."""
        impacted = []
        
        # Search for usages of the top 5 most important symbols
        # (to avoid too many API calls)
        symbols_to_search = list(functions)[:3] + list(classes)[:2]
        
        for symbol in symbols_to_search:
            try:
                # Use GitHub's code search API
                # Note: This has rate limits, so we limit the search
                search_results = repo.search_code(f"{symbol} language:python")
                
                for result in search_results[:5]:  # Limit to 5 results per symbol
                    if result.path not in exclude_files:
                        impacted.append({
                            "file": result.path,
                            "symbol": symbol,
                            "reason": f"May use '{symbol}'"
                        })
            except Exception as e:
                # Code search might not be available for all repos
                print(f"DependencyAgent: Search failed for {symbol}: {e}")
                continue
        
        # Deduplicate by file path
        seen = set()
        unique_impacted = []
        for item in impacted:
            if item['file'] not in seen:
                seen.add(item['file'])
                unique_impacted.append(item)
        
        return unique_impacted

