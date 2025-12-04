"""
Test script for security features in RiskAgent.
"""

import asyncio
import os

os.environ['GEMINI_API_KEYS'] = 'fake'
os.environ['APP_ID'] = '123'
os.environ['PRIVATE_KEY_PATH'] = 'fake'
os.environ['WEBHOOK_SECRET'] = 'fake'

from app.agents.risk import RiskAgent


async def test_security():
    print("=" * 60)
    print("TEST: Security Features")
    print("=" * 60)
    
    # Test 1: Sensitive file detection
    print("\n📁 Test 1: Sensitive file (.env)")
    agent = RiskAgent({
        'diff_data': {
            'files_changed': [
                {'filename': '.env', 'patch': '+SECRET=abc123'}
            ]
        },
        'test_data': {},
        'dependency_data': {}
    })
    result = await agent.run()
    print(f"   Score: {result['score']}")
    print(f"   Security Issues: {result['security_issues']}")
    assert result['score'] >= 30
    assert len(result['security_issues']) > 0
    print("   ✅ PASSED")
    
    # Test 2: Hardcoded secret
    print("\n🔑 Test 2: Hardcoded password")
    agent = RiskAgent({
        'diff_data': {
            'files_changed': [
                {'filename': 'config.py', 'patch': '+password = "supersecret123"'}
            ]
        },
        'test_data': {},
        'dependency_data': {}
    })
    result = await agent.run()
    print(f"   Score: {result['score']}")
    print(f"   Security Issues: {result['security_issues']}")
    assert result['score'] >= 20
    assert any('secret' in str(i).lower() for i in result['security_issues'])
    print("   ✅ PASSED")
    
    # Test 3: SQL injection pattern
    print("\n💉 Test 3: SQL injection")
    agent = RiskAgent({
        'diff_data': {
            'files_changed': [
                {'filename': 'db.py', 'patch': '+cursor.execute(query + user_input)'}
            ]
        },
        'test_data': {},
        'dependency_data': {}
    })
    result = await agent.run()
    print(f"   Score: {result['score']}")
    print(f"   Security Issues: {result['security_issues']}")
    assert result['score'] >= 20
    assert any('sql' in str(i).lower() for i in result['security_issues'])
    print("   ✅ PASSED")
    
    # Test 4: eval() usage
    print("\n⚠️ Test 4: Command injection (eval)")
    agent = RiskAgent({
        'diff_data': {
            'files_changed': [
                {'filename': 'utils.py', 'patch': '+result = eval(user_input)'}
            ]
        },
        'test_data': {},
        'dependency_data': {}
    })
    result = await agent.run()
    print(f"   Score: {result['score']}")
    print(f"   Security Issues: {result['security_issues']}")
    assert result['score'] >= 20
    print("   ✅ PASSED")
    
    # Test 5: Vulnerable package
    print("\n📦 Test 5: Vulnerable package")
    agent = RiskAgent({
        'diff_data': {
            'files_changed': [
                {'filename': 'requirements.txt', 'patch': '+pycrypto==2.6.1'}
            ]
        },
        'test_data': {},
        'dependency_data': {}
    })
    result = await agent.run()
    print(f"   Score: {result['score']}")
    print(f"   Security Issues: {result['security_issues']}")
    assert result['score'] >= 25
    print("   ✅ PASSED")
    
    # Test 6: Clean code (no security issues)
    print("\n✅ Test 6: Clean code")
    agent = RiskAgent({
        'diff_data': {
            'files_changed': [
                {'filename': 'utils.py', 'patch': '+def add(a, b): return a + b'}
            ]
        },
        'test_data': {},
        'dependency_data': {}
    })
    result = await agent.run()
    print(f"   Score: {result['score']}")
    print(f"   Security Issues: {result['security_issues']}")
    assert len(result['security_issues']) == 0
    print("   ✅ PASSED")
    
    print("\n" + "=" * 60)
    print("🎉 ALL SECURITY TESTS PASSED!")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(test_security())
