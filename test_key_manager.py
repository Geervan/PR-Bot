import asyncio
import os

# Mock settings for testing BEFORE importing app modules
os.environ["GEMINI_API_KEYS"] = "fake_key_1,fake_key_2,fake_key_3"
os.environ["APP_ID"] = "123"
os.environ["PRIVATE_KEY_PATH"] = "fake_path"
os.environ["WEBHOOK_SECRET"] = "fake_secret"

from app.core.key_manager import key_manager
from app.core.llm import llm_client

# Re-initialize key manager with mock keys (hacky but works for script)
key_manager.keys = ["fake_key_1", "fake_key_2", "fake_key_3"]
key_manager.current_index = 0

async def test_rotation():
    print("Testing Key Rotation...")
    keys_used = []
    for _ in range(5):
        key = key_manager.get_next_key()
        keys_used.append(key)
        print(f"Got key: {key}")
    
    assert keys_used[0] == "fake_key_1"
    assert keys_used[1] == "fake_key_2"
    assert keys_used[2] == "fake_key_3"
    assert keys_used[3] == "fake_key_1"
    print("Rotation Test Passed!")

async def test_rate_limit():
    print("\nTesting Rate Limit Handling...")
    key = "fake_key_1"
    print(f"Reporting rate limit for {key}")
    key_manager.report_rate_limit(key)
    
    next_key = key_manager.get_next_key()
    print(f"Next key should not be {key}. Got: {next_key}")
    assert next_key != key
    print("Rate Limit Test Passed!")

if __name__ == "__main__":
    asyncio.run(test_rotation())
    asyncio.run(test_rate_limit())
