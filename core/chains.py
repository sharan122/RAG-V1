from langchain.chains import ConversationalRetrievalChain
from langchain_anthropic import ChatAnthropic
from langchain.prompts import ChatPromptTemplate
from langchain_core.documents import Document
from langchain_text_splitters import MarkdownHeaderTextSplitter, RecursiveCharacterTextSplitter
from langchain_community.vectorstores import Weaviate
from langchain_community.embeddings import CohereEmbeddings
from typing import List, Dict, Any, Optional, Union
from pathlib import Path
from core.config import ANTHROPIC_API_KEY, ANTHROPIC_MODEL, COHERE_API_KEY, COHERE_RERANK_MODEL, CHUNK_SIZE, CHUNK_OVERLAP, TOP_K_RETRIEVE, TOP_K_RERANK
from core.vectorstore import get_weaviate_client, WEAVIATE_INDEX_NAME
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

def create_rag_chain(retriever: Any) -> ConversationalRetrievalChain:
    """Create the RAG chain."""
    llm = create_llm()
    
    # Read the structured prompt from file
    try:
        with open("prompts/question_prompt.txt", "r", encoding="utf-8") as f:
            question_prompt = f.read()
    except FileNotFoundError:
        # Fallback prompt if file not found
        question_prompt = """You are an expert API documentation assistant. Answer the user's question based on the provided context.

IMPORTANT: You MUST respond with a JSON object in EXACTLY this format:

{{
  "short_answers": ["brief answer 1", "brief answer 2"],
  "descriptions": ["detailed description 1", "detailed description 2"],
  "url": ["https://example.com/api1", "https://example.com/api2"],
  "curl": ["curl -X GET 'https://api.example.com/endpoint'", "curl -X POST 'https://api.example.com/endpoint'"],
  "values": {{"key1": "value1", "key2": "value2"}},
  "numbers": {{"count": 5, "total": 100}}
}}

RULES:
1. Use ONLY these exact keys: short_answers, descriptions, url, curl, values, numbers
2. Each key should contain an array or object as shown above
3. If a key has no relevant data, use an empty array [] or empty object {{}}
4. NEVER nest JSON objects - keep it flat
5. NEVER add additional keys
6. ALWAYS return valid JSON that can be parsed

Context: {context}

Question: {question}

Respond with ONLY the JSON object, no additional text."""
    
    # Escape curly braces in the prompt to prevent LangChain template errors
    question_prompt = question_prompt.replace("{", "{{").replace("}", "}}")
    
    prompt_template = ChatPromptTemplate.from_template(question_prompt)
    
    chain = ConversationalRetrievalChain.from_llm(
        llm=llm,
        retriever=retriever,
        return_source_documents=True,
        verbose=True,
        combine_docs_chain_kwargs={"prompt": prompt_template}
    )
    
    logger.info("Created RAG chain")
    return chain

def get_rag_chain() -> Optional[ConversationalRetrievalChain]:
    """Get the RAG chain instance."""
    return rag_chain

def get_retriever() -> Optional[Any]:
    """Get the retriever instance."""
    return retriever

def get_global_variables() -> Dict[str, Any]:
    """Get all global variables for debugging."""
    return {
        "raw_document_text_length": len(raw_document_text) if raw_document_text else 0,
        "extracted_endpoints_count": len(extracted_endpoints) if extracted_endpoints else 0,
        "detected_base_url": detected_base_url,
        "base_urls_detected": base_urls_detected,
        "curl_examples_total_count": curl_examples_total_count,
        "rag_chain_exists": rag_chain is not None,
        "retriever_exists": retriever is not None
    }
