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
            "title": f"cURL for {method} {endpoint}",
            "description": "cURL command would be generated here",
            "code_blocks": [{"language": "bash", "title": f"{method} {endpoint}", "code": f"curl -X {method} <BASE_URL>{endpoint}"}],
            "tables": [],
            "lists": [],
            "links": [],
            "notes": ["This is a placeholder response"],
            "warnings": []
        }
    return {
        "title": "cURL examples",
        "description": "cURL examples would be listed here",
        "code_blocks": [],
        "tables": [],
        "lists": [],
        "links": [],
        "notes": ["This is a placeholder response"],
        "warnings": []
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

        # Split using Markdown headers
        headers_to_split_on = [("#","h1"),("##","h2"),("###","h3"),("####","h4")]
        md_splitter = MarkdownHeaderTextSplitter(headers_to_split_on=headers_to_split_on)
        docs = md_splitter.split_text(raw)

        for d in docs:
            d.metadata.setdefault("source", request.title)

        # Enrich metadata with section_path
        for d in docs:
            d.metadata["section_path"] = build_section_path(d.metadata)

        # Chunk documents
        splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)
        chunks: List[Document] = splitter.split_documents(docs)

        # Embeddings
        embeddings = CohereEmbeddings(model="embed-english-v3.0")

        # Sanitize and set index/class name
        index_name = sanitize_index_name(request.title)

        # Initialize explicit Weaviate client (recommended, fixes URL/auth errors)
        client = weaviate_client.Client(url=WEAVIATE_URL)

        # Store weaviate client & index globally so clear/status can use them
        state.weaviate_client_instance = client
        state.weaviate_index_name = index_name

        # Defer vector store creation until after we assemble all documents
        vector_store = None

        # Ensure schema exists with cosine similarity (no auto-vectorizer)
        try:
            existing = client.schema.get()
            classes = existing.get("classes", []) if isinstance(existing, dict) else []
            present = any(cls.get("class") == index_name for cls in classes)
            if not present:
                client.schema.create_class({
                    "class": index_name,
                    "description": "RAG API docs chunks",
                    "vectorizer": "none",
                    "vectorIndexType": "hnsw",
                    "vectorIndexConfig": {"distance": "cosine"},
                    "properties": [
                        {"name": "page_content", "dataType": ["text"]},
                        {"name": "title", "dataType": ["text"]},
                        {"name": "section_path", "dataType": ["text"]},
                        {"name": "endpoint", "dataType": ["text"]},
                        {"name": "http_method", "dataType": ["text"]},
                        {"name": "base_url", "dataType": ["text"]},
                        {"name": "auth", "dataType": ["text"]},
                        {"name": "tags", "dataType": ["text[]"]},
                        {"name": "has_curl", "dataType": ["boolean"]},
                        {"name": "is_catalog", "dataType": ["boolean"]},
                        {"name": "is_example", "dataType": ["boolean"]},
                        {"name": "is_param_table", "dataType": ["boolean"]},
                        {"name": "is_structured", "dataType": ["boolean"]},
                        {"name": "section", "dataType": ["text"]},
                        {"name": "source", "dataType": ["text"]}
                    ]
                })
        except Exception as err:
            print(f"DEBUG: ensure schema error: {err}")

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
        # Merge unique endpoints from structured, text, and validated LLM recall
        merged: Dict[str, Dict[str, Any]] = {}
        for e in structured_eps + text_eps + llm_eps_validated:
            key = f"{e.get('http_method')} {e.get('endpoint')}"
            if key not in merged:
                merged[key] = e
        state.extracted_endpoints = list(merged.values())
        
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
        state.vector_store = WeaviateStore.from_documents(
            documents=all_docs,
            embedding=embeddings,
            client=client,
            index_name=index_name,
            text_key="page_content",
        )

        # Estimate db size / docs count
        state.documents_count = len(all_docs)
        content_size = sum(len(c.page_content.encode('utf-8')) for c in all_docs)
        metadata_size = sum(len(str(c.metadata).encode('utf-8')) for c in all_docs)
        approx_vector_bytes = len(chunks) * 1536 * 4 if len(chunks) > 0 else 0
        total_size_bytes = approx_vector_bytes + content_size + metadata_size + (1024 * 1024)
        state.db_size_mb = total_size_bytes / (1024 * 1024)

        # Create retriever (same MMR config you used)
        state.retriever = state.vector_store.as_retriever(
            search_type="mmr",
            search_kwargs={"k": 6, "fetch_k": 24, "lambda_mult": 0.3}
        )

        # Build LLM + chain (use cheaper default model; configurable via ANTHROPIC_MODEL)
        llm = ChatAnthropic(model=ANTHROPIC_MODEL, temperature=0.2, max_tokens=600)

        SYSTEM_PROMPT = """
You are an expert technical assistant. Always respond in a structured JSON format, using key-value pairs for each type of information. Your response must be valid JSON and include only the following top-level keys as needed:

{
    "type": "simple|code|api|table|list|explanatory|error|warning|values|links|short_answer",
    "title": "string (if applicable)",
    "description": "string (main explanation or answer)",
    "code_blocks": [ { "language": "string", "code": "string", "title": "string" } ],
    "tables": [ { "headers": ["string"], "rows": [["string"]] } ],
    "lists": [ ["string"] ],
    "links": [ "string (URL)" ],
    "notes": [ "string" ],
    "warnings": [ "string" ],
    "errors": [ "string" ],
    "values": { "key": "value", ... },
    "short_answer": "string (if a brief answer is appropriate)"
}

Guidelines:
- If the user requests an explanation, set "type": "explanatory" and provide a detailed answer in "description".
- If the user requests to find, create, or get something, respond with direct, actionable information ("type": "simple", "code", "api", "table", "list", etc. as appropriate).
- Always fill in the relevant keys. If a section is not needed, omit it from the JSON.
- For errors or warnings, use the "errors" or "warnings" keys.
- For links, use the "links" key.
- For tables, use the "tables" key with headers and rows.
- For code, use "code_blocks" with language and title.
- For short answers, use "short_answer".
- For values, use the "values" key as a dictionary.
- Do not include any extra text outside the JSON object.
- Do not use markdown formatting, only valid JSON.
- If you do not know the answer, reply with:
    { "type": "error", "errors": ["I don't know based on the provided context."] }

Grounding Rules:
- Only answer using retrieved CONTEXT. If a requested fact (field, path, header, status code) is absent, state it is not found in the provided docs.
- Prefer verbatim field names and exact endpoint paths from the context.
- For cURL: if examples are missing, synthesize from the retrieved context using safe placeholders (e.g., <API_KEY>, <BASE_URL>, <VALUE>), and include necessary headers.
- Include citations in "notes" for returned elements when possible using source title and section_path.

Task Routing Hints:
- If the user asks to list APIs/endpoints, return a table with method and path, plus summaries.
- If the user asks for payloads, return request and response schemas with status codes.
- If the user asks for cURL, produce a single copyable command and a multiline variant.
"""
        # Escape braces to prevent template variable parsing inside example JSON
        SYSTEM_PROMPT = SYSTEM_PROMPT.replace("{", "{{").replace("}", "}}")
        
        HUMAN_PROMPT = """CONTEXT:
{context}

CHAT HISTORY:
{chat_history}

QUESTION:
{input}

Answer:"""
        
        prompt = ChatPromptTemplate.from_messages([
            ("system", SYSTEM_PROMPT),
            ("human", """{task_preface}\n\nCONTEXT:\n{context}\n\nCHAT HISTORY:\n{chat_history}\n\nQUESTION:\n{input}\n\nAnswer:"""),
        ])
        
        doc_chain = create_stuff_documents_chain(llm=llm, prompt=prompt)

        # --- FIX: Map retriever output to 'context' key expected by the prompt ---
        from langchain.schema.runnable import RunnableLambda
        
        def _map_inputs_for_chain(x: Dict[str, Any]) -> Dict[str, Any]:
            user_input = x.get("input", "")
            # Intent detection
            intent = detect_intent(user_input)
            # For cURL discovery: do not synthesize unless asked
            if intent in {"find_curl", "generate_curl"}:
                explicit = parse_explicit_endpoint(user_input)
                method = explicit.get("http_method") if explicit else None
                endpoint = explicit.get("endpoint") if explicit else None
                allow_synth = intent == "generate_curl"
                curl_struct = get_curl_from_docs(method, endpoint, allow_synthesis=allow_synth)
                # Return early by embedding the curl_struct as context so LLM can format
                return {
                    "context": [Document(page_content=json.dumps(curl_struct))],
                    "input": user_input,
                    "chat_history": x.get("chat_history", ""),
                    "task_preface": build_task_preface(intent, method, endpoint)
                }
            # If listing APIs, return catalog context directly
            if intent == "list_apis" and api_catalog_text:
                catalog_doc = Document(page_content=api_catalog_text, metadata={"title": "API Catalog", "is_catalog": True})
                return {
                    "context": [catalog_doc],
                    "input": user_input,
                    "chat_history": x.get("chat_history", ""),
                    "task_preface": build_task_preface(intent, None, None)
                }

            # Parse explicit endpoint to bias retrieval
            explicit = parse_explicit_endpoint(user_input)
            try:
                if explicit:
                    docs = hybrid_retrieve_documents(user_input, explicit.get("http_method"), explicit.get("endpoint"), k_candidates=24, k_final=8, alpha=0.5)
                    if not docs:
                        # fallback to retriever
                        docs = state.retriever.invoke(f"{explicit['http_method']} {explicit['endpoint']}\n\n{user_input}")
                else:
                    docs = hybrid_retrieve_documents(user_input, None, None, k_candidates=24, k_final=8, alpha=0.5)
                    if not docs:
                        docs = state.retriever.invoke(user_input)
            except Exception as retrieval_error:
                print(f"DEBUG: retriever.invoke error: {retrieval_error}")
                docs = []
            task_preface = build_task_preface(intent, explicit.get("http_method") if explicit else None, explicit.get("endpoint") if explicit else None)
            return {
                "context": docs,
                "input": user_input,
                "chat_history": x.get("chat_history", ""),
                "task_preface": task_preface
            }
        
        retriever_chain = RunnableLambda(_map_inputs_for_chain)
        state.rag_chain = retriever_chain | doc_chain

        state.last_updated = time.strftime('%Y-%m-%d %H:%M:%S', time.gmtime())

        return SuccessResponse(
            message=f"Documentation processed successfully. Created {len(all_docs)} chunks and found {len(state.extracted_endpoints)} endpoints.",
            data={
                "sections": len(docs),
                "chunks": len(all_docs),
                "db_size_mb": round(db_size_mb, 2),
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
