from langchain.chains import ConversationalRetrievalChain
from langchain_anthropic import ChatAnthropic
from langchain_text_splitters import RecursiveCharacterTextSplitter
from typing import List, Dict, Any, Optional
from core.config import ANTHROPIC_API_KEY, ANTHROPIC_MODEL, CHUNK_SIZE, CHUNK_OVERLAP
from utils.logger import get_logger

logger = get_logger(__name__)

# Global variables
rag_chain: Optional[ConversationalRetrievalChain] = None
retriever: Optional[Any] = None  # Will be a retriever from Weaviate.as_retriever()
raw_document_text: str = ""
extracted_endpoints: List[Dict[str, Any]] = []
detected_base_url: Optional[str] = None
base_urls_detected: List[str] = []
curl_examples_total_count: int = 0

def create_llm() -> ChatAnthropic:
    """Create the Anthropic LLM instance."""
    if not ANTHROPIC_API_KEY:
        raise ValueError("ANTHROPIC_API_KEY environment variable is required")
    
    return ChatAnthropic(
        anthropic_api_key=ANTHROPIC_API_KEY,
        model=ANTHROPIC_MODEL,
        temperature=0.1
    )

def create_text_splitter() -> RecursiveCharacterTextSplitter:
    """Create the text splitter for chunking documents."""
    return RecursiveCharacterTextSplitter(
        chunk_size=CHUNK_SIZE,
        chunk_overlap=CHUNK_OVERLAP,
        length_function=len,
        separators=["\n\n", "\n", " ", ""]
    )



