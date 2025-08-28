import weaviate
from langchain_community.vectorstores import Weaviate
from langchain_community.embeddings import CohereEmbeddings
from langchain_core.documents import Document
from typing import List, Dict, Any, Optional
from core.config import WEAVIATE_URL, WEAVIATE_INDEX_NAME, COHERE_API_KEY , COHERE_EMBEDDING_MODEL, COHERE_RERANK_MODEL
from utils.logger import get_logger

logger = get_logger(__name__)

# Global variables
weaviate_client_instance: Optional[weaviate.Client] = None
weaviate_index_name: str = WEAVIATE_INDEX_NAME
rag_chain = None
retriever = None

def initialize_weaviate() -> weaviate.Client:
    """Initialize Weaviate client."""
    global weaviate_client_instance
    
    if weaviate_client_instance is None:
        try:
            weaviate_client_instance = weaviate.Client(WEAVIATE_URL)
            logger.info(f"Connected to Weaviate at {WEAVIATE_URL}")
        except Exception as e:
            logger.error(f"Failed to connect to Weaviate: {e}")
            raise
    
    return weaviate_client_instance

def get_weaviate_client() -> weaviate.Client:
    """Get the Weaviate client instance."""
    if weaviate_client_instance is None:
        return initialize_weaviate()
    return weaviate_client_instance

def create_weaviate_schema() -> None:
    """Create the Weaviate schema for document storage."""
    client = get_weaviate_client()
    
    # Define the schema
    schema = {
        "class": WEAVIATE_INDEX_NAME,
        "vectorizer": "none",  # We'll provide our own vectors
        "properties": [
            {
                "name": "page_content",
                "dataType": ["text"],
                "description": "The content of the document chunk"
            },
            {
                "name": "title",
                "dataType": ["text"],
                "description": "Title of the document"
            },
            {
                "name": "section_path",
                "dataType": ["text"],
                "description": "Path to the section in the document"
            },
            {
                "name": "endpoint",
                "dataType": ["text"],
                "description": "API endpoint path"
            },
            {
                "name": "http_method",
                "dataType": ["text"],
                "description": "HTTP method (GET, POST, etc.)"
            },
            {
                "name": "auth",
                "dataType": ["text"],
                "description": "Authentication method"
            },
            {
                "name": "has_curl",
                "dataType": ["boolean"],
                "description": "Whether the chunk contains cURL examples"
            },
            {
                "name": "is_catalog",
                "dataType": ["boolean"],
                "description": "Whether this is a catalog entry"
            },
            {
                "name": "is_structured",
                "dataType": ["boolean"],
                "description": "Whether this is structured data"
            },
            {
                "name": "base_url",
                "dataType": ["text"],
                "description": "Base URL for the API"
            },
            {
                "name": "tags",
                "dataType": ["text[]"],
                "description": "Tags for categorization"
            },
            {
                "name": "section",
                "dataType": ["text"],
                "description": "Section name"
            },
            {
                "name": "parameters",
                "dataType": ["text[]"],
                "description": "API parameters"
            }
        ],
        "vectorIndexConfig": {
            "distance": "cosine"
        }
    }
    
    try:
        # Check if class exists
        if client.schema.exists(WEAVIATE_INDEX_NAME):
            logger.info(f"Schema {WEAVIATE_INDEX_NAME} already exists")
            return
        
        # Create the class
        client.schema.create_class(schema)
        logger.info(f"Created schema {WEAVIATE_INDEX_NAME}")
    except Exception as e:
        logger.error(f"Failed to create schema: {e}")
        raise

def get_embeddings() -> CohereEmbeddings:
    """Get Cohere embeddings instance."""
    if not COHERE_API_KEY:
        raise ValueError("COHERE_API_KEY environment variable is required")
    
    return CohereEmbeddings(
        model=COHERE_EMBEDDING_MODEL,
        cohere_api_key=COHERE_API_KEY
    )

def create_vectorstore(documents: List[Document]) -> Weaviate:
    """Create a Weaviate vector store from documents."""
    client = get_weaviate_client()
    embeddings = get_embeddings()
    
    # Create schema if it doesn't exist
    create_weaviate_schema()
    
    # Create the vector store
    vectorstore = Weaviate.from_documents(
        documents=documents,
        embedding=embeddings,
        client=client,
        index_name=WEAVIATE_INDEX_NAME,
        by_text=False
    )
    
    logger.info(f"Created vector store with {len(documents)} documents")
    return vectorstore

def clear_vectorstore() -> bool:
    """Clear all documents from the vector store."""
    try:
        client = get_weaviate_client()
        client.schema.delete_class(WEAVIATE_INDEX_NAME)
        logger.info(f"Cleared vector store {WEAVIATE_INDEX_NAME}")
        return True
    except Exception as e:
        logger.error(f"Failed to clear vector store: {e}")
        return False

def get_vectorstore_status() -> Dict[str, Any]:
    """Get the status of the vector store."""
    try:
        client = get_weaviate_client()
        
        # Check if class exists
        if not client.schema.exists(WEAVIATE_INDEX_NAME):
            return {
                "status": "not_initialized",
                "index_name": WEAVIATE_INDEX_NAME,
                "document_count": 0,
                "message": "Vector store has not been initialized"
            }
        
        # Get document count
        result = client.query.aggregate(WEAVIATE_INDEX_NAME).with_meta_count().do()
        count = result.get("data", {}).get("Aggregate", {}).get(WEAVIATE_INDEX_NAME, [{}])[0].get("meta", {}).get("count", 0)
        
        return {
            "status": "ready",
            "index_name": WEAVIATE_INDEX_NAME,
            "document_count": count,
            "message": f"Vector store is ready with {count} documents"
        }
    except Exception as e:
        logger.error(f"Failed to get vector store status: {e}")
        return {
            "status": "error",
            "index_name": WEAVIATE_INDEX_NAME,
            "document_count": 0,
            "message": f"Error getting status: {str(e)}"
        }

def hybrid_retrieve_documents(query: str, k: int = 8, where_filter: Optional[Dict] = None) -> List[Document]:
    """Retrieve documents using hybrid search (BM25 + vector)."""
    try:
        client = get_weaviate_client()
        
        # Build the query
        query_builder = client.query.get(WEAVIATE_INDEX_NAME, [
            "page_content", "title", "section_path", "endpoint", "http_method", "auth", "has_curl"
        ]).with_limit(k)
        
        # Add hybrid search
        query_builder = query_builder.with_hybrid(
            query=query,
            alpha=0.5  # Balance between BM25 and vector search
        )
        
        # Add filters if specified
        if where_filter:
            query_builder = query_builder.with_where(where_filter)
        
        # Execute query
        result = query_builder.do()
        
        # Convert to Document objects
        documents = []
        for obj in result.get("data", {}).get("Get", {}).get(WEAVIATE_INDEX_NAME, []):
            doc = Document(
                page_content=obj.get("page_content", ""),
                metadata={
                    "title": obj.get("title", ""),
                    "section_path": obj.get("section_path", ""),
                    "endpoint": obj.get("endpoint", ""),
                    "http_method": obj.get("http_method", ""),
                    "auth": obj.get("auth", ""),
                    "has_curl": obj.get("has_curl", False)
                }
            )
            documents.append(doc)
        
        return documents
    except Exception as e:
        logger.error(f"Failed to retrieve documents: {e}")
        return []

def _query_weaviate_for_curl(method: Optional[str], endpoint: Optional[str], limit: int = 20) -> List[Dict[str, Any]]:
    """Retrieve documents from Weaviate likely containing cURL examples."""
    try:
        client = get_weaviate_client()
        cls = weaviate_index_name
        
        props = ["page_content", "title", "section_path", "endpoint", "http_method"]
        query = client.query.get(cls, props).with_limit(limit)
        
        operands: List[Dict[str, Any]] = []
        # Always filter for objects likely containing cURL text
        operands.append({"path": ["page_content"], "operator": "Like", "valueString": "*curl*"})
        
        if endpoint:
            operands.append({"path": ["endpoint"], "operator": "Equal", "valueText": endpoint})
        if method:
            operands.append({"path": ["http_method"], "operator": "Equal", "valueText": method})
        
        if len(operands) == 1:
            query = query.with_where(operands[0])
        else:
            query = query.with_where({"operator": "And", "operands": operands})
        
        result = query.do()
        objs = result.get("data", {}).get("Get", {}).get(cls, []) if isinstance(result, dict) else []
        
        out: List[Dict[str, Any]] = []
        for obj in objs:
            text = obj.get("page_content") or ""
            title = obj.get("title") or ""
            section_path = obj.get("section_path") or ""
            
            # Extract cURL blocks from the text
            from utils.parser import _extract_curl_blocks_from_text
            for block in _extract_curl_blocks_from_text(text):
                out.append({
                    "title": block.get("title") or title or "cURL example",
                    "section_path": section_path,
                    "code": block["code"],
                })
                if len(out) >= limit:
                    return out
        
        return out
    except Exception as err:
        logger.error(f"Error in _query_weaviate_for_curl: {err}")
        return []

def _count_curl_examples_weaviate(method: Optional[str], endpoint: Optional[str], keyword_terms: Optional[List[str]] = None) -> Optional[int]:
    """Return exact count of Weaviate objects that likely contain cURL."""
    try:
        client = get_weaviate_client()
        cls = weaviate_index_name
        
        # Build aggregate query
        query = client.query.aggregate(cls).with_meta_count()
        
        operands: List[Dict[str, Any]] = []
        # Always filter for objects likely containing cURL text
        operands.append({"path": ["page_content"], "operator": "Like", "valueString": "*curl*"})
        
        if endpoint:
            operands.append({"path": ["endpoint"], "operator": "Equal", "valueText": endpoint})
        if method:
            operands.append({"path": ["http_method"], "operator": "Equal", "valueText": method})
        
        if len(operands) == 1:
            query = query.with_where(operands[0])
        else:
            query = query.with_where({"operator": "And", "operands": operands})
        
        result = query.do()
        count = result.get("data", {}).get("Aggregate", {}).get(cls, [{}])[0].get("meta", {}).get("count", 0)
        
        return count
    except Exception as e:
        logger.error(f"Error counting cURL examples: {e}")
        return None
