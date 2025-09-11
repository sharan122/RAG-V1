import os
from dotenv import load_dotenv

load_dotenv()

# API Keys
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
COHERE_API_KEY = os.getenv("COHERE_API_KEY")

# Weaviate Configuration
WEAVIATE_URL = os.getenv("WEAVIATE_URL", "http://127.0.0.1:8080")
WEAVIATE_INDEX_NAME = os.getenv("WEAVIATE_INDEX_NAME", "RAGDocs")

# Model Configuration
ANTHROPIC_MODEL = os.getenv("ANTHROPIC_MODEL", "claude-3-5-haiku-20241022")
COHERE_EMBEDDING_MODEL = os.getenv("COHERE_EMBEDDING_MODEL", "embed-english-v3.0")
COHERE_RERANK_MODEL = os.getenv("COHERE_RERANK_MODEL", "rerank-english-v3.0")

# Application Configuration
APP_TITLE = "RAG API Documentation Assistant"
APP_VERSION = "1.0.0"
APP_DESCRIPTION = "AI-powered API documentation assistant with RAG capabilities"

# Memory Configuration
MEMORY_K = 10  # Number of messages to keep in memory

# Chunking Configuration
CHUNK_SIZE = 1500                    # Optimal for API documentation
CHUNK_OVERLAP = 300                  # Better context preservation
MIN_CHUNK_SIZE = 50                  # Minimum chunk size to keep

# Retrieval Configuration
TOP_K_RETRIEVE = 8                   # Final number of documents
TOP_K_FETCH = 20                     # Documents to fetch before MMR
MMR_LAMBDA = 0.7                     # MMR diversity vs relevance balance
TOP_K_RERANK = 5                     # Documents after reranking

# Query Expansion Configuration
MAX_EXPANDED_QUERIES = 3             # Maximum query variations
ENABLE_QUERY_EXPANSION = True        # Enable query expansion

