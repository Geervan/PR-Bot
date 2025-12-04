"""
Vector store module using NumPy for simple vector operations.
No external vector DB dependencies - works on any Python version.
"""

import os
import json
import numpy as np
from typing import List, Dict, Any, Optional
from pathlib import Path


class VectorStore:
    """
    Simple file-based vector store using NumPy.
    
    Stores:
    - Embeddings as numpy arrays
    - Metadata as JSON
    - File hashes for incremental updates
    """
    
    def __init__(self, repo_id: str, persist_dir: str = "./.vector_db"):
        """
        Initialize vector store for a specific repository.
        
        Args:
            repo_id: Unique identifier for the repo (e.g., "owner/repo")
            persist_dir: Directory to persist the database
        """
        self.repo_id = repo_id.replace("/", "_")
        self.persist_dir = os.path.join(persist_dir, self.repo_id)
        
        # Ensure directory exists
        os.makedirs(self.persist_dir, exist_ok=True)
        
        # File paths
        self.embeddings_file = os.path.join(self.persist_dir, "embeddings.npy")
        self.metadata_file = os.path.join(self.persist_dir, "metadata.json")
        self.hashes_file = os.path.join(self.persist_dir, "file_hashes.json")
        
        # Load existing data
        self.embeddings = self._load_embeddings()
        self.metadata = self._load_metadata()
        self.file_hashes = self._load_hashes()
    
    def _load_embeddings(self) -> np.ndarray:
        """Load embeddings from disk."""
        if os.path.exists(self.embeddings_file):
            try:
                return np.load(self.embeddings_file)
            except:
                pass
        return np.array([])
    
    def _load_metadata(self) -> List[Dict]:
        """Load metadata from disk."""
        if os.path.exists(self.metadata_file):
            try:
                with open(self.metadata_file, 'r') as f:
                    return json.load(f)
            except:
                pass
        return []
    
    def _load_hashes(self) -> Dict[str, str]:
        """Load file hashes from disk."""
        if os.path.exists(self.hashes_file):
            try:
                with open(self.hashes_file, 'r') as f:
                    return json.load(f)
            except:
                pass
        return {}
    
    def _save(self):
        """Save all data to disk."""
        if len(self.embeddings) > 0:
            np.save(self.embeddings_file, self.embeddings)
        
        with open(self.metadata_file, 'w') as f:
            json.dump(self.metadata, f)
        
        with open(self.hashes_file, 'w') as f:
            json.dump(self.file_hashes, f)
    
    def _compute_hash(self, content: str) -> str:
        """Compute hash of file content."""
        import hashlib
        return hashlib.sha256(content.encode()).hexdigest()[:16]
    
    def needs_update(self, file_path: str, content: str) -> bool:
        """Check if a file needs to be re-indexed."""
        current_hash = self._compute_hash(content)
        stored_hash = self.file_hashes.get(file_path)
        return stored_hash != current_hash
    
    def add_chunks(
        self, 
        file_path: str, 
        chunks: List[Dict[str, Any]], 
        embeddings: List[List[float]],
        content_hash: str
    ):
        """
        Add or update chunks for a file.
        """
        if not chunks or not embeddings:
            return
        
        # Remove old chunks for this file
        self._delete_file_chunks(file_path)
        
        # Convert embeddings to numpy array
        new_embeddings = np.array(embeddings)
        
        # Create metadata for each chunk
        new_metadata = [
            {
                "id": f"{file_path}:{i}",
                "file_path": file_path,
                "chunk_index": i,
                "chunk_type": chunk.get("type", "code"),
                "name": chunk.get("name", ""),
                "content": chunk.get("content", "")[:500]  # Store truncated content
            }
            for i, chunk in enumerate(chunks)
        ]
        
        # Append to existing data
        if len(self.embeddings) == 0:
            self.embeddings = new_embeddings
        else:
            self.embeddings = np.vstack([self.embeddings, new_embeddings])
        
        self.metadata.extend(new_metadata)
        
        # Update hash
        self.file_hashes[file_path] = content_hash
        self._save()
    
    def _delete_file_chunks(self, file_path: str):
        """Delete all chunks for a file."""
        if len(self.metadata) == 0:
            return
        
        # Find indices to keep (not matching file_path)
        keep_indices = [
            i for i, m in enumerate(self.metadata)
            if m.get("file_path") != file_path
        ]
        
        if len(keep_indices) == len(self.metadata):
            return  # Nothing to delete
        
        # Filter metadata
        self.metadata = [self.metadata[i] for i in keep_indices]
        
        # Filter embeddings
        if len(self.embeddings) > 0 and len(keep_indices) > 0:
            self.embeddings = self.embeddings[keep_indices]
        elif len(keep_indices) == 0:
            self.embeddings = np.array([])
        
        self._save()
    
    def delete_file(self, file_path: str):
        """Remove a file from the index."""
        self._delete_file_chunks(file_path)
        if file_path in self.file_hashes:
            del self.file_hashes[file_path]
            self._save()
    
    def query(
        self, 
        query_embedding: List[float], 
        n_results: int = 5,
        filter_dict: Optional[Dict] = None
    ) -> List[Dict[str, Any]]:
        """
        Query for similar code chunks using cosine similarity.
        """
        if not query_embedding or len(self.embeddings) == 0:
            return []
        
        query_vec = np.array(query_embedding)
        
        # Compute cosine similarity
        # Normalize vectors
        query_norm = query_vec / (np.linalg.norm(query_vec) + 1e-8)
        emb_norms = self.embeddings / (np.linalg.norm(self.embeddings, axis=1, keepdims=True) + 1e-8)
        
        # Compute similarities
        similarities = np.dot(emb_norms, query_norm)
        
        # Apply filter if provided
        valid_indices = list(range(len(self.metadata)))
        if filter_dict:
            valid_indices = [
                i for i, m in enumerate(self.metadata)
                if all(m.get(k) == v for k, v in filter_dict.items())
            ]
        
        if not valid_indices:
            return []
        
        # Get top results
        valid_similarities = [(i, similarities[i]) for i in valid_indices]
        valid_similarities.sort(key=lambda x: x[1], reverse=True)
        top_indices = valid_similarities[:n_results]
        
        # Format results
        results = []
        for idx, sim in top_indices:
            meta = self.metadata[idx]
            results.append({
                "id": meta.get("id", ""),
                "content": meta.get("content", ""),
                "metadata": {
                    "file_path": meta.get("file_path", ""),
                    "chunk_type": meta.get("chunk_type", ""),
                    "name": meta.get("name", "")
                },
                "distance": 1 - sim  # Convert similarity to distance
            })
        
        return results
    
    def get_stats(self) -> Dict[str, Any]:
        """Get statistics about the index."""
        return {
            "repo_id": self.repo_id,
            "total_chunks": len(self.metadata),
            "indexed_files": len(self.file_hashes)
        }


def get_vector_store(repo_full_name: str) -> VectorStore:
    """Factory function to get a vector store for a repository."""
    return VectorStore(repo_id=repo_full_name)

