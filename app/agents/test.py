from typing import Any, Dict
from app.agents.base import BaseAgent

class TestAgent(BaseAgent):
    """Analyzes test impact."""

    async def run(self) -> Dict[str, Any]:
        print("TestAgent: Analyzing test impact...")
        files_changed = self.context.get("diff_data", {}).get("files_changed", [])
        
        tests_modified = False
        code_modified = False
        
        for file in files_changed:
            filename = file['filename']
            if "test" in filename.lower():
                tests_modified = True
            else:
                code_modified = True
        
        missing_tests = code_modified and not tests_modified
        
        return {
            "tests_modified": tests_modified,
            "missing_tests": missing_tests
        }
