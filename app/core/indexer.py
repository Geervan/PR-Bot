"""
Codebase Indexer - Handles full and incremental indexing of repositories.
Supports multiple languages via Tree-sitter.
"""

from typing import List, Dict, Any
from app.core.vector_store import VectorStore, get_vector_store
from app.core.embeddings import embeddings_client
from app.core.code_parser import code_parser
from github import Github
from app.core.security import get_installation_access_token


class CodebaseIndexer:
    """
    Indexes a codebase for RAG-based context retrieval.
    
    Features:
    - Full indexing on first run
    - Incremental updates on subsequent runs
    - Multi-language support via Tree-sitter
    - Chunks code into logical units (functions, classes)
    """
    
    # File extensions to index (all Tree-sitter supported + common ones)
    SUPPORTED_EXTENSIONS = {
        # Python
        '.py',
        # JavaScript/TypeScript
        '.js', '.jsx', '.mjs', '.ts', '.tsx',
        # Java
        '.java',
        # C/C++
        '.c', '.h', '.cpp', '.cc', '.cxx', '.hpp',
        # Go
        '.go',
        # Rust
        '.rs',
        # Web (no Tree-sitter, but useful for context)
        '.html', '.css', '.scss',
        # Config
        '.json', '.yaml', '.yml', '.toml',
        # Docs
        '.md',
    }
    
    # Maximum file size to index (100KB)
    MAX_FILE_SIZE = 100 * 1024
    
    # Directories to skip
    SKIP_DIRS = {
        'node_modules', 'venv', '.venv', '__pycache__', '.git', 
        'dist', 'build', 'target', '.idea', '.vscode',
        'vendor', 'packages', '.next', '.nuxt'
    }
    
    def __init__(self, repo_full_name: str, installation_id: int):
        self.repo_full_name = repo_full_name
        self.installation_id = installation_id
        self.vector_store = get_vector_store(repo_full_name)
    
    async def index_full(self) -> Dict[str, Any]:
        """
        Perform a full index of the repository.
        Only indexes files that have changed since last index.
        """
        print(f"CodebaseIndexer: Starting full index of {self.repo_full_name}...")
        
        token = get_installation_access_token(self.installation_id)
        g = Github(token)
        repo = g.get_repo(self.repo_full_name)
        
        stats = {"indexed": 0, "skipped": 0, "errors": 0}
        
        try:
            contents = repo.get_contents("")
            await self._process_contents(repo, contents, stats)
        except Exception as e:
            print(f"CodebaseIndexer: Error during indexing: {e}")
            stats["errors"] += 1
        
        print(f"CodebaseIndexer: Indexing complete. {stats}")
        return stats
    
    async def _process_contents(self, repo, contents, stats: Dict):
        """Recursively process repository contents."""
        while contents:
            file_content = contents.pop(0)
            
            # Skip directories we don't want
            if file_content.type == "dir":
                if file_content.name not in self.SKIP_DIRS:
                    try:
                        contents.extend(repo.get_contents(file_content.path))
                    except:
                        pass
                continue
            
            # Check file extension
            path = file_content.path
            ext = '.' + path.split('.')[-1].lower() if '.' in path else ''
            
            if ext not in self.SUPPORTED_EXTENSIONS:
                stats["skipped"] += 1
                continue
            
            # Check file size
            if file_content.size > self.MAX_FILE_SIZE:
                stats["skipped"] += 1
                continue
            
            # Get file content
            try:
                content = file_content.decoded_content.decode('utf-8')
            except:
                stats["errors"] += 1
                continue
            
            # Check if file needs update
            if not self.vector_store.needs_update(path, content):
                stats["skipped"] += 1
                continue
            
            # Index the file
            await self._index_file(path, content, stats)
    
    async def _index_file(self, file_path: str, content: str, stats: Dict):
        """Index a single file."""
        try:
            # Chunk the file
            chunks = self._chunk_code(file_path, content)
            
            if not chunks:
                stats["skipped"] += 1
                return
            
            # Generate embeddings
            texts = [chunk["content"] for chunk in chunks]
            embeddings = await embeddings_client.embed_batch(texts)
            
            # Filter out empty embeddings
            valid_chunks = []
            valid_embeddings = []
            for chunk, emb in zip(chunks, embeddings):
                if emb:
                    valid_chunks.append(chunk)
                    valid_embeddings.append(emb)
            
            if valid_chunks:
                # Store in vector DB
                content_hash = self.vector_store._compute_hash(content)
                self.vector_store.add_chunks(file_path, valid_chunks, valid_embeddings, content_hash)
                stats["indexed"] += 1
                print(f"  Indexed: {file_path} ({len(valid_chunks)} chunks)")
            else:
                stats["skipped"] += 1
                
        except Exception as e:
            print(f"  Error indexing {file_path}: {e}")
            stats["errors"] += 1
    
    def _chunk_code(self, file_path: str, content: str) -> List[Dict[str, Any]]:
        """
        Chunk code into logical units.
        Uses Tree-sitter for supported languages, falls back to simple chunking.
        """
        chunks = []
        
        # Check if Tree-sitter supports this language
        if code_parser.is_supported(file_path):
            # Use Tree-sitter to get summary
            summary = code_parser.get_summary(content, file_path)
            
            chunks.append({
                "content": f"File: {file_path}\n\n{summary}",
                "type": "file_summary",
                "name": file_path
            })
        
        # Add file content (full or chunked)
        if len(content) < 4000:
            chunks.append({
                "content": content,
                "type": "full_file",
                "name": file_path
            })
        else:
            # Split into smaller chunks
            lines = content.split('\n')
            chunk_size = 50  # lines per chunk
            for i in range(0, len(lines), chunk_size):
                chunk_lines = lines[i:i + chunk_size]
                chunks.append({
                    "content": '\n'.join(chunk_lines),
                    "type": "code_chunk",
                    "name": f"{file_path}:L{i+1}-{i+len(chunk_lines)}"
                })
        
        return chunks
    
    async def index_files(self, file_paths: List[str]) -> Dict[str, Any]:
        """
        Index specific files (for incremental updates).
        Used when processing a PR to update only changed files.
        """
        print(f"CodebaseIndexer: Incremental index for {len(file_paths)} files...")
        
        token = get_installation_access_token(self.installation_id)
        g = Github(token)
        repo = g.get_repo(self.repo_full_name)
        
        stats = {"indexed": 0, "skipped": 0, "errors": 0}
        
        for file_path in file_paths:
            try:
                file_content = repo.get_contents(file_path)
                content = file_content.decoded_content.decode('utf-8')
                
                if self.vector_store.needs_update(file_path, content):
                    await self._index_file(file_path, content, stats)
                else:
                    stats["skipped"] += 1
                    
            except Exception as e:
                print(f"  Error fetching {file_path}: {e}")
                stats["errors"] += 1
        
        return stats
    
    async def delete_files(self, file_paths: List[str]):
        """Remove deleted files from the index."""
        for file_path in file_paths:
            self.vector_store.delete_file(file_path)
            print(f"  Removed from index: {file_path}")
