"""
Test script for the RAG (vector store) system.
"""

import asyncio
import os
import shutil

# Set mock env vars before importing app modules
os.environ["GEMINI_API_KEYS"] = "fake_key"
os.environ["APP_ID"] = "123"
os.environ["PRIVATE_KEY_PATH"] = "fake_path"
os.environ["WEBHOOK_SECRET"] = "fake_secret"

from app.core.vector_store import VectorStore, get_vector_store


def test_vector_store_basic():
    """Test basic vector store operations."""
    print("=" * 60)
    print("TEST: Vector Store Basic Operations")
    print("=" * 60)
    
    # Clean up test directory
    test_dir = "./.test_vector_db"
    if os.path.exists(test_dir):
        shutil.rmtree(test_dir)
    
    # Create vector store
    store = VectorStore("test/repo", persist_dir=test_dir)
    
    # Check initial stats
    stats = store.get_stats()
    print(f"\n📊 Initial stats: {stats}")
    assert stats["total_chunks"] == 0
    
    # Add some chunks with mock embeddings
    chunks = [
        {"content": "def hello(): return 'world'", "type": "function", "name": "hello"},
        {"content": "class User: pass", "type": "class", "name": "User"}
    ]
    # Mock 768-dimensional embeddings (Gemini's dimension)
    embeddings = [
        [0.1] * 768,
        [0.2] * 768
    ]
    
    store.add_chunks("utils.py", chunks, embeddings, "hash123")
    
    # Check stats after adding
    stats = store.get_stats()
    print(f"📊 After adding: {stats}")
    assert stats["total_chunks"] == 2
    assert stats["indexed_files"] == 1
    
    print("\n✅ Basic operations test PASSED!")
    
    # Clean up
    shutil.rmtree(test_dir)


def test_vector_store_query():
    """Test vector similarity search."""
    print("\n" + "=" * 60)
    print("TEST: Vector Store Query")
    print("=" * 60)
    
    # Clean up test directory
    test_dir = "./.test_vector_db"
    if os.path.exists(test_dir):
        shutil.rmtree(test_dir)
    
    store = VectorStore("test/repo", persist_dir=test_dir)
    
    # Add chunks with distinct embeddings
    chunks = [
        {"content": "def calculate_sum(a, b): return a + b", "type": "function", "name": "calculate_sum"},
        {"content": "def calculate_product(a, b): return a * b", "type": "function", "name": "calculate_product"},
        {"content": "class DatabaseConnection: pass", "type": "class", "name": "DatabaseConnection"}
    ]
    
    # Create embeddings that make the sum functions similar
    embeddings = [
        [1.0, 0.0, 0.0] + [0.0] * 765,  # calculate_sum
        [0.9, 0.1, 0.0] + [0.0] * 765,  # calculate_product (similar to sum)
        [0.0, 0.0, 1.0] + [0.0] * 765,  # DatabaseConnection (different)
    ]
    
    store.add_chunks("math.py", chunks, embeddings, "hash456")
    
    # Query with embedding similar to calculate_sum
    query_embedding = [1.0, 0.0, 0.0] + [0.0] * 765
    results = store.query(query_embedding, n_results=2)
    
    print(f"\n🔍 Query results: {len(results)} found")
    for r in results:
        print(f"   - {r['metadata']['name']}: distance={r['distance']:.4f}")
    
    # The sum function should be first (most similar)
    assert len(results) == 2
    assert results[0]["metadata"]["name"] == "calculate_sum"
    
    print("\n✅ Query test PASSED!")
    
    # Clean up
    shutil.rmtree(test_dir)


def test_incremental_update():
    """Test incremental update (file hash tracking)."""
    print("\n" + "=" * 60)
    print("TEST: Incremental Update")
    print("=" * 60)
    
    test_dir = "./.test_vector_db"
    if os.path.exists(test_dir):
        shutil.rmtree(test_dir)
    
    store = VectorStore("test/repo", persist_dir=test_dir)
    
    # Check if file needs update (should return True for new file)
    content = "def foo(): pass"
    needs_update = store.needs_update("new_file.py", content)
    print(f"\n📝 New file needs update: {needs_update}")
    assert needs_update == True
    
    # Add the file
    chunks = [{"content": content, "type": "function", "name": "foo"}]
    embeddings = [[0.5] * 768]
    store.add_chunks("new_file.py", chunks, embeddings, store._compute_hash(content))
    
    # Check if same content needs update (should return False)
    needs_update = store.needs_update("new_file.py", content)
    print(f"📝 Same content needs update: {needs_update}")
    assert needs_update == False
    
    # Check if modified content needs update (should return True)
    modified_content = "def foo(): return 'bar'"
    needs_update = store.needs_update("new_file.py", modified_content)
    print(f"📝 Modified content needs update: {needs_update}")
    assert needs_update == True
    
    print("\n✅ Incremental update test PASSED!")
    
    # Clean up
    shutil.rmtree(test_dir)


def test_persistence():
    """Test that data persists across store instances."""
    print("\n" + "=" * 60)
    print("TEST: Persistence")
    print("=" * 60)
    
    test_dir = "./.test_vector_db"
    if os.path.exists(test_dir):
        shutil.rmtree(test_dir)
    
    # Create store and add data
    store1 = VectorStore("test/repo", persist_dir=test_dir)
    chunks = [{"content": "persistent data", "type": "code", "name": "test"}]
    embeddings = [[0.3] * 768]
    store1.add_chunks("persistent.py", chunks, embeddings, "hash789")
    
    print(f"\n💾 Store 1 chunks: {store1.get_stats()['total_chunks']}")
    
    # Create new store instance (should load persisted data)
    store2 = VectorStore("test/repo", persist_dir=test_dir)
    
    print(f"💾 Store 2 chunks: {store2.get_stats()['total_chunks']}")
    
    assert store2.get_stats()["total_chunks"] == 1
    assert store2.get_stats()["indexed_files"] == 1
    
    print("\n✅ Persistence test PASSED!")
    
    # Clean up
    shutil.rmtree(test_dir)


if __name__ == "__main__":
    try:
        test_vector_store_basic()
        test_vector_store_query()
        test_incremental_update()
        test_persistence()
        print("\n" + "=" * 60)
        print("🎉 ALL RAG TESTS PASSED!")
        print("=" * 60)
    except AssertionError as e:
        print(f"\n❌ TEST FAILED: {e}")
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
