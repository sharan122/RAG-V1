"""
Shared state module for RAG system.
This module holds global variables that need to be shared between different routers.
"""

from typing import List, Dict, Any, Optional
from langchain_core.documents import Document

# Global variables for RAG system state
raw_document_text: str = ""
extracted_endpoints: List[Dict[str, Any]] = []
detected_base_url: Optional[str] = None
base_urls_detected: List[str] = []
curl_examples_total_count: int = 0
vector_store = None
rag_chain = None
retriever = None
documents_count = 0
db_size_mb = 0.0
last_updated = None
weaviate_client_instance = None
weaviate_index_name = None

def get_state() -> Dict[str, Any]:
    """Get current state as a dictionary."""
    return {
        "raw_document_text": raw_document_text,
        "extracted_endpoints": extracted_endpoints,
        "detected_base_url": detected_base_url,
        "base_urls_detected": base_urls_detected,
        "curl_examples_total_count": curl_examples_total_count,
        "vector_store": vector_store,
        "rag_chain": rag_chain,
        "retriever": retriever,
        "documents_count": documents_count,
        "db_size_mb": db_size_mb,
        "last_updated": last_updated,
        "weaviate_client_instance": weaviate_client_instance,
        "weaviate_index_name": weaviate_index_name,
    }

def is_ready() -> bool:
    """Check if the RAG system is ready."""
    return rag_chain is not None and retriever is not None

