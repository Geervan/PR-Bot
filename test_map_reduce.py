"""
Test script for the Map-Reduce strategy.
"""

import asyncio
import os

# Set mock env vars before importing app modules
os.environ["GEMINI_API_KEYS"] = "fake_key"
os.environ["APP_ID"] = "123"
os.environ["PRIVATE_KEY_PATH"] = "fake_path"
os.environ["WEBHOOK_SECRET"] = "fake_secret"

from app.agents.file_summary import FileSummaryAgent
from app.agents.writer import ReviewWriterAgent
from app.agents.risk import RiskAgent


async def test_file_summary_agent():
    """Test the FileSummaryAgent (Map step)."""
    print("=" * 60)
    print("TEST: FileSummaryAgent (Map Step)")
    print("=" * 60)
    
    context = {
        "diff_data": {
            "files_changed": [
                {
                    "filename": "app/utils.py",
                    "patch": """+def helper():
+    return "hello"
+
-def old_func():
-    pass""",
                    "additions": 3,
                    "deletions": 2
                },
                {
                    "filename": "app/main.py",
                    "patch": """+from app.utils import helper
+
+def main():
+    result = helper()
+    print(result)""",
                    "additions": 5,
                    "deletions": 0
                }
            ]
        },
        "dependency_data": {
            "summaries": {
                "app/utils.py": "Functions: helper\nCalls: None",
                "app/main.py": "From Imports: app.utils.helper\nFunctions: main\nCalls: helper, print"
            }
        }
    }
    
    agent = FileSummaryAgent(context)
    result = await agent.run()
    
    print(f"\n📝 File Summaries Generated: {len(result['file_summaries'])}")
    for fs in result["file_summaries"]:
        print(f"\n  📄 {fs['filename']}:")
        print(f"     {fs['summary'][:100]}...")
    
    assert len(result["file_summaries"]) == 2
    print("\n✅ FileSummaryAgent test PASSED!")
    
    return result


async def test_risk_agent():
    """Test the improved RiskAgent."""
    print("\n" + "=" * 60)
    print("TEST: RiskAgent (Improved)")
    print("=" * 60)
    
    context = {
        "diff_data": {
            "changed_files_count": 8,
            "total_additions": 350,
            "total_deletions": 50
        },
        "test_data": {
            "missing_tests": True
        },
        "dependency_data": {
            "impact_analysis": [
                {"file": "a.py", "symbol": "func1"},
                {"file": "b.py", "symbol": "func1"},
                {"file": "c.py", "symbol": "func2"}
            ]
        }
    }
    
    agent = RiskAgent(context)
    result = await agent.run()
    
    print(f"\n⚠️ Risk Level: {result['level']}")
    print(f"   Score: {result['score']}/100")
    print(f"   Reasons:")
    for reason in result['reasons']:
        print(f"     - {reason}")
    
    assert result['level'] in ['Low', 'Medium', 'High']
    assert 'reasons' in result
    print("\n✅ RiskAgent test PASSED!")
    
    return result


async def test_review_writer_fallback():
    """Test the ReviewWriterAgent fallback (without LLM)."""
    print("\n" + "=" * 60)
    print("TEST: ReviewWriterAgent (Fallback)")
    print("=" * 60)
    
    context = {
        "diff_data": {
            "changed_files_count": 3,
            "total_additions": 100,
            "total_deletions": 20
        },
        "file_summary_data": {
            "file_summaries": [
                {"filename": "utils.py", "additions": 50, "deletions": 10, "summary": "**utils.py** (+50/-10)\n- Added helper function"},
                {"filename": "main.py", "additions": 50, "deletions": 10, "summary": "**main.py** (+50/-10)\n- Updated main logic"}
            ]
        },
        "test_data": {"tests_modified": False, "missing_tests": True},
        "risk_data": {"level": "Medium", "score": 45, "reasons": ["No tests"]},
        "dependency_data": {"impact_analysis": []}
    }
    
    agent = ReviewWriterAgent(context)
    
    # Test fallback generation (simulating LLM failure)
    fallback = agent._generate_fallback_review(
        context["file_summary_data"]["file_summaries"],
        context["risk_data"],
        context["test_data"]
    )
    
    print(f"\n📝 Fallback Review:\n{fallback}")
    
    assert "utils.py" in fallback
    assert "main.py" in fallback
    assert "Warning" in fallback  # Should warn about missing tests
    print("\n✅ ReviewWriterAgent fallback test PASSED!")


if __name__ == "__main__":
    async def run_all():
        await test_file_summary_agent()
        await test_risk_agent()
        await test_review_writer_fallback()
        print("\n" + "=" * 60)
        print("🎉 ALL MAP-REDUCE TESTS PASSED!")
        print("=" * 60)
    
    asyncio.run(run_all())
