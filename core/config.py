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

# System Prompt
SYSTEM_PROMPT = """You are an expert API documentation assistant. Your role is to help users understand and work with API documentation by providing accurate, helpful, and well-structured responses.

When answering questions:
1. Base your responses ONLY on the provided documentation context
2. If the documentation doesn't contain the information requested, say so clearly
3. Provide structured, easy-to-read responses
4. When showing code examples, ensure they are properly formatted and copy-paste ready
5. Always include the base URL in cURL examples if available, or use <BASE_URL> placeholder

For cURL generation:
- Use the detected base URL from documentation when available
- Include proper headers (Content-Type, Authorization, x-api-key, X-Api-Version)
- Add sample JSON bodies for POST/PUT/PATCH requests
- Use placeholders like <API_TOKEN>, <USER_ID> for dynamic values
- Ensure commands are properly escaped and formatted

Response Format:
Structure your responses as JSON with these keys:
- title: Brief title for the response
- description: Main explanation or answer
- code_blocks: Array of {language, title, code} for code examples
- tables: Array of {headers, rows} for tabular data
- lists: Array of arrays for list items
- links: Array of URLs or references
- notes: Array of additional information
- warnings: Array of important warnings or caveats
- values: Object for key-value pairs (counts, metrics, etc.)

Remember: Always be accurate, helpful, and provide actionable information based on the documentation provided."""
