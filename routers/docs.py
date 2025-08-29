from fastapi import APIRouter, HTTPException
from models.requests import DocumentationRequest
from models.responses import SuccessResponse, ErrorResponse
from utils.parser import extract_endpoints_from_text, detect_base_url_from_text, extract_all_base_urls, _extract_curl_blocks_from_text
from utils.helpers import detect_intent, determine_response_type, parse_structured_response, build_section_path, build_structured_endpoint_json, build_catalog_text, attempt_parse_openapi, _llm_recall_endpoints_full, sanitize_index_name, _validate_endpoint_presence
from langchain_core.documents import Document
from langchain_text_splitters import MarkdownHeaderTextSplitter, RecursiveCharacterTextSplitter
from langchain_community.vectorstores import Weaviate as WeaviateStore
from langchain_cohere import CohereEmbeddings
from langchain_anthropic import ChatAnthropic
from langchain_core.prompts import ChatPromptTemplate
from langchain.chains.combine_documents import create_stuff_documents_chain
from langchain.schema.runnable import RunnableLambda
from typing import List, Dict, Any, Optional
import json
import re
import time
import weaviate as weaviate_client
import os

# SMART & FLEXIBLE cURL GENERATION FUNCTION
def generate_perfect_curl(user_input: str, context_docs: List[Document], detected_base_url: str = None) -> Dict[str, Any]:
    """
    Generate perfect, usable cURL commands using Claude for ANY cURL request.
    This function is completely flexible and can handle any user request intelligently.
    """
    try:
        # Check if user wants to create cURL
        if "create" in user_input.lower() and "curl" in user_input.lower():
            print(f"DEBUG: Smart cURL generation requested: {user_input}")
            print(f"DEBUG: Context docs available: {len(context_docs)}")
            
            # Import required modules
            import re
            from langchain_anthropic import ChatAnthropic
            
            # Initialize Claude
            claude = ChatAnthropic(
                model="claude-3-haiku-20240307",
                anthropic_api_key=os.getenv("ANTHROPIC_API_KEY")
            )
            
            # SMART INTENT DETECTION - Understand what the user wants
            user_request = user_input.lower()
            
            # Detect if user wants ALL endpoints of a specific type
            is_all_request = any(word in user_request for word in ["all", "every", "each", "list"])
            is_method_specific = any(method in user_request for method in ["post", "get", "put", "delete", "patch"])
            
            # Detect specific endpoint requests
            specific_endpoint = None
            if "/" in user_input:
                # Extract endpoint path
                endpoint_match = re.search(r'[/][\w\-{}]+', user_input)
                if endpoint_match:
                    specific_endpoint = endpoint_match.group(0)
            
            print(f"DEBUG: Intent detected - All request: {is_all_request}, Method specific: {is_method_specific}, Specific endpoint: {specific_endpoint}")
            
            # DYNAMIC DOCUMENT SEARCH - Find relevant documentation
            relevant_docs = []
            search_query = user_input
            
            # If asking for all POST endpoints, search for POST-related content
            if is_all_request and is_method_specific:
                if "post" in user_request:
                    search_query = "POST endpoint API documentation"
                elif "get" in user_request:
                    search_query = "GET endpoint API documentation"
                elif "put" in user_request:
                    search_query = "PUT endpoint API documentation"
                elif "delete" in user_request:
                    search_query = "DELETE endpoint API documentation"
            
            # Search through all available documents
            for doc in context_docs:
                doc_content = doc.page_content.lower()
                doc_metadata = doc.metadata
                
                # Check if document is relevant
                is_relevant = False
                
                # Check for method-specific content
                if is_method_specific:
                    if "post" in user_request and ("post" in doc_content or "POST" in doc_content):
                        is_relevant = True
                    elif "get" in user_request and ("get" in doc_content or "GET" in doc_content):
                        is_relevant = True
                    elif "put" in user_request and ("put" in doc_content or "PUT" in doc_content):
                        is_relevant = True
                    elif "delete" in user_request and ("delete" in doc_content or "DELETE" in doc_content):
                        is_relevant = True
                
                # Check for specific endpoint
                if specific_endpoint and specific_endpoint.lower() in doc_content:
                    is_relevant = True
                
                # Check for general API documentation
                if "endpoint" in doc_content or "api" in doc_content or "http" in doc_content:
                    is_relevant = True
                
                if is_relevant:
                    relevant_docs.append(doc)
                    print(f"DEBUG: Found relevant doc: {doc_metadata.get('title', 'No title')[:50]}")
            
            print(f"DEBUG: Found {len(relevant_docs)} relevant documents")
            
            if relevant_docs:
                # Combine relevant documentation for Claude
                combined_context = "\n\n".join([doc.page_content[:800] for doc in relevant_docs[:5]])
                
                # INTELLIGENT PROMPT GENERATION - Create the perfect prompt for Claude
                if is_all_request and is_method_specific:
                    # User wants all endpoints of a specific type
                    method_type = "POST" if "post" in user_request else "GET" if "get" in user_request else "PUT" if "put" in user_request else "DELETE"
                    
                    prompt = f"""
                    You are an expert API developer. Based on the provided API documentation, generate perfect, usable cURL commands for ALL {method_type} endpoints found in the documentation.

                    Requirements:
                    1. Find ALL {method_type} endpoints in the documentation
                    2. Generate a separate cURL command for each endpoint
                    3. Use SINGLE LINE format (no line breaks or backslashes)
                    4. Include all necessary headers and authentication
                    5. Use proper JSON formatting for request bodies
                    6. Make all commands copy-paste ready
                    7. Use placeholders like <API_KEY>, <BASE_URL> for sensitive data
                    8. Base everything on the actual API documentation provided

                    API Documentation:
                    {combined_context}

                    Generate cURL commands for ALL {method_type} endpoints found. Return them in a clear, organized format.
                    """
                    
                elif specific_endpoint:
                    # User wants a specific endpoint
                    prompt = f"""
                    You are an expert API developer. Based on the provided API documentation, generate a perfect, usable cURL command for the specific endpoint: {specific_endpoint}

                    Requirements:
                    1. Generate a perfect cURL command for {specific_endpoint}
                    2. Use SINGLE LINE format (no line breaks or backslashes)
                    3. Include all necessary headers and authentication
                    4. Use proper JSON formatting for request body
                    5. Make it copy-paste ready
                    6. Use placeholders like <API_KEY>, <BASE_URL> for sensitive data
                    7. Base the cURL on the actual API documentation provided

                    API Documentation:
                    {combined_context}

                    Endpoint: {specific_endpoint}

                    Generate the perfect cURL command for this endpoint.
                    """
                    
                else:
                    # Generic cURL request - be smart about it
                    prompt = f"""
                    You are an expert API developer. Based on the provided API documentation, generate perfect, usable cURL commands based on this user request: "{user_input}"

                    Requirements:
                    1. Understand what the user is asking for
                    2. Generate appropriate cURL commands
                    3. Use SINGLE LINE format (no line breaks or backslashes)
                    4. Include all necessary headers and authentication
                    5. Use proper JSON formatting for request bodies
                    6. Make all commands copy-paste ready
                    7. Use placeholders like <API_KEY>, <BASE_URL> for sensitive data
                    8. Base everything on the actual API documentation provided

                    API Documentation:
                    {combined_context}

                    User Request: {user_input}

                    Generate the appropriate cURL commands based on what the user is asking for.
                    """
                
                # GENERATE PERFECT cURL USING CLAUDE
                print(f"DEBUG: Sending intelligent prompt to Claude")
                curl_response = claude.invoke(prompt)
                curl_content = curl_response.content.strip()
                
                print(f"DEBUG: Claude response received, length: {len(curl_content)}")
                
                # CLEAN UP AND FORMAT THE RESPONSE
                if curl_content.startswith("```bash"):
                    curl_content = curl_content.replace("```bash", "").replace("```", "").strip()
                elif curl_content.startswith("```"):
                    curl_content = curl_content.replace("```", "").strip()
                
                # DETERMINE THE RESPONSE TYPE AND CONTENT
                if is_all_request and is_method_specific:
                    # Multiple endpoints - create a comprehensive response
                    method_type = "POST" if "post" in user_request else "GET" if "get" in user_request else "PUT" if "put" in user_request else "DELETE"
                    
                    return {
                        "short_answers": [f"Generated cURL commands for all {method_type} endpoints"],
                        "descriptions": [f"Here are perfect cURL commands for all {method_type} endpoints found in the documentation: {curl_content}"],
                        "url": [],
                        "curl": [curl_content],
                        "values": {"method_type": method_type, "endpoint_count": "multiple"},
                        "numbers": {"endpoints": len(curl_content.split("curl")) if "curl" in curl_content else 1}
                    }
                    
                elif specific_endpoint:
                    # Single endpoint
                    return {
                        "short_answers": [f"Generated cURL command for {specific_endpoint}"],
                        "descriptions": [f"Here's the perfect cURL command for the {specific_endpoint} endpoint: {curl_content}"],
                        "url": [],
                        "curl": [curl_content],
                        "values": {"endpoint": specific_endpoint, "method": "specific"},
                        "numbers": {"endpoints": 1}
                    }
                    
                else:
                    # Generic response
                    return {
                        "short_answers": ["Generated cURL commands based on your request"],
                        "descriptions": [f"Here are the cURL commands based on your request: '{user_input}': {curl_content}"],
                        "url": [],
                        "curl": [curl_content],
                        "values": {"request": user_input, "generation_method": "claude_analysis"},
                        "numbers": {"commands": len(curl_content.split("curl")) if "curl" in curl_content else 1}
                    }
            
            else:
                print(f"DEBUG: No relevant documentation found")
                # Fallback response
                return {
                    "short_answers": ["No relevant documentation found for cURL generation"],
                    "descriptions": ["I couldn't find relevant documentation for your cURL request. Please ensure documentation is loaded and try again."],
                    "url": [],
                    "curl": [],
                    "values": {"error": "no_documentation", "suggestion": "load_documentation"},
                    "numbers": {"endpoints": 0}
                }
                
    except Exception as e:
        print(f"ERROR: Smart cURL generation failed: {e}")
        return {
            "short_answers": ["cURL generation failed"],
            "descriptions": [f"Failed to generate cURL commands: {str(e)}"],
            "url": [],
            "curl": [],
            "values": {"error": "generation_failed", "error_details": str(e)},
            "numbers": {"endpoints": 0}
        }

router = APIRouter(prefix="/docs", tags=["documentation"])

# Import shared state
from core.state import (
    raw_document_text, extracted_endpoints, detected_base_url, base_urls_detected, 
    curl_examples_total_count, vector_store, rag_chain, retriever, documents_count, 
    db_size_mb, last_updated, weaviate_client_instance, weaviate_index_name
)

# Environment variables
WEAVIATE_URL = os.getenv("WEAVIATE_URL", "http://127.0.0.1:8080")
WEAVIATE_INDEX_NAME = os.getenv("WEAVIATE_INDEX_NAME", "RAGDocs")
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
ANTHROPIC_MODEL = os.getenv("ANTHROPIC_MODEL", "claude-3-haiku-20240307")

# Add missing helper functions
def build_task_preface(intent: str, method: Optional[str], path: Optional[str]) -> str:
    if intent == "comprehensive_list":
        return (
            "Task: COMPREHENSIVE LIST - Retrieve and list ALL API endpoints from the entire documentation. "
            "This requires full document coverage, not just search results. Return JSON with type='table' and "
            "tables=[{headers,rows}]. Use columns: Method, Path, Summary, Auth, Has cURL. "
            "Include ALL endpoints found in the documentation. Include citations in notes.\n"
        )
    if intent == "list_apis":
        return (
            "Task: List all API endpoints as a table. Return JSON with type='table' and tables=[{headers,rows}]. "
            "Use columns: Method, Path, Summary, Auth, Has cURL. Include citations in notes.\n"
        )
    if intent == "get_payload":
        target = f" for {method} {path}" if method and path else ""
        return (
            f"Task: Return request/response payload details{target}. Strict JSON: type='values', "
            "values={request:{schema,example}, responses:[{status,schema,example}]}. Include citations in notes.\n"
        )
    if intent == "generate_curl":
        target = f" for {method} {path}" if method and path else ""
        return (
            f"Task: Generate cURL commands{target}. Strict JSON: type='code', code_blocks=[{{language:'bash',title,code}}]. "
            "Use placeholders like <API_TOKEN>, <BASE_URL> if needed; include minimal required headers. Include citations in notes.\n"
        )
    return ""

def parse_explicit_endpoint(question: str) -> Optional[Dict[str, str]]:
    """Parse patterns like 'GET /users/{id}' from the question."""
    # First try explicit method + path pattern
    m = re.search(r"(?im)\b(GET|POST|PUT|PATCH|DELETE|OPTIONS|HEAD)\s+(/[^\s#]+)", question)
    if m:
        return {"http_method": m.group(1).upper(), "endpoint": m.group(2)}
    
    # Then try to extract just the method if no path is specified
    # This helps with queries like "generate curl for PUT endpoints"
    method_match = re.search(r"(?im)\b(GET|POST|PUT|PATCH|DELETE|OPTIONS|HEAD)\b", question)
    if method_match:
        return {"http_method": method_match.group(1).upper(), "endpoint": None}
    
    return None

def hybrid_retrieve_documents(user_input: str, method: Optional[str], endpoint: Optional[str], k_candidates: int = 24, k_final: int = 8, alpha: float = 0.5) -> List[Document]:
    """Hybrid retrieval (BM25 + vector) with optional endpoint/method filter, plus reranking.
    Returns a list of langchain Documents.
    """
    try:
        import core.state as state
        if not state.weaviate_client_instance:
            return []
        # Embed query
        query_vector = CohereEmbeddings(model="embed-english-v3.0").embed_query(user_input)
        cls = state.weaviate_index_name or WEAVIATE_INDEX_NAME
        props = ["page_content", "title", "section_path", "endpoint", "http_method", "section"]
        qb = state.weaviate_client_instance.query.get(cls, props)
        where_clause = _build_where_clause(method, endpoint)
        if where_clause:
            qb = qb.with_where(where_clause)
        result = (
            qb.with_hybrid(query=user_input, alpha=alpha, vector=query_vector)
              .with_limit(k_candidates)
              .do()
        )
        objs = result.get("data", {}).get("Get", {}).get(cls, []) if isinstance(result, dict) else []
        docs: List[Document] = []
        for obj in objs:
            text = obj.get("page_content") or ""
            meta = {
                "title": obj.get("title"),
                "section_path": obj.get("section_path"),
                "endpoint": obj.get("endpoint"),
                "http_method": obj.get("http_method"),
                "section": obj.get("section"),
            }
            docs.append(Document(page_content=text, metadata=meta))
        # Rerank with Cohere if available
        try:
            api_key = os.getenv("COHERE_API_KEY")
            if api_key and len(docs) > 1:
                import cohere  # type: ignore
                client = cohere.Client(api_key)
                rer = client.rerank(model="rerank-english-v3.0", query=user_input, documents=[d.page_content for d in docs])
                idx_to_score = {r.index: float(getattr(r, "relevance_score", 0.0)) for r in rer.results}
                ranked = sorted(enumerate(docs), key=lambda t: idx_to_score.get(t[0], 0.0), reverse=True)
                docs = [d for _, d in ranked[:k_final]]
            else:
                docs = docs[:k_final]
        except Exception as rerank_err:
            print(f"DEBUG: rerank failed: {rerank_err}")
            docs = docs[:k_final]
        return docs
    except Exception as err:
        print(f"DEBUG: hybrid_retrieve_documents error: {err}")
        return []

def _build_where_clause(method: Optional[str], endpoint: Optional[str]) -> Optional[Dict[str, Any]]:
    operands: List[Dict[str, Any]] = []
    if endpoint:
        operands.append({"path": ["endpoint"], "operator": "Equal", "valueText": endpoint})
    if method:
        operands.append({"path": ["http_method"], "operator": "Equal", "valueText": method})
    if not operands:
        return None
    if len(operands) == 1:
        return operands[0]
    return {"operator": "And", "operands": operands}

def get_curl_from_docs(method: Optional[str], endpoint: Optional[str], allow_synthesis: bool = False, max_examples: int = 10, keyword_terms: Optional[List[str]] = None, api_version: Optional[str] = None) -> Dict[str, Any]:
    """Find cURL in docs stored in Weaviate. If none and allow_synthesis=True, synthesize one."""
    # For now, return a simple response - this can be enhanced later
    if method and endpoint:
        return {
            "short_answers": [f"cURL for {method} {endpoint}"],
            "descriptions": ["cURL command would be generated here"],
            "url": [],
            "curl": [f"curl -X {method} <BASE_URL>{endpoint}"],
            "values": {"method": method, "endpoint": endpoint},
            "numbers": {"endpoints": 1}
        }
    return {
        "short_answers": ["cURL examples"],
        "descriptions": ["cURL examples would be listed here"],
        "url": [],
        "curl": [],
        "values": {"status": "placeholder"},
        "numbers": {"endpoints": 0}
    }


def _validate_endpoint_presence(raw_text: str, method: str, path: str) -> bool:
    """Verify that a (method, path) appears in the raw text in common forms."""
    patterns = [
        rf"(?im)\b{re.escape(method)}\s+{re.escape(path)}\b",
        rf"(?is)\*\*\s*{re.escape(method)}\s*\*\*\s*`\s*{re.escape(path)}\s*`",
        rf"(?im)\b{re.escape(method)}\s+`?{re.escape(path).lstrip('/')}\b",
    ]
    for p in patterns:
        if re.search(p, raw_text):
            return True
    return False

def build_catalog_text(title: str, endpoints: List[Dict[str, Any]]) -> str:
    """Create a synthetic API catalog markdown-like text for fast listing."""
    lines = [f"## {title} - API Catalog", "", "Method | Path | Summary | Auth | Has cURL", "---|---|---|---|---"]
    for e in endpoints:
        lines.append(f"{e.get('http_method','')} | {e.get('endpoint','')} | {e.get('summary','')} | {e.get('auth','')} | {str(e.get('has_curl', False))}")
    return "\n".join(lines)

def build_structured_endpoint_json(base_url: Optional[str], endpoint: Dict[str, Any]) -> Dict[str, Any]:
    """Create a structured JSON object for hybrid storage for deterministic lookups."""
    return {
        "endpoint": endpoint.get("endpoint"),
        "method": endpoint.get("http_method"),
        "base_url": base_url,
        "summary": endpoint.get("summary", ""),
        "parameters": endpoint.get("parameters", []),
        "tags": endpoint.get("tags", []),
        "sections": ["description", "parameters", "examples"],
        "_type": "api_endpoint_structured"
    }

@router.post("/process", response_model=SuccessResponse)
async def process_documentation(request: DocumentationRequest):
    """Process API documentation and create RAG system."""
    import core.state as state
    
    try:
        # Strip yaml front matter
        raw = re.sub(r"^---\n.*?\n---\n", "", request.content, flags=re.DOTALL)
        # Keep a copy of raw text for cURL fallback/LLM filters
        state.raw_document_text = raw

        # IMPROVED CHUNKING STRATEGY - Prevent content truncation and ensure endpoint coverage
        print(f"DEBUG: Processing document with {len(raw)} characters")
        
        # Step 1: Split by major sections (H1 headers only) to keep API sections together
        major_sections = [("#","h1")]
        major_splitter = MarkdownHeaderTextSplitter(headers_to_split_on=major_sections)
        major_docs = major_splitter.split_text(raw)
        print(f"DEBUG: Created {len(major_docs)} major sections")
        
        # Step 2: For each major section, create intelligent chunks
        all_chunks: List[Document] = []
        
        for i, major_doc in enumerate(major_docs):
            section_title = major_doc.metadata.get("h1", f"Section_{i}")
            print(f"DEBUG: Processing section: {section_title}")
            
            # Use larger chunks with more overlap for API documentation
            section_splitter = RecursiveCharacterTextSplitter(
                chunk_size=3000,      # Increased from 1000 to prevent truncation
                chunk_overlap=600,     # Increased from 200 for better continuity
                separators=["\n\n", "\n", " ", ""],  # Preserve paragraph structure
                length_function=len,
                is_separator_regex=False
            )
            
            section_chunks = section_splitter.split_documents([major_doc])
            print(f"DEBUG: Section '{section_title}' created {len(section_chunks)} chunks")
            
            # Enrich each chunk with comprehensive metadata
            for j, chunk in enumerate(section_chunks):
                chunk.metadata.update({
                    "source": request.title,
                    "section_path": build_section_path(chunk.metadata),
                    "section_index": i,
                    "chunk_index": j,
                    "total_chunks_in_section": len(section_chunks),
                    "chunk_size": len(chunk.page_content)
                })
                
                # Validate chunk quality - reject chunks that are too short or broken
                if len(chunk.page_content.strip()) < 100:
                    print(f"DEBUG: Rejecting chunk {j} in section {section_title} - too short ({len(chunk.page_content)} chars)")
                    continue
                
                # Check for broken content patterns
                if any(pattern in chunk.page_content for pattern in ["}\n]\n```", "wABEgEAAAADAOz_"]):
                    print(f"DEBUG: Rejecting chunk {j} in section {section_title} - contains broken content")
                    continue
                
                all_chunks.append(chunk)
        
        print(f"DEBUG: Total chunks created: {len(all_chunks)} (after quality filtering)")
        
        # Step 3: Create additional endpoint-specific chunks for better retrieval
        endpoint_chunks = []
        for chunk in all_chunks:
            content = chunk.page_content.lower()
            # If chunk contains endpoint information, create additional focused chunks
            if any(keyword in content for keyword in ["post", "get", "put", "delete", "http", "api", "endpoint"]):
                # Create a focused chunk around this endpoint
                focused_chunk = Document(
                    page_content=chunk.page_content,
                    metadata={
                        **chunk.metadata,
                        "is_endpoint_focused": True,
                        "endpoint_density": "high"
                    }
                )
                endpoint_chunks.append(focused_chunk)
        
        # Combine all chunks
        chunks = all_chunks + endpoint_chunks
        print(f"DEBUG: Final chunk count: {len(chunks)} (including {len(endpoint_chunks)} endpoint-focused chunks)")
        
        # Validate final chunk quality
        valid_chunks = []
        for chunk in chunks:
            if len(chunk.page_content.strip()) >= 100 and not any(pattern in chunk.page_content for pattern in ["}\n]\n```", "wABEgEAAAADAOz_"]):
                valid_chunks.append(chunk)
        
        chunks = valid_chunks
        print(f"DEBUG: Final valid chunks: {len(chunks)}")
        
        if len(chunks) < 20:
            print(f"WARNING: Very few chunks created ({len(chunks)}). Document may not be properly processed.")
            # Fallback: create larger chunks
            fallback_splitter = RecursiveCharacterTextSplitter(
                chunk_size=5000,
                chunk_overlap=1000,
                separators=["\n\n", "\n", " ", ""]
            )
            fallback_chunks = fallback_splitter.split_documents([Document(page_content=raw, metadata={"source": request.title})])
            chunks = fallback_chunks
            print(f"DEBUG: Fallback chunks created: {len(chunks)}")
        
        # COMPREHENSIVE CHUNK QUALITY ANALYSIS
        print(f"\n=== CHUNK QUALITY ANALYSIS ===")
        print(f"Total chunks: {len(chunks)}")
        print(f"Total content length: {sum(len(c.page_content) for c in chunks)} characters")
        print(f"Average chunk size: {sum(len(c.page_content) for c in chunks) / len(chunks) if chunks else 0:.0f} characters")
        
        # Check for endpoint coverage
        endpoint_keywords = ["post", "get", "put", "delete", "http", "api", "endpoint", "curl"]
        endpoint_chunks_count = sum(1 for c in chunks if any(keyword in c.page_content.lower() for keyword in endpoint_keywords))
        print(f"Chunks with endpoint content: {endpoint_chunks_count}/{len(chunks)}")
        
        # Check for broken content
        broken_chunks = sum(1 for c in chunks if any(pattern in c.page_content for pattern in ["}\n]\n```", "wABEgEAAAADAOz_", "```\n```", "{\n\n}"]))
        print(f"Chunks with broken content: {broken_chunks}/{len(chunks)}")
        
        if broken_chunks > 0:
            print(f"WARNING: {broken_chunks} chunks contain broken content patterns!")
        
        # Ensure minimum chunk count for comprehensive coverage
        if len(chunks) < 30:
            print(f"WARNING: Insufficient chunks ({len(chunks)}) for comprehensive API documentation coverage!")
            print(f"Expected: 50+ chunks for full API documentation")
            print(f"Current: {len(chunks)} chunks")
        
        print(f"=== END CHUNK ANALYSIS ===\n")
        
        # Enrich metadata for all chunks
        for d in chunks:
            d.metadata.setdefault("source", request.title)
            d.metadata["section_path"] = build_section_path(d.metadata)

        # Embeddings
        print(f"DEBUG: Initializing Cohere embeddings with model: embed-english-v3.0")
        try:
            embeddings = CohereEmbeddings(model="embed-english-v3.0")
            # Test embeddings with a simple text
            test_embedding = embeddings.embed_query("test")
            print(f"✅ Cohere embeddings working - test embedding length: {len(test_embedding)}")
        except Exception as embed_error:
            print(f"❌ Cohere embeddings failed: {embed_error}")
            raise HTTPException(status_code=500, detail=f"Embeddings initialization failed: {str(embed_error)}")

        # Sanitize and set index/class name
        index_name = sanitize_index_name(request.title)

        # Initialize explicit Weaviate client (recommended, fixes URL/auth errors)
        print(f"DEBUG: Initializing Weaviate client with URL: {WEAVIATE_URL}")
        client = weaviate_client.Client(url=WEAVIATE_URL)
        
        # Test Weaviate connection
        try:
            client.is_ready()
            print(f"✅ Weaviate client connection successful")
        except Exception as conn_error:
            print(f"❌ Weaviate client connection failed: {conn_error}")
            raise HTTPException(status_code=500, detail=f"Weaviate connection failed: {str(conn_error)}")
        
        # Store weaviate client & index globally so clear/status can use them
        state.weaviate_client_instance = client
        state.weaviate_index_name = index_name

        # Defer vector store creation until after we assemble all documents
        vector_store = None

        # Let LangChain handle schema creation automatically
        # This ensures compatibility between schema and vector store
        print(f"DEBUG: Using LangChain Weaviate integration for automatic schema creation")

        # Extract endpoints, base URL and build a synthetic catalog
        # Prefer OpenAPI structured parsing if available
        structured_eps = attempt_parse_openapi(raw)
        text_eps = extract_endpoints_from_text(raw)
        # LLM-assisted recall pass with validation
        llm_eps_raw = _llm_recall_endpoints_full(raw)
        llm_eps_validated: List[Dict[str, Any]] = []
        for e in llm_eps_raw:
            m = e.get("http_method")
            p = e.get("endpoint")
            if not m or not p:
                continue
            if _validate_endpoint_presence(raw, m, p):
                llm_eps_validated.append(e)
        # ENHANCED ENDPOINT EXTRACTION - Scan chunks for additional endpoints
        
        chunk_endpoints = []
        for chunk in chunks:
            chunk_text = chunk.page_content.lower()
            # Look for HTTP method + endpoint patterns in chunks
            endpoint_patterns = [
                r'(post|get|put|delete|patch)\s+([/\w\-{}]+)',
                r'```http\s*\n(post|get|put|delete|patch)\s+([/\w\-{}]+)',
                r'endpoint[:\s]+(post|get|put|delete|patch)\s+([/\w\-{}]+)'
            ]
            
            for pattern in endpoint_patterns:
                matches = re.findall(pattern, chunk_text, re.IGNORECASE)
                for match in matches:
                    if len(match) == 2:
                        method, endpoint = match
                        chunk_endpoints.append({
                            "http_method": method.upper(),
                            "endpoint": endpoint,
                            "source": "chunk_scan",
                            "chunk_id": chunk.metadata.get("chunk_index", "unknown")
                        })
        
        print(f"DEBUG: Enhanced endpoint extraction found {len(chunk_endpoints)} additional endpoints from chunks")
        
        # Merge unique endpoints from all sources
        merged: Dict[str, Dict[str, Any]] = {}
        all_endpoint_sources = structured_eps + text_eps + llm_eps_validated + chunk_endpoints
        
        for e in all_endpoint_sources:
            key = f"{e.get('http_method')} {e.get('endpoint')}"
            if key not in merged:
                merged[key] = e
        
        state.extracted_endpoints = list(merged.values())
        print(f"DEBUG: Total unique endpoints found: {len(state.extracted_endpoints)}")
        
        # Validate endpoint coverage
        expected_endpoints = [
            "POST /file-storage", "POST /bulk-file-storage", "GET /file-storage/file",
            "POST /file-storage/bulkDownload", "DELETE /file-storage/file",
            "POST /file-storage/moveFiles", "POST /file-storage/copyFiles",
            "POST /file-utilities/convert", "POST /file-utilities/split",
            "POST /file-utilities/merge", "POST /file-utilities/encrypt",
            "GET /file-storage/file/versions", "POST /file-storage/presignedurl"
        ]
        
        found_endpoints = [f"{e.get('http_method')} {e.get('endpoint')}" for e in state.extracted_endpoints]
        missing_endpoints = [ep for ep in expected_endpoints if ep not in found_endpoints]
        
        if missing_endpoints:
            print(f"WARNING: Missing expected endpoints: {missing_endpoints}")
        else:
            print(f"✅ All expected endpoints found!")
        
        # PERFECT cURL GENERATION FUNCTION - MOVED TO GLOBAL SCOPE
        pass
        
        # Build catalog text
        api_catalog_text = build_catalog_text(request.title, extracted_endpoints) if extracted_endpoints else None
        state.detected_base_url = detect_base_url_from_text(raw)
        # Collect all base URLs for list_base_urls
        state.base_urls_detected = extract_all_base_urls(raw)
        # Precompute total cURL example count from raw docs for exact global counts
        state.curl_examples_total_count = len(_extract_curl_blocks_from_text(raw))

        # Build Documents for endpoints and catalog (semantic chunking: one endpoint per chunk)
        endpoint_docs: List[Document] = []
        for e in extracted_endpoints:
            content_lines = [
                f"### {e['http_method']} {e['endpoint']}",
                e.get("summary", ""),
                f"Auth: {e.get('auth','unknown')}",
            ]
            endpoint_doc = Document(
                page_content="\n".join([line for line in content_lines if line]),
                metadata={
                    "source": request.title,
                    "title": f"{e['http_method']} {e['endpoint']}",
                    "section_path": f"API > {e['http_method']} {e['endpoint']}",
                    "endpoint": e["endpoint"],
                    "http_method": e["http_method"],
                    "base_url": detected_base_url,
                    "auth": e.get("auth", "unknown"),
                    "has_curl": e.get("has_curl", False),
                    "is_catalog": False,
                    "tags": e.get("tags", []),
                    "section": "endpoint",
                }
            )
            endpoint_docs.append(endpoint_doc)

            # Hybrid: also store structured JSON as a separate doc for deterministic lookups
            structured = build_structured_endpoint_json(detected_base_url, e)
            endpoint_docs.append(Document(
                page_content=json.dumps(structured, ensure_ascii=False),
                metadata={
                    "source": request.title,
                    "title": f"{e['http_method']} {e['endpoint']} (structured)",
                    "section_path": f"API > {e['http_method']} {e['endpoint']} > structured",
                    "endpoint": e["endpoint"],
                    "http_method": e["http_method"],
                    "base_url": detected_base_url,
                    "is_structured": True,
                    "section": "structured",
                }
            ))

        catalog_docs: List[Document] = []
        if api_catalog_text:
            catalog_docs.append(Document(
                page_content=api_catalog_text,
                metadata={
                    "source": request.title,
                    "title": f"{request.title} Catalog",
                    "section_path": "API > Catalog",
                    "is_catalog": True,
                }
            ))

        # Add documents (chunks + endpoint summaries + catalog)
        all_docs: List[Document] = chunks + endpoint_docs + catalog_docs
        # Create Weaviate store and import docs in one step (more reliable schema creation)
        print(f"DEBUG: Attempting to create Weaviate store with {len(all_docs)} documents")
        print(f"DEBUG: Index name: {index_name}")
        print(f"DEBUG: Weaviate client: {client}")
        print(f"DEBUG: Embeddings model: {embeddings}")
        
        try:
            vector_store = WeaviateStore.from_documents(
                documents=all_docs,
                embedding=embeddings,
                client=client,
                index_name=index_name,
                text_key="page_content",
            )
            print(f"DEBUG: WeaviateStore.from_documents() completed successfully")
        except Exception as weaviate_error:
            print(f"ERROR: WeaviateStore.from_documents() failed: {weaviate_error}")
            print(f"ERROR: This means the documents were NOT stored in Weaviate!")
            raise HTTPException(status_code=500, detail=f"Weaviate storage failed: {str(weaviate_error)}")
        
        # LangChain Weaviate integration handles storage automatically
        print(f"DEBUG: LangChain Weaviate will store {len(all_docs)} documents automatically")
        
        # Verify storage was successful
        try:
            # Simple verification that documents were stored
            stored_count = len(client.query.get(index_name, ["page_content"]).with_limit(1000).do().get("data", {}).get("Get", {}).get(index_name, []))
            print(f"DEBUG: Verification - {stored_count} documents stored in Weaviate")
            
            if stored_count > 0:
                print(f"✅ Weaviate storage successful - {stored_count} documents persisted")
            else:
                print(f"❌ WARNING: No documents found in Weaviate after storage!")
                print(f"DEBUG: Attempting manual storage as fallback...")
                
                # Manual fallback storage
                try:
                    for i, doc in enumerate(all_docs):
                        client.data_object.create(
                            data_object={
                                "page_content": doc.page_content,
                                "title": doc.metadata.get("title", ""),
                                "section_path": doc.metadata.get("section_path", ""),
                                "endpoint": doc.metadata.get("endpoint", ""),
                                "http_method": doc.metadata.get("http_method", ""),
                                "base_url": doc.metadata.get("base_url", ""),
                                "auth": doc.metadata.get("auth", ""),
                                "tags": doc.metadata.get("tags", []),
                                "has_curl": doc.metadata.get("has_curl", False),
                                "is_catalog": doc.metadata.get("is_catalog", False),
                                "is_example": doc.metadata.get("is_example", False),
                                "is_param_table": doc.metadata.get("is_param_table", False),
                                "is_structured": doc.metadata.get("is_structured", False),
                                "section": doc.metadata.get("section", ""),
                                "source": doc.metadata.get("source", ""),
                                "cURLs": doc.metadata.get("cURLs", ""),
                                "section_index": doc.metadata.get("section_index", 0),
                                "chunk_index": doc.metadata.get("chunk_index", 0),
                                "total_chunks_in_section": doc.metadata.get("total_chunks_in_section", 0),
                                "chunk_size": doc.metadata.get("chunk_size", 0),
                                "is_endpoint_focused": doc.metadata.get("is_endpoint_focused", False),
                                "endpoint_density": doc.metadata.get("endpoint_density", "")
                            },
                            class_name=index_name
                        )
                        print(f"DEBUG: Manually stored document {i+1}/{len(all_docs)}")
                    
                    # Verify manual storage
                    manual_stored_count = len(client.query.get(index_name, ["page_content"]).with_limit(1000).do().get("data", {}).get("Get", {}).get(index_name, []))
                    print(f"DEBUG: Manual storage verification - {manual_stored_count} documents stored")
                    
                    if manual_stored_count > 0:
                        print(f"✅ Manual storage successful - {manual_stored_count} documents persisted")
                    else:
                        print(f"❌ Manual storage also failed!")
                        
                except Exception as manual_error:
                    print(f"ERROR: Manual storage failed: {manual_error}")
                    
        except Exception as verify_error:
            print(f"WARNING: Could not verify Weaviate storage: {verify_error}")
        
        # Store in global state
        state.vector_store = vector_store
        state.retriever = vector_store.as_retriever(search_kwargs={"k": 8})
        state.documents_count = len(all_docs)
        state.db_size_mb = len(raw) / (1024 * 1024)

        # Create retriever (same MMR config you used)
        state.retriever = state.vector_store.as_retriever(
            search_type="mmr",
            search_kwargs={"k": 6, "fetch_k": 24, "lambda_mult": 0.3}
        )

        # Build LLM + chain (use cheaper default model; configurable via ANTHROPIC_MODEL)
        llm = ChatAnthropic(model=ANTHROPIC_MODEL, temperature=0.2, max_tokens=600)

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

Question: {input}

Respond with ONLY the JSON object, no additional text."""

        # Create the prompt template - no need to escape braces for create_stuff_documents_chain
        prompt = ChatPromptTemplate.from_template(question_prompt)
        
        # Create the document chain that will handle the Document objects
        doc_chain = create_stuff_documents_chain(llm=llm, prompt=prompt)

        # --- FIX: Map retriever output to 'context' key expected by the prompt ---
        from langchain.schema.runnable import RunnableLambda
        
        def _map_inputs_for_chain(x: Dict[str, Any]) -> Dict[str, Any]:
            user_input = x.get("input", "")
            # Intent detection
            intent = detect_intent(user_input)
            
            # Parse explicit endpoint to bias retrieval
            explicit = parse_explicit_endpoint(user_input)
            
            try:
                # COMPREHENSIVE RETRIEVAL STRATEGY
                if intent == "comprehensive_list":
                    print(f"DEBUG: Using comprehensive retrieval for intent: {intent}")
                    # For comprehensive listing, get ALL documents with high limits
                    docs = hybrid_retrieve_documents(
                        user_input=user_input,
                        method=explicit.get("http_method") if explicit else None,
                        endpoint=explicit.get("endpoint") if explicit else None,
                        k_candidates=1000,  # Much higher limit for comprehensive coverage
                        k_final=500,        # Return more final results
                        alpha=0.1          # Bias toward BM25 for broader coverage
                    )
                    print(f"DEBUG: Comprehensive retrieval returned {len(docs)} documents")
                    
                    # TOKEN MANAGEMENT: Limit comprehensive listing to prevent token limit exceeded
                    max_comprehensive_docs = 100  # Limit comprehensive listing to 100 docs
                    if len(docs) > max_comprehensive_docs:
                        print(f"DEBUG: Token management: Limiting comprehensive docs from {len(docs)} to {max_comprehensive_docs}")
                        docs = docs[:max_comprehensive_docs]
                    
                    # FALLBACK: If hybrid retrieval doesn't provide enough coverage, use raw text
                    if len(docs) < 10:  # Threshold for insufficient coverage
                        print(f"DEBUG: Hybrid retrieval returned only {len(docs)} docs, using raw text fallback")
                        # Create a comprehensive document from raw text
                        raw_doc = Document(
                            page_content=state.raw_document_text,
                            metadata={
                                "title": "Complete API Documentation",
                                "section_path": "full_document",
                                "source": "raw_text_fallback"
                            }
                        )
                        docs = [raw_doc]
                        print(f"DEBUG: Fallback created comprehensive document with {len(state.raw_document_text)} characters")
                else:
                    # Standard retrieval for specific requests
                    if explicit:
                        docs = state.retriever.invoke(f"{explicit['http_method']} {explicit['endpoint']}\n\n{user_input}")
                    else:
                        docs = state.retriever.invoke(user_input)
            except Exception as retrieval_error:
                print(f"DEBUG: retriever.invoke error: {retrieval_error}")
                docs = []
            
            # INTEGRATE PERFECT cURL GENERATION
            # Check if user wants to create cURL and bypass the broken LLM
            if "create" in user_input.lower() and "curl" in user_input.lower():
                print(user_input,"user_input================")
                print(f"DEBUG: cURL generation detected, using perfect cURL generator")
                try:
                    # Limit docs for cURL generation to avoid token issues
                    limited_docs = docs[:20] if len(docs) > 20 else docs
                    print(f"DEBUG: Limited docs for cURL from {len(docs)} to {len(limited_docs)}")
                    curl_response = generate_perfect_curl(user_input, limited_docs, state.detected_base_url)
                    if curl_response:
                        print(f"DEBUG: Perfect cURL generated successfully")
                        # Return the cURL response directly, bypassing the broken LLM
                        return {
                            "context": limited_docs,
                            "input": user_input,
                            "chat_history": x.get("chat_history", ""),
                            "task_preface": "Generate perfect cURL command",
                            "curl_response": curl_response  # This will be used to bypass the LLM
                        }
                except Exception as curl_error:
                    print(f"ERROR: Perfect cURL generation failed: {curl_error}")
                    # Continue with normal flow if cURL generation fails
            
            # TOKEN MANAGEMENT: Limit context size to prevent token limit exceeded
            max_docs = 50  # Limit to 50 documents to stay well under token limit
            if len(docs) > max_docs:
                print(f"DEBUG: Token management: Limiting docs from {len(docs)} to {max_docs} to prevent token limit exceeded")
                docs = docs[:max_docs]
            
            task_preface = build_task_preface(intent, explicit.get("http_method") if explicit else None, explicit.get("endpoint") if explicit else None)
            return {
                "context": docs,
                "input": user_input,
                "chat_history": x.get("chat_history", ""),
                "task_preface": task_preface
            }
        
        retriever_chain = RunnableLambda(_map_inputs_for_chain)
        
        # Create a custom chain that handles cURL generation bypass
        def _handle_curl_bypass(x: Dict[str, Any]) -> Dict[str, Any]:
            """Handle cURL generation bypass when perfect cURL is generated"""
            if "curl_response" in x:
                print(f"DEBUG: Bypassing LLM with perfect cURL response")
                return x["curl_response"]
            else:
                # Normal flow - use the LLM
                return doc_chain.invoke(x)
        
        # Create the final chain with cURL bypass capability
        state.rag_chain = retriever_chain | RunnableLambda(_handle_curl_bypass)

        state.last_updated = time.strftime('%Y-%m-%d %H:%M:%S', time.gmtime())

        return SuccessResponse(
            message=f"Documentation processed successfully. Created {len(all_docs)} chunks and found {len(state.extracted_endpoints)} endpoints.",
            data={
                "sections": len(major_docs),
                "chunks": len(all_docs),
                "db_size_mb": round(state.db_size_mb, 2),
                "message": "Documentation processed successfully"
            }
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to process documentation: {str(e)}")

@router.post("/clear", response_model=SuccessResponse)
async def clear_documentation():
    """Clear all processed documentation."""
    try:
        import core.state as state
        
        # Clear Weaviate database by deleting the class
        if state.weaviate_client_instance and state.weaviate_index_name:
            try:
                # Delete the Weaviate class (this removes all data)
                state.weaviate_client_instance.schema.delete_class(state.weaviate_index_name)
                print(f"DEBUG: Deleted Weaviate class: {state.weaviate_index_name}")
            except Exception as weaviate_error:
                print(f"DEBUG: Error deleting Weaviate class: {weaviate_error}")
                # Continue with state reset even if Weaviate deletion fails
        
        # Reset all state variables
        state.vector_store = None
        state.rag_chain = None
        state.retriever = None
        state.documents_count = 0
        state.db_size_mb = 0.0
        state.last_updated = None
        state.weaviate_client_instance = None
        state.weaviate_index_name = None
        state.raw_document_text = ""
        state.extracted_endpoints = []
        state.detected_base_url = None
        state.base_urls_detected = []
        state.curl_examples_total_count = 0
        
        print("DEBUG: All state variables reset")
        
        return SuccessResponse(message="Documentation cleared successfully")
        
    except Exception as e:
        print(f"DEBUG: Error in clear_documentation: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to clear documentation: {str(e)}")

@router.get("/status")
async def get_documentation_status():
    """Get the status of processed documentation."""
    try:
        import core.state as state
        # Return the structure that matches what the frontend expects
        return {
            "is_ready": state.vector_store is not None and state.rag_chain is not None,
            "documents_count": state.documents_count,
            "db_size_mb": state.db_size_mb,
            "last_updated": state.last_updated,
            "vectorstore": {
                "status": "ready" if state.vector_store is not None else "not_initialized",
                "index_name": state.weaviate_index_name or WEAVIATE_INDEX_NAME,
                "document_count": state.documents_count,
                "db_size_mb": state.db_size_mb
            },
            "endpoints": {
                "count": len(state.extracted_endpoints) if state.extracted_endpoints else 0,
                "list": state.extracted_endpoints[:10] if state.extracted_endpoints else []  # Show first 10
            },
            "base_url": state.detected_base_url,
            "curl_examples": state.curl_examples_total_count
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get status: {str(e)}")

@router.get("/health")
async def docs_health():
    """Get documentation system health status."""
    try:
        import core.state as state
        is_ready = state.vector_store is not None and state.rag_chain is not None
        
        return {
            "status": "healthy" if is_ready else "unhealthy",
            "is_ready": is_ready,
            "document_count": state.documents_count,
            "message": "Documentation system is operational" if is_ready else "Documentation system is not ready"
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "is_ready": False,
            "document_count": 0,
            "error": str(e),
            "message": "Documentation system error"
        }

@router.post("/reload")
async def reload_documentation():
    """Manually reload existing documentation from Weaviate."""
    try:
        print("🔄 Manual reload requested...")
        success = await reload_existing_data()
        
        if success:
            return {
                "status": "success",
                "message": "Documentation reloaded successfully",
                "documents_count": get_state().get("documents_count", 0)
            }
        else:
            return {
                "status": "warning",
                "message": "No existing documentation found to reload",
                "documents_count": 0
            }
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to reload documentation: {str(e)}")

@router.get("/test")
async def test_rag_system():
    """Test if the RAG system is working after reload."""
    try:
        import core.state as state
        
        if not state.rag_chain:
            return {
                "status": "error",
                "message": "RAG system not initialized",
                "is_ready": False
            }
        
        # Try a simple test query
        test_result = state.rag_chain.invoke({
            "question": "What is this documentation about?",
            "chat_history": ""
        })
        
        return {
            "status": "success",
            "message": "RAG system is working",
            "is_ready": True,
            "test_result": str(test_result)[:200] + "..." if len(str(test_result)) > 200 else str(test_result)
        }
        
    except Exception as e:
        return {
            "status": "error",
            "message": f"RAG system test failed: {str(e)}",
            "is_ready": False,
            "error": str(e)
        }

async def reload_existing_data():
    """Reload existing data from Weaviate on application startup."""
    try:
        import core.state as state
        from core.config import WEAVIATE_URL, WEAVIATE_INDEX_NAME
        
        print(f"DEBUG: Attempting to reload existing data from Weaviate...")
        
        # Check if Weaviate has any existing data
        import weaviate as weaviate_client
        
        # Initialize Weaviate client
        client = weaviate_client.Client(url=WEAVIATE_URL)
        
        # Check if any classes exist and have data
        try:
            schema = client.schema.get()
            existing_classes = [cls.get("class") for cls in schema.get("classes", [])]
            
            print(f"DEBUG: Found existing classes: {existing_classes}")
            
            # Look for classes with data and collect total counts
            total_documents = 0
            all_endpoints = []
            primary_class = None
            primary_vector_store = None
            primary_retriever = None
            
            for class_name in existing_classes:
                try:
                    # Check how many objects exist in this class
                    objects_response = client.query.get(class_name, ["page_content"]).with_limit(1).do()
                    objects = objects_response.get("data", {}).get("Get", {}).get(class_name, [])
                    
                    if objects:
                        print(f"DEBUG: Found class '{class_name}' with data, checking total count...")
                        
                        # Get total count of objects in this class
                        total_objects_response = client.query.aggregate(class_name).with_meta_count().do()
                        total_count = total_objects_response.get("data", {}).get("Aggregate", {}).get(class_name, [{}])[0].get("meta", {}).get("count", 0)
                        total_documents += total_count
                        
                        print(f"DEBUG: Class '{class_name}' has {total_count} documents")
                        
                        # Use the first class with data as the primary one for vector store
                        if primary_class is None:
                            primary_class = class_name
                            
                            # Initialize embeddings
                            from langchain_cohere import CohereEmbeddings
                            embeddings = CohereEmbeddings(model="embed-english-v3.0")
                            
                            # Create vector store from existing data
                            from langchain_community.vectorstores import Weaviate as WeaviateStore
                            primary_vector_store = WeaviateStore(
                                client=client,
                                index_name=class_name,
                                text_key="page_content",
                                embedding=embeddings
                            )
                            
                            # Create retriever
                            primary_retriever = primary_vector_store.as_retriever(
                                search_type="similarity",
                                search_kwargs={"k": 50}
                            )
                        
                        # Extract basic endpoint information from the documents
                        try:
                            # Get a sample of documents to extract endpoints
                            sample_docs = client.query.get(class_name, ["page_content", "endpoint", "http_method"]).with_limit(100).do()
                            sample_objects = sample_docs.get("data", {}).get("Get", {}).get(class_name, [])
                            
                            for obj in sample_objects:
                                props = obj.get("properties", {})
                                if props.get("endpoint") and props.get("http_method"):
                                    all_endpoints.append({
                                        "method": props.get("http_method"),
                                        "path": props.get("endpoint"),
                                        "summary": f"Endpoint from {class_name}",
                                        "auth": "API Key",
                                        "has_curl": True
                                    })
                            
                        except Exception as endpoint_error:
                            print(f"DEBUG: Could not extract endpoints from {class_name}: {endpoint_error}")
                        
                except Exception as class_error:
                    print(f"DEBUG: Error checking class '{class_name}': {class_error}")
                    continue
            
            if primary_class and primary_vector_store and primary_retriever:
                print(f"DEBUG: Total documents found across all classes: {total_documents}")
                print(f"DEBUG: Total endpoints extracted: {len(all_endpoints)}")
                
                # Create RAG chain
                from langchain_core.prompts import ChatPromptTemplate
                from langchain.chains.combine_documents import create_stuff_documents_chain
                from langchain_anthropic import ChatAnthropic
                
                llm = ChatAnthropic(
                    model="claude-3-haiku-20240307",
                    anthropic_api_key=os.getenv("ANTHROPIC_API_KEY")
                )
                
                # Read the structured prompt from file for reloaded data
                try:
                    with open("prompts/question_prompt.txt", "r", encoding="utf-8") as f:
                        reloaded_prompt = f.read()
                except FileNotFoundError:
                    # Fallback prompt if file not found
                    reloaded_prompt = """You are an expert API documentation assistant. Answer the user's question based on the provided context.

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

Question: {input}

Respond with ONLY the JSON object, no additional text."""

                # Create the prompt template - no need to escape braces for create_stuff_documents_chain
                
                prompt = ChatPromptTemplate.from_template(reloaded_prompt)
                
                # Create the RAG chain with proper input mapping
                rag_chain = create_stuff_documents_chain(llm, prompt)
                
                # Wrap the chain to handle the expected input format and include retrieval
                from langchain.schema.runnable import RunnableLambda
                
                def _map_inputs_for_chain(inputs):
                    """Map inputs to the expected format for the RAG chain with smart cURL generation."""
                    question = inputs.get("input", inputs.get("question", ""))
                    
                    # SMART cURL GENERATION CHECK
                    if "create" in question.lower() and "curl" in question.lower():
                        print(f"DEBUG: Smart cURL generation detected in reloaded chain")
                        try:
                            # Get documents directly from Weaviate for cURL generation
                            result = client.query.get(primary_class, ["page_content", "text", "endpoint", "http_method", "title"]).with_limit(20).do()
                            
                            if 'errors' in result:
                                # Fallback to RAG_V1 class
                                result = client.query.get("RAG_V1", ["text", "h1", "h2", "h3", "h4", "source"]).with_limit(20).do()
                            
                            # Convert to Document objects
                            from langchain_core.documents import Document
                            documents = []
                            get_data = result.get("data", {}).get("Get", {})
                            if get_data:
                                available_classes = list(get_data.keys())
                                if available_classes:
                                    actual_class = available_classes[0]
                                    docs = get_data.get(actual_class, [])
                                    for doc in docs:
                                        props = doc.get("properties", {})
                                        content = props.get("text", props.get("page_content", ""))
                                        if content:
                                            documents.append(Document(
                                                page_content=content,
                                                metadata={
                                                    "title": props.get("h1", props.get("title", "")),
                                                    "endpoint": props.get("h2", ""),
                                                    "http_method": props.get("h3", "")
                                                }
                                            ))
                            
                            # Generate perfect cURL using the smart function
                            curl_response = generate_perfect_curl(question, documents, None)
                            if curl_response:
                                print(f"DEBUG: Smart cURL generated successfully in reloaded chain")
                                return {
                                    "context": documents,
                                    "input": question,
                                    "curl_response": curl_response
                                }
                        except Exception as curl_error:
                            print(f"DEBUG: Smart cURL generation failed in reloaded chain: {curl_error}")
                    
                    # NORMAL DOCUMENT RETRIEVAL
                    try:
                        print(f"DEBUG: Retrieving documents for question: {question}")
                        
                        # Get documents directly from Weaviate without using the retriever
                        print(f"DEBUG: Querying Weaviate class: {primary_class}")
                        
                        # Try to get documents from the RAG_V1 class which has the actual data
                        try:
                            # First try the primary class
                            result = client.query.get(primary_class, ["page_content", "text", "endpoint", "http_method", "title"]).with_limit(50).do()
                            print(f"DEBUG: Weaviate query result keys: {list(result.keys()) if isinstance(result, dict) else 'Not a dict'}")
                            
                            if 'errors' in result:
                                print(f"DEBUG: Weaviate query had errors, trying RAG_V1 class instead")
                                # Fallback to RAG_V1 class which we know has data
                                result = client.query.get("RAG_V1", ["text", "h1", "h2", "h3", "h4", "source"]).with_limit(50).do()
                                print(f"DEBUG: Weaviate query result keys: {list(result.keys()) if isinstance(result, dict) else 'Not a dict'}")
                            
                            # Get the first available class name from the Get results
                            get_data = result.get("data", {}).get("Get", {})
                            if get_data:
                                # Convert keys to list and get the first one
                                available_classes = list(get_data.keys())
                                if available_classes:
                                    actual_class = available_classes[0]
                                    docs = get_data.get(actual_class, [])
                                    print(f"DEBUG: Using class '{actual_class}' for document retrieval")
                                else:
                                    docs = []
                                    print(f"DEBUG: No classes found in Get data")
                            else:
                                docs = []
                                print(f"DEBUG: No Get data found in result")
                            print(f"DEBUG: Raw docs from Weaviate: {len(docs) if docs else 0}")
                            
                            if docs:
                                # Convert to Document objects for context
                                from langchain_core.documents import Document
                                documents = []
                                for doc in docs:
                                    props = doc.get("properties", {})
                                    # Use 'text' field if available, otherwise 'page_content'
                                    content = props.get("text", props.get("page_content", ""))
                                    if content:
                                        documents.append(Document(
                                            page_content=content,
                                            metadata={
                                                "title": props.get("h1", props.get("title", "")),
                                                "endpoint": props.get("h2", ""),
                                                "http_method": props.get("h3", "")
                                            }
                                        ))
                                
                                context = "\n\n".join([doc.page_content for doc in documents])
                                print(f"DEBUG: Successfully retrieved {len(documents)} documents for context")
                                print(f"DEBUG: Context length: {len(context)} characters")
                            else:
                                context = "No relevant documentation found."
                                print(f"DEBUG: No documents found in Weaviate")
                                
                        except Exception as query_error:
                            print(f"DEBUG: Error in Weaviate query: {query_error}")
                            context = "Unable to retrieve documentation due to query error."
                            
                    except Exception as e:
                        print(f"DEBUG: Error retrieving documents: {e}")
                        context = "Unable to retrieve documentation."
                    
                    return {
                        "context": context,
                        "input": question
                    }
                
                # Create the base RAG chain first
                base_rag_chain = create_stuff_documents_chain(llm, prompt)
                
                # Create a custom chain that handles cURL generation bypass for reloaded data
                def _handle_curl_bypass_reloaded(x: Dict[str, Any]) -> Dict[str, Any]:
                    """Handle cURL generation bypass when perfect cURL is generated in reloaded chain"""
                    if "curl_response" in x:
                        print(f"DEBUG: Bypassing LLM with perfect cURL response in reloaded chain")
                        return x["curl_response"]
                    else:
                        # Normal flow - use the base LLM chain
                        return base_rag_chain.invoke(x)
                
                # Create the final chain with cURL bypass capability
                rag_chain = RunnableLambda(_map_inputs_for_chain) | RunnableLambda(_handle_curl_bypass_reloaded)
                
                # Test the chain to make sure it works
                try:
                    print("DEBUG: Testing reloaded RAG chain...")
                    test_result = rag_chain.invoke({
                        "input": "What is this documentation about?",
                        "chat_history": ""
                    })
                    print(f"DEBUG: Chain test successful: {str(test_result)[:100]}...")
                except Exception as test_error:
                    print(f"DEBUG: Chain test failed: {test_error}")
                    # Fallback to simple chain if complex one fails
                    rag_chain = base_rag_chain
                    print("DEBUG: Using fallback simple chain")
                
                # Update state with combined data
                state.vector_store = primary_vector_store
                state.retriever = primary_retriever
                state.rag_chain = rag_chain
                state.weaviate_client_instance = client
                state.weaviate_index_name = primary_class
                state.documents_count = total_documents
                state.last_updated = "Reloaded from existing data"
                
                if all_endpoints:
                    state.extracted_endpoints = all_endpoints
                
                print(f"✅ Successfully reloaded {total_documents} documents from {len([c for c in existing_classes if c in ['Test_API_Documentation', 'API_Documentation', 'RAG_V1']])} classes")
                return True
            else:
                print(f"DEBUG: No classes with data found")
                
        except Exception as schema_error:
            print(f"DEBUG: Error checking Weaviate schema: {schema_error}")
            
    except Exception as e:
        print(f"DEBUG: Error in reload_existing_data: {e}")
        import traceback
        print(f"DEBUG: Full traceback: {traceback.format_exc()}")
        
    return False
