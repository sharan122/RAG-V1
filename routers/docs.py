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
                model="claude-3-5-haiku-20241022",
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
ANTHROPIC_MODEL = os.getenv("ANTHROPIC_MODEL", "claude-3-5-haiku-20241022")

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
    """Process API documentation and create RAG system efficiently."""
    import core.state as state
    
    try:
        # Strip yaml front matter and store raw text
        raw = re.sub(r"^---\n.*?\n---\n", "", request.content, flags=re.DOTALL)
        state.raw_document_text = raw
        print(f"Processing document: {len(raw)} characters")

        # ENHANCED CHUNKING STRATEGY - Multi-level chunking for better context
        # First: Split by major sections to preserve API structure
        major_sections = [("#", "h1"), ("##", "h2")]
        major_splitter = MarkdownHeaderTextSplitter(headers_to_split_on=major_sections)
        major_docs = major_splitter.split_text(raw)
        
        # Second: Create detailed chunks with better separators
        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=1500,           # Smaller chunks for better precision
            chunk_overlap=300,         # Good overlap for context
            separators=[
                "\n\n## ",             # API section headers
                "\n\n### ",            # Endpoint headers
                "\n\n",                # Paragraph breaks
                "\n",                  # Line breaks
                " ",                   # Word breaks
                ""                     # Character breaks
            ],
            length_function=len,
            is_separator_regex=False
        )
        
        # Process each major section
        all_chunks = []
        for major_doc in major_docs:
            section_chunks = text_splitter.split_documents([major_doc])
            all_chunks.extend(section_chunks)
        
        chunks = all_chunks
        print(f"Created {len(chunks)} chunks")
        
        # Enrich chunks with metadata
        for i, chunk in enumerate(chunks):
            chunk.metadata.update({
                "source": request.title,
                "chunk_index": i,
                "chunk_size": len(chunk.page_content),
                "section_path": build_section_path(chunk.metadata)
            })
        
        # Filter out low-quality chunks (keep all valid content)
        valid_chunks = []
        for chunk in chunks:
            content = chunk.page_content.strip()
            # Only reject if extremely short or clearly broken
            if len(content) >= 50 and not any(pattern in content for pattern in ["}\n]\n```", "wABEgEAAAADAOz_"]):
                valid_chunks.append(chunk)
        
        chunks = valid_chunks
        print(f"Valid chunks after filtering: {len(chunks)}")
        
        # Fallback if too few chunks
        if len(chunks) < 10:
            print("Creating fallback chunks with larger size")
            fallback_splitter = RecursiveCharacterTextSplitter(
                chunk_size=4000,
                chunk_overlap=800,
                separators=["\n\n", "\n", " ", ""]
            )
            chunks = fallback_splitter.split_documents([Document(page_content=raw, metadata={"source": request.title})])
            print(f"Fallback chunks created: {len(chunks)}")

        # Initialize embeddings and Weaviate
        print("Initializing embeddings and Weaviate...")
        embeddings = CohereEmbeddings(model="embed-english-v3.0")
        index_name = sanitize_index_name(request.title)
        client = weaviate_client.Client(url=WEAVIATE_URL)
        
        # Test connections
        client.is_ready()
        print("✅ Connections successful")
        
        # Store globally
        state.weaviate_client_instance = client
        state.weaviate_index_name = index_name

        # Extract endpoints and base URL
        print("Extracting endpoints...")
        structured_eps = attempt_parse_openapi(raw)
        text_eps = extract_endpoints_from_text(raw)
        llm_eps_raw = _llm_recall_endpoints_full(raw)
        
        # Merge and validate endpoints
        merged: Dict[str, Dict[str, Any]] = {}
        all_endpoint_sources = structured_eps + text_eps + llm_eps_raw
        
        for e in all_endpoint_sources:
            key = f"{e.get('http_method')} {e.get('endpoint')}"
            if key not in merged and e.get('http_method') and e.get('endpoint'):
                merged[key] = e
        
        state.extracted_endpoints = list(merged.values())
        state.detected_base_url = detect_base_url_from_text(raw)
        state.base_urls_detected = extract_all_base_urls(raw)
        state.curl_examples_total_count = len(_extract_curl_blocks_from_text(raw))
        
        print(f"Found {len(state.extracted_endpoints)} endpoints")

        # Create endpoint documents
        endpoint_docs: List[Document] = []
        for e in state.extracted_endpoints:
            endpoint_doc = Document(
                page_content=f"### {e['http_method']} {e['endpoint']}\n{e.get('summary', '')}",
                metadata={
                    "source": request.title,
                    "title": f"{e['http_method']} {e['endpoint']}",
                    "endpoint": e["endpoint"],
                    "http_method": e["http_method"],
                    "base_url": state.detected_base_url,
                    "section": "endpoint",
                }
            )
            endpoint_docs.append(endpoint_doc)

        # Combine all documents
        all_docs: List[Document] = chunks + endpoint_docs
        print(f"Total documents to store: {len(all_docs)}")
        
        # Store in Weaviate
        print("Storing documents in Weaviate...")
        vector_store = WeaviateStore.from_documents(
            documents=all_docs,
            embedding=embeddings,
            client=client,
            index_name=index_name,
            text_key="page_content",
        )
        
        # Verify storage
        stored_count = len(client.query.get(index_name, ["page_content"]).with_limit(1000).do().get("data", {}).get("Get", {}).get(index_name, []))
        print(f"✅ Stored {stored_count} documents in Weaviate")
        
        # Store in global state with MMR retrieval for better diversity
        state.vector_store = vector_store
        state.retriever = vector_store.as_retriever(
            search_type="mmr",
            search_kwargs={
                "k": 8,                    # Final number of documents
                "fetch_k": 20,             # Number of documents to fetch before MMR
                "lambda_mult": 0.7         # Balance between relevance and diversity
            }
        )
        state.documents_count = len(all_docs)
        state.db_size_mb = len(raw) / (1024 * 1024)

        # Create RAG chain
        print("Creating RAG chain...")
        llm = ChatAnthropic(model=ANTHROPIC_MODEL, temperature=0.2, max_tokens=600)
        
        # Read prompt from file
        try:
            with open("prompts/question_prompt.txt", "r", encoding="utf-8") as f:
                question_prompt = f.read()
        except FileNotFoundError:
            question_prompt = """You are an expert API documentation assistant. Answer based on the provided context.

Respond with JSON format:
{{
  "short_answers": ["brief answer"],
  "descriptions": ["detailed description"],
  "url": ["https://example.com/api"],
  "curl": ["curl -X GET 'https://api.example.com/endpoint'"],
  "values": {{"key": "value"}},
  "numbers": {{"count": 5}}
}}

Context: {context}
Question: {input}
Respond with ONLY the JSON object."""

        prompt = ChatPromptTemplate.from_template(question_prompt)
        doc_chain = create_stuff_documents_chain(llm=llm, prompt=prompt)
        
        # Enhanced retriever mapping with query expansion
        def _map_inputs(x: Dict[str, Any]) -> Dict[str, Any]:
            user_input = x.get("input", "")
            
            # Query expansion for better retrieval
            expanded_queries = [user_input]
            
            # Add API-specific query variations
            if any(word in user_input.lower() for word in ["api", "endpoint", "request"]):
                expanded_queries.extend([
                    f"REST API {user_input}",
                    f"HTTP {user_input}",
                    f"API documentation {user_input}"
                ])
            
            # Add method-specific queries
            if "get" in user_input.lower():
                expanded_queries.append(user_input.replace("get", "retrieve fetch"))
            if "post" in user_input.lower():
                expanded_queries.append(user_input.replace("post", "create add"))
            if "put" in user_input.lower():
                expanded_queries.append(user_input.replace("put", "update modify"))
            if "delete" in user_input.lower():
                expanded_queries.append(user_input.replace("delete", "remove"))
            
            # Retrieve documents using expanded queries
            all_docs = []
            for query in expanded_queries[:3]:  # Limit to 3 queries to avoid token limits
                docs = state.retriever.invoke(query)
                all_docs.extend(docs)
            
            # Remove duplicates while preserving order
            seen = set()
            unique_docs = []
            for doc in all_docs:
                doc_id = hash(doc.page_content)
                if doc_id not in seen:
                    seen.add(doc_id)
                    unique_docs.append(doc)
            
            # Limit to top 8 most relevant documents
            docs = unique_docs[:8]
            
            return {
                "context": docs,
                "input": user_input,
                "chat_history": x.get("chat_history", "")
            }
        
        state.rag_chain = RunnableLambda(_map_inputs) | doc_chain
        state.last_updated = time.strftime('%Y-%m-%d %H:%M:%S', time.gmtime())
        
        print("✅ RAG system created successfully")
        return SuccessResponse(
            message=f"Documentation processed successfully. Created {len(all_docs)} chunks and found {len(state.extracted_endpoints)} endpoints.",
            data={
                "chunks": len(all_docs),
                "endpoints": len(state.extracted_endpoints),
                "db_size_mb": round(state.db_size_mb, 2)
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
                "documents_count": state.documents_count
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
                    model="claude-3-5-haiku-20241022",
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
