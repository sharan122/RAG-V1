import os
from dotenv import load_dotenv
import re
import json
import time
import sys
from typing import List, Optional, Dict, Any
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from langchain_text_splitters import MarkdownHeaderTextSplitter
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.schema import Document
from langchain_cohere import CohereEmbeddings
from langchain_anthropic import ChatAnthropic
from langchain_community.vectorstores import Weaviate
from langchain_core.prompts import ChatPromptTemplate
from langchain.chains.combine_documents import create_stuff_documents_chain
from langchain.chains import create_retrieval_chain
from langchain.memory import ConversationBufferMemory
import weaviate as weaviate_client

import weaviate as weaviate_client
from langchain_community.vectorstores import Weaviate as WeaviateStore

# Load environment variables
load_dotenv()
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
COHERE_API_KEY = os.getenv("COHERE_API_KEY")
WEAVIATE_URL = os.getenv("WEAVIATE_URL", "http://127.0.0.1:8080")
WEAVIATE_INDEX_NAME = os.getenv("WEAVIATE_INDEX_NAME", "RAGDocs")
ANTHROPIC_MODEL = os.getenv("ANTHROPIC_MODEL", "claude-3-haiku-20240307")

if ANTHROPIC_API_KEY:
    os.environ["ANTHROPIC_API_KEY"] = ANTHROPIC_API_KEY
if COHERE_API_KEY:
    os.environ["COHERE_API_KEY"] = COHERE_API_KEY

app = FastAPI(title="RAG API Documentation Assistant", version="1.0.0")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, set the React app's origin
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Pydantic models
class DocumentationRequest(BaseModel):
    content: str
    title: Optional[str] = "API Documentation"

class QuestionRequest(BaseModel):
    question: str
    show_sources: bool = True
    session_id: Optional[str] = "default"

class QuestionResponse(BaseModel):
    answer: str
    sources: List[dict]
    processing_info: dict
    memory_count: int

class StructuredResponse(BaseModel):
    type: str  # "simple", "code", "api", "list", "table", "mixed"
    content: Dict[str, Any]
    memory_count: int

class VectorDBStatus(BaseModel):
    is_ready: bool
    documents_count: int
    db_size_mb: float
    last_updated: Optional[str] = None

class MemoryStatus(BaseModel):
    active_sessions: int
    total_memories: int
    memory_size_mb: float

class ClearMemoryRequest(BaseModel):
    session_id: Optional[str] = None  # None means clear all sessions

# Global variables to store the RAG system
vector_store = None
rag_chain = None
retriever = None
documents_count = 0
db_size_mb = 0.0
last_updated = None

# Memory management
conversation_memories: Dict[str, ConversationBufferMemory] = {}

# Ingestion-time extracted structures
extracted_endpoints: List[Dict[str, Any]] = []
api_catalog_text: Optional[str] = None
detected_base_url: Optional[str] = None
curl_examples_total_count: int = 0
base_urls_detected: List[str] = []
raw_document_text: Optional[str] = None

def sanitize_index_name(name: str) -> str:
    s = re.sub(r'[^0-9a-zA-Z]', '_', name).strip('_')
    if not s:
        s = "RAGDocs"
    if not s[0].isalpha():
        s = "RAG_" + s
    return s[0].upper() + s[1:]

def get_object_size_mb(obj):
    """Calculate the size of an object in MB."""
    size = sys.getsizeof(obj)
    # For complex objects, we need to estimate better
    if hasattr(obj, '__dict__'):
        size += sum(get_object_size_mb(v) for v in obj.__dict__.values())
    return size / (1024 * 1024)  # Convert to MB

def get_memory_size_mb():
    """Calculate the total size of all conversation memories in MB."""
    total_size = 0
    for session_id, memory in conversation_memories.items():
        # Estimate memory size based on chat history
        chat_history = memory.chat_memory.messages
        for message in chat_history:
            if hasattr(message, "content"):
                total_size += len(message.content.encode('utf-8'))
            if hasattr(message, "type"):
                total_size += len(str(message.type).encode('utf-8'))
    return total_size / (1024 * 1024)

def get_memory_for_session(session_id: str) -> ConversationBufferMemory:
    """Get or create memory for a session."""
    if session_id not in conversation_memories:
        conversation_memories[session_id] = ConversationBufferMemory(
            memory_key="chat_history",
            return_messages=True
        )
    return conversation_memories[session_id]

def build_section_path(metadata: Dict[str, Any]) -> str:
    """Build a breadcrumb-like section path from markdown header metadata."""
    keys_order = ["h1", "h2", "h3", "h4", "h5", "h6", "section", "title"]
    parts: List[str] = []
    for key in keys_order:
        if key in metadata and metadata[key]:
            parts.append(str(metadata[key]))
    return " > ".join(parts)

def _get_curl_code_fence_spans(text: str) -> List[tuple]:
    """Return list of (start, end) spans for fenced code blocks that contain curl.
    This allows ignoring only cURL code fences while still parsing ```http fences.
    """
    spans: List[tuple] = []
    for m in re.finditer(r"```([a-zA-Z0-9_-]*)\n([\s\S]*?)```", text):
        lang = (m.group(1) or "").lower()
        body = m.group(2) or ""
        if "curl" in body.lower():
            spans.append((m.start(), m.end()))
    return spans

def _pos_in_spans(pos: int, spans: List[tuple]) -> bool:
    for s, e in spans:
        if s <= pos < e:
            return True
    return False

def extract_endpoints_from_text(text: str) -> List[Dict[str, Any]]:
    """Extract endpoint candidates (supports Markdown like '**POST** `/path`' as well).
    Returns list of dicts with http_method and endpoint.
    """
    endpoints: List[Dict[str, Any]] = []

    curl_spans = _get_curl_code_fence_spans(text)
    # Pattern A: Plain 'METHOD /path'
    pattern_plain = re.compile(r"(?im)\b(GET|POST|PUT|PATCH|DELETE|OPTIONS|HEAD)\s+(/[^\s`#]+)")
    # Pattern B: Markdown '**METHOD** `/path`'
    pattern_md = re.compile(r"(?is)\*\*\s*(GET|POST|PUT|PATCH|DELETE|OPTIONS|HEAD)\s*\*\*\s*`\s*(/[^`\s]+)\s*`")
    # Pattern C: 'METHOD path' where path lacks leading '/' but contains a slash, and is not a full URL
    pattern_no_slash = re.compile(r"(?im)\b(GET|POST|PUT|PATCH|DELETE|OPTIONS|HEAD)\s+([a-zA-Z][^\s`#]+/[^\s`#]+)")

    for match in pattern_plain.finditer(text):
        if _pos_in_spans(match.start(), curl_spans):
            continue
        method = match.group(1).upper()
        path = match.group(2).strip()
        window_start = max(0, match.start() - 300)
        window_end = min(len(text), match.end() + 500)
        window = text[window_start:window_end]
        has_curl = bool(re.search(r"(?im)```\s*curl|^\s*curl\s", window))
        auth = "bearer" if re.search(r"(?i)authorization|bearer|oauth|api[-_ ]?key", window) else "unknown"
        summary_match = re.search(r"(?m)^[#]{1,3}\s+.*$", window)
        summary = summary_match.group(0).lstrip('# ').strip() if summary_match else ""
        endpoints.append({
            "http_method": method,
            "endpoint": path,
            "summary": summary,
            "auth": auth,
            "has_curl": has_curl,
        })

    for match in pattern_md.finditer(text):
        if _pos_in_spans(match.start(), curl_spans):
            continue
        method = match.group(1).upper()
        path = match.group(2).strip()
        pos = match.start()
        window_start = max(0, pos - 300)
        window_end = min(len(text), pos + 500)
        window = text[window_start:window_end]
        has_curl = bool(re.search(r"(?im)```\s*curl|^\s*curl\s", window))
        auth = "bearer" if re.search(r"(?i)authorization|bearer|oauth|api[-_ ]?key", window) else "unknown"
        summary_match = re.search(r"(?m)^[#]{1,3}\s+.*$", window)
        summary = summary_match.group(0).lstrip('# ').strip() if summary_match else ""
        endpoints.append({
            "http_method": method,
            "endpoint": path,
            "summary": summary,
            "auth": auth,
            "has_curl": has_curl,
        })
    # Pattern C: Normalize missing leading '/'
    for match in pattern_no_slash.finditer(text):
        if _pos_in_spans(match.start(), curl_spans):
            continue
        method = match.group(1).upper()
        raw_path = match.group(2).strip()
        if re.match(r"(?i)^https?://", raw_path):
            continue
        path = raw_path if raw_path.startswith('/') else f"/{raw_path}"
        window_start = max(0, match.start() - 300)
        window_end = min(len(text), match.end() + 500)
        window = text[window_start:window_end]
        has_curl = bool(re.search(r"(?im)```\s*curl|^\s*curl\s", window))
        auth = "bearer" if re.search(r"(?i)authorization|bearer|oauth|api[-_ ]?key", window) else "unknown"
        summary_match = re.search(r"(?m)^[#]{1,3}\s+.*$", window)
        summary = summary_match.group(0).lstrip('# ').strip() if summary_match else ""
        endpoints.append({
            "http_method": method,
            "endpoint": path,
            "summary": summary,
            "auth": auth,
            "has_curl": has_curl,
        })
    # Deduplicate by method+path while keeping first seen summary
    dedup: Dict[str, Dict[str, Any]] = {}
    for e in endpoints:
        key = f"{e['http_method']} {e['endpoint']}"
        if key not in dedup:
            dedup[key] = e
    return list(dedup.values())

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

def _llm_recall_endpoints(raw_text: str, max_chars: int = 160000) -> List[Dict[str, Any]]:
    """Use Claude to propose additional endpoints (method + path). Returns list of dicts.
    We cap input size to avoid token limits.
    """
    try:
        snippet = raw_text[:max_chars]
        llm = ChatAnthropic(model=ANTHROPIC_MODEL, temperature=0, max_tokens=500)
        prompt = (
            "You are reading API docs. Extract unique endpoints explicitly mentioned.\n"
            "Return STRICT JSON: {\n  \"endpoints\": [ { \"method\": \"GET|POST|...\", \"path\": \"/path\", \"summary\": \"...\" } ]\n}\n"
            "Do not invent. Only include items that actually appear in the text.\n\nDOC:\n" + snippet
        )
        resp = llm.invoke(prompt)
        text = getattr(resp, 'content', None) or (resp if isinstance(resp, str) else str(resp))
        m = re.search(r"\{[\s\S]*\}", text)
        data = json.loads(m.group(0)) if m else json.loads(text)
        items = data.get("endpoints") if isinstance(data, dict) else None
        out: List[Dict[str, Any]] = []
        if isinstance(items, list):
            for it in items:
                method = str(it.get("method", "")).upper().strip()
                path = str(it.get("path", "")).strip()
                summary = str(it.get("summary", "")).strip() if it.get("summary") else ""
                if method in {"GET","POST","PUT","PATCH","DELETE","OPTIONS","HEAD"} and path:
                    if not path.startswith('/') and not re.match(r"(?i)^https?://", path):
                        path = "/" + path
                    out.append({"http_method": method, "endpoint": path, "summary": summary})
        return out
    except Exception:
        return []

def extract_all_base_urls(text: str) -> List[str]:
    """Extract all plausible base URLs from the documentation text."""
    try:
        urls = re.findall(r"https?://[a-zA-Z0-9_.:-/]+", text)
        # Deduplicate while preserving order
        seen = set()
        ordered: List[str] = []
        for u in urls:
            if u not in seen:
                seen.add(u)
                ordered.append(u)
        return ordered[:50]
    except Exception:
        return []

def attempt_parse_openapi(raw_text: str) -> List[Dict[str, Any]]:
    """Try to parse OpenAPI/Swagger content to extract endpoints. Returns same shape as extract_endpoints_from_text.
    Conservative: only acts if 'openapi:' or 'swagger:' keyword is present. Fallback returns empty list on failure.
    """
    endpoints: List[Dict[str, Any]] = []
    try:
        if 'openapi:' not in raw_text and 'swagger:' not in raw_text:
            return []
        import yaml  # PyYAML
        data = yaml.safe_load(raw_text)
        paths = data.get('paths', {}) if isinstance(data, dict) else {}
        for path, methods in paths.items():
            if not isinstance(methods, dict):
                continue
            for method, info in methods.items():
                method_upper = str(method).upper()
                if method_upper not in {"GET","POST","PUT","PATCH","DELETE","OPTIONS","HEAD"}:
                    continue
                summary = (info or {}).get('summary') or ''
                tags = (info or {}).get('tags') or []
                endpoints.append({
                    "http_method": method_upper,
                    "endpoint": path,
                    "summary": summary,
                    "auth": "unknown",
                    "has_curl": False,
                    "tags": tags,
                })
        return endpoints
    except Exception:
        return []

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

def _extract_method_and_terms(question: str) -> Dict[str, Any]:
    """Detect method tokens and simple search terms from the question for filtering list/count."""
    q = question.lower()
    method = None
    for m in ["get","post","put","patch","delete","options","head"]:
        if re.search(rf"\b{m}\b", q):
            method = m.upper()
            break
    # extract path-like fragments or keywords
    path_tokens = re.findall(r"/(?:[a-zA-Z0-9._%\-/{}]+)", question)
    words = [w for w in re.findall(r"[a-zA-Z][a-zA-Z0-9_-]{2,}", q) if w not in {"apis","endpoints","list","show","all","of","the","for","with","and","get","post","put","patch","delete","options","head","base","urls","url","count","number"}]
    terms = set([t.lower() for t in path_tokens] + words[:6])
    return {"method": method, "terms": terms}

def _filter_endpoints_for_query(endpoints: List[Dict[str, Any]], question: str) -> List[Dict[str, Any]]:
    crit = _extract_method_and_terms(question)
    method = crit["method"]
    terms: set = crit["terms"]
    results: List[Dict[str, Any]] = []
    for e in endpoints:
        if method and e.get("http_method") != method:
            continue
        if terms:
            hay = (e.get("endpoint","") + " " + e.get("summary","")) .lower()
            if not any(term in hay for term in list(terms)):
                continue
        results.append(e)
    return results or endpoints

def build_catalog_text(title: str, endpoints: List[Dict[str, Any]]) -> str:
    """Create a synthetic API catalog markdown-like text for fast listing."""
    lines = [f"## {title} - API Catalog", "", "Method | Path | Summary | Auth | Has cURL", "---|---|---|---|---"]
    for e in endpoints:
        lines.append(f"{e.get('http_method','')} | {e.get('endpoint','')} | {e.get('summary','')} | {e.get('auth','')} | {str(e.get('has_curl', False))}")
    return "\n".join(lines)

def detect_intent(question: str) -> str:
    """Simple intent detector: list_apis | get_payload | find_curl | generate_curl | count_apis | list_base_urls | other."""
    q = question.lower()
    if any(sig in q for sig in [
        "list apis", "list endpoints", "list api endpoints", "all apis", "available apis", "available endpoints", "api list", "endpoints list"
    ]) or (
        ("endpoint" in q or "endpoints" in q) and any(tok in q for tok in ["list", "show", "display", "enumerate"]) 
    ):
        return "list_apis"
    if any(sig in q for sig in [
        "payload", "request body", "request schema", "response schema", "response body", "fields required", "parameters"
    ]):
        return "get_payload"
    if "curl" in q:
        if any(sig in q for sig in ["generate", "create", "make", "build", "write"]):
            return "generate_curl"
        if any(sig in q for sig in ["find", "show", "present", "any", "existing", "example", "available", "list", "all"]):
            return "find_curl"
        # ambiguous mention of curl → generic
        return "other"
    if any(sig in q for sig in ["how many apis", "count apis", "number of apis", "api count", "endpoint count"]):
        return "count_apis"
    if any(sig in q for sig in ["base url", "base urls", "list base urls", "api url", "api urls"]):
        return "list_base_urls"
    return "other"

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

def _extract_curl_blocks_from_text(text: str) -> List[Dict[str, Any]]:
    """Extract cURL snippets from text. Returns list of {title, code}."""
    results: List[Dict[str, Any]] = []
    # Code fences first
    for m in re.finditer(r"```[a-zA-Z]*\n([\s\S]*?)```", text):
        body = m.group(1)
        if re.search(r"(?im)^\s*curl\b", body):
            results.append({"title": "cURL example", "code": body.strip()})
    # Fallback: standalone curl lines/blocks
    for m in re.finditer(r"(?im)^(\s*curl\b[\s\S]*?)(?:\n\s*\n|$)", text):
        snippet = m.group(1).strip()
        if snippet and all(snippet != r["code"] for r in results):
            results.append({"title": "cURL example", "code": snippet})
    return results

def _query_weaviate_for_curl(method: Optional[str], endpoint: Optional[str], limit: int = 20) -> List[Dict[str, Any]]:
    """Retrieve documents from Weaviate likely containing cURL examples; optionally filter by endpoint/method.
    Returns list of {title, section_path, code} entries.
    """
    try:
        if 'weaviate_client_instance' not in globals() or weaviate_client_instance is None:
            return []
        cls = weaviate_index_name if 'weaviate_index_name' in globals() and weaviate_index_name else WEAVIATE_INDEX_NAME
        props = ["page_content", "title", "section_path", "endpoint", "http_method"]
        query = weaviate_client_instance.query.get(cls, props).with_limit(limit)
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
        print(f"DEBUG: _query_weaviate_for_curl error: {err}")
        return []

def _count_curl_examples_weaviate(method: Optional[str], endpoint: Optional[str], keyword_terms: Optional[List[str]] = None) -> Optional[int]:
    """Return exact count of Weaviate objects that likely contain cURL, optionally filtered.
    This counts chunks (objects), not individual code blocks. Use only for filtered counts.
    """
    try:
        if 'weaviate_client_instance' not in globals() or weaviate_client_instance is None:
            return None
        cls = weaviate_index_name if 'weaviate_index_name' in globals() and weaviate_index_name else WEAVIATE_INDEX_NAME
        where_operands: List[Dict[str, Any]] = [
            {"path": ["page_content"], "operator": "Like", "valueString": "*curl*"}
        ]
        if endpoint:
            where_operands.append({"path": ["endpoint"], "operator": "Equal", "valueText": endpoint})
        if method:
            where_operands.append({"path": ["http_method"], "operator": "Equal", "valueText": method})
        if keyword_terms:
            for term in keyword_terms:
                like_val = f"*{term}*"
                where_operands.append({"path": ["page_content"], "operator": "Like", "valueString": like_val})
        if len(where_operands) == 1:
            where_clause = where_operands[0]
        else:
            where_clause = {"operator": "And", "operands": where_operands}
        agg = (
            weaviate_client_instance
            .query
            .aggregate(cls)
            .with_where(where_clause)
            .with_meta_count()
            .do()
        )
        count = (
            agg.get("data", {})
               .get("Aggregate", {})
               .get(cls, [{}])[0]
               .get("meta", {})
               .get("count")
        )
        return int(count) if count is not None else None
    except Exception as err:
        print(f"DEBUG: _count_curl_examples_weaviate error: {err}")
        return None

def _filter_curl_snippets_by_terms(snippets: List[Dict[str, Any]], method: Optional[str], endpoint: Optional[str], keyword_terms: Optional[List[str]]) -> List[Dict[str, Any]]:
    filtered: List[Dict[str, Any]] = []
    terms = [t.lower() for t in (keyword_terms or [])]
    for s in snippets:
        code = (s.get("code") or "").lower()
        ok = True
        if method and f"-x {method.lower()}" not in code and method.lower() not in code:
            ok = False
        if ok and endpoint and endpoint.lower() not in code:
            ok = False
        if ok and terms:
            if not any(t in code for t in terms):
                ok = False
        if ok:
            filtered.append(s)
    return filtered or snippets

def _llm_filter_curl_snippets(question: str, snippets: List[Dict[str, Any]], top_k: int = 10) -> List[Dict[str, Any]]:
    try:
        if not snippets:
            return []
        if not os.getenv("ANTHROPIC_API_KEY"):
            return snippets[:top_k]
        llm = ChatAnthropic(model=ANTHROPIC_MODEL, temperature=0, max_tokens=300)
        joined = "\n\n".join([f"### SNIPPET {i+1}\n{snip.get('code','')}" for i, snip in enumerate(snippets[:50])])
        prompt = (
            "Rank the following cURL snippets by relevance to the QUESTION. Return JSON {\"indices\":[int...]}.\n\n"
            f"QUESTION: {question}\n\nSNIPPETS:\n{joined}\n"
        )
        resp = llm.invoke(prompt)
        text = getattr(resp, 'content', None) or (resp if isinstance(resp, str) else str(resp))
        m = re.search(r"\{[\s\S]*\}", text)
        data = json.loads(m.group(0)) if m else json.loads(text)
        idxs = data.get("indices") if isinstance(data, dict) else None
        if isinstance(idxs, list):
            ranked = []
            for i in idxs:
                try:
                    ranked.append(snippets[i-1])
                except Exception:
                    pass
            return ranked[:top_k] if ranked else snippets[:top_k]
        return snippets[:top_k]
    except Exception as err:
        print(f"DEBUG: _llm_filter_curl_snippets error: {err}")
        return snippets[:top_k]

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

def hybrid_retrieve_documents(user_input: str, method: Optional[str], endpoint: Optional[str], k_candidates: int = 24, k_final: int = 8, alpha: float = 0.5) -> List[Document]:
    """Hybrid retrieval (BM25 + vector) with optional endpoint/method filter, plus reranking.
    Returns a list of langchain Documents.
    """
    try:
        if 'weaviate_client_instance' not in globals() or weaviate_client_instance is None:
            return []
        # Embed query
        query_vector = CohereEmbeddings(model="embed-english-v3.0").embed_query(user_input)
        cls = weaviate_index_name if 'weaviate_index_name' in globals() and weaviate_index_name else WEAVIATE_INDEX_NAME
        props = ["page_content", "title", "section_path", "endpoint", "http_method", "section"]
        qb = weaviate_client_instance.query.get(cls, props)
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

def _doc_mentions_x_api_key() -> bool:
    try:
        if not raw_document_text:
            return False
        return bool(re.search(r"(?i)\bx-api-key\b", raw_document_text))
    except Exception:
        return False

def _guess_headers_for_endpoint(method: str, endpoint: str, api_version: Optional[str] = None) -> Dict[str, str]:
    """Minimal headers based on extracted metadata."""
    headers: Dict[str, str] = {}
    for e in extracted_endpoints:
        if e.get("endpoint") == endpoint and e.get("http_method") == method:
            if str(e.get("auth", "")).lower() == "bearer":
                headers["Authorization"] = "Bearer <API_TOKEN>"
            break
    # Common header across docs
    if _doc_mentions_x_api_key():
        headers["x-api-key"] = "<API_KEY>"
    if method in {"POST", "PUT", "PATCH"}:
        headers["Content-Type"] = "application/json"
    if api_version:
        headers["X-Api-Version"] = api_version
    return headers

def _format_curl(method: str, url: str, headers: Dict[str, str], body: Optional[str]) -> str:
    parts: List[str] = [f"curl -X {method} {url}"]
    for k, v in headers.items():
        parts.append(f"  -H '{k}: {v}'")
    if body and body.strip():
        parts.append(f"  -d '{body.strip()}'")
    return " \\\n".join(parts)

def _synthesize_curl(method: str, endpoint: str, example_body: Optional[str] = None, api_version: Optional[str] = None) -> str:
    base = detected_base_url or "<BASE URL>"
    url = f"{base.rstrip('/')}{endpoint}"
    headers = _guess_headers_for_endpoint(method, endpoint, api_version=api_version)
    return _format_curl(method, url, headers, example_body)

def get_curl_from_docs(method: Optional[str], endpoint: Optional[str], allow_synthesis: bool = False, max_examples: int = 10, keyword_terms: Optional[List[str]] = None, api_version: Optional[str] = None) -> Dict[str, Any]:
    """Find cURL in docs stored in Weaviate. If none and allow_synthesis=True, synthesize one.

    Returns a structured content dict with code_blocks and notes on success.
    Returns an error dict if not found and synthesis not allowed or method/path missing.
    """
    # 1) Find examples in docs
    examples = _query_weaviate_for_curl(method, endpoint, limit=max_examples)
    # Fallback: scan raw docs if needed
    if not examples and raw_document_text:
        raw_examples = _extract_curl_blocks_from_text(raw_document_text)
        examples = _filter_curl_snippets_by_terms(raw_examples, method, endpoint, keyword_terms)[:max_examples]
    if examples:
        # Keyword filter and LLM re-ranking for precision
        filtered = _filter_curl_snippets_by_terms(examples, method, endpoint, keyword_terms)
        ranked = _llm_filter_curl_snippets(" ".join([str(method or ""), str(endpoint or ""), " ".join(keyword_terms or [])]).strip(), filtered, top_k=max_examples)
        code_blocks = [{"language": "bash", "title": e.get("title") or "cURL example", "code": e.get("code", "")} for e in ranked]
        notes = [f"Source section: {e.get('section_path','')}" for e in examples if e.get('section_path')]
        return {
            "title": "cURL examples",
            "description": "Found cURL examples in the documentation.",
            "code_blocks": code_blocks,
            "tables": [],
            "lists": [],
            "links": [],
            "notes": notes,
            "warnings": []
        }

    # 2) Not present
    if not allow_synthesis:
        # If no method/endpoint specified, this means user wants to see all available cURLs
        if not method and not endpoint:
            # Try to find any cURL examples in the raw document
            try:
                if 'raw_document_text' in globals() and raw_document_text:
                    raw_examples = _extract_curl_blocks_from_text(raw_document_text)
                else:
                    raw_examples = []
            except NameError:
                raw_examples = []
                if raw_examples:
                    code_blocks = [{"language": "bash", "title": e.get("title") or "cURL example", "code": e.get("code", "")} for e in raw_examples[:max_examples]]
                    return {
                        "title": "All cURL Examples Found",
                        "description": f"Found {len(code_blocks)} cURL examples in the documentation.",
                        "code_blocks": code_blocks,
                        "tables": [],
                        "lists": [],
                        "links": [],
                        "notes": [f"Total cURL examples found: {len(code_blocks)}"],
                        "warnings": []
                    }
            
            # If still no examples found, return a helpful message
            return {
                "type": "error",
                "errors": ["No cURL examples found in the documentation. Try asking to 'generate cURLs' instead."]
            }
        
        # Specific method/endpoint requested but not found
        target = f" for {method} {endpoint}" if method and endpoint else ""
        return {
            "type": "error",
            "errors": [f"No cURL example found in the documentation{target}."]
        }

    # 3) Synthesize only when explicitly allowed
    if method and endpoint:
        curl_cmd = _synthesize_curl(method, endpoint, example_body=None, api_version=api_version)
        return {
            "title": "cURL (synthesized)",
            "description": "Synthesized from documentation metadata. Replace placeholders before use.",
            "code_blocks": [{"language": "bash", "title": f"{method} {endpoint}", "code": curl_cmd}],
            "tables": [],
            "lists": [],
            "links": [],
            "notes": ["Synthesized due to missing explicit example in docs."],
            "warnings": []
        }

    return {"type": "error", "errors": ["Method and endpoint are required to generate a cURL command."]}

def generate_curls_for_all_endpoints(api_version: Optional[str] = None) -> Dict[str, Any]:
    """Generate or retrieve cURLs for all extracted endpoints in one response."""
    code_blocks: List[Dict[str, str]] = []
    notes: List[str] = []
    try:
        if 'extracted_endpoints' not in globals() or not extracted_endpoints:
            return {"type": "error", "errors": ["No endpoints found in the uploaded documentation."]}
    except NameError:
        return {"type": "error", "errors": ["No endpoints found in the uploaded documentation."]}
    for e in extracted_endpoints:
        method = e.get("http_method")
        endpoint = e.get("endpoint")
        res = get_curl_from_docs(method, endpoint, allow_synthesis=True, api_version=api_version)
        if isinstance(res, dict):
            for cb in res.get("code_blocks", []) or []:
                # Ensure title shows method + path
                title = cb.get("title") or f"{method} {endpoint}"
                code_blocks.append({"language": "bash", "title": title, "code": cb.get("code", "")})
            for n in res.get("notes", []) or []:
                if n not in notes:
                    notes.append(n)
    if not code_blocks:
        return {"type": "error", "errors": ["Unable to generate cURLs for endpoints."]}
    try:
        base_note = f"Base URL: {detected_base_url}" if detected_base_url else "Base URL: <BASE URL>"
    except NameError:
        base_note = "Base URL: <BASE URL>"
    if base_note not in notes:
        notes.append(base_note)
    return {
        "title": "cURL commands for all endpoints",
        "description": "Generated from documentation context. Replace placeholders before use.",
        "code_blocks": code_blocks,
        "tables": [],
        "lists": [],
        "links": [],
        "notes": notes,
        "warnings": []
    }

def generate_curl_with_claude(method: str, endpoint: str, question: str = "", additional_context: str = "") -> Dict[str, Any]:
    """
    Generate a properly structured cURL command using Claude.
    This function creates ready-to-copy cURL commands with proper formatting.
    
    Args:
        method: HTTP method (GET, POST, PUT, DELETE, etc.)
        endpoint: API endpoint path
        question: User's original question for context
        additional_context: Any additional context from documentation
        
    Returns:
        Dict containing the generated cURL and metadata
    """
    try:
        if not os.getenv("ANTHROPIC_API_KEY"):
            return {
                "success": False,
                "error": "Claude API key not available",
                "curl": None
            }
        
                # Get base URL from detected documentation or use placeholder
        try:
            base_url = detected_base_url or "<BASE_URL>"
        except NameError:
            base_url = "<BASE_URL>"
        
        # Build comprehensive prompt for Claude
        prompt = f"""
You are an expert API documentation specialist. Generate a properly formatted cURL command for the following API endpoint.

HTTP Method: {method}
Endpoint: {endpoint}
Base URL: {base_url}

User Question: {question}

Additional Context: {additional_context}

Requirements:
1. Create a cURL command that users can directly copy and paste
2. Use proper cURL syntax with line breaks for readability
3. Include appropriate headers based on the method and endpoint
4. Use the actual base URL if provided, otherwise use <BASE_URL> placeholder
5. Include proper placeholders for dynamic values (e.g., <API_KEY>, <USER_ID>)
6. Add comments explaining what each part does
7. Ensure the cURL is properly escaped and formatted

Generate ONLY the cURL command with comments, no other text or explanations.
Format it as a clean, copy-paste ready command.
"""

        # Use Claude to generate the cURL
        llm = ChatAnthropic(model=ANTHROPIC_MODEL, temperature=0, max_tokens=500)
        response = llm.invoke(prompt)
        
        # Extract the generated cURL
        generated_curl = getattr(response, 'content', None) or str(response)
        
        # Clean up the response - remove any markdown formatting
        generated_curl = re.sub(r'^```bash\s*', '', generated_curl)
        generated_curl = re.sub(r'^```curl\s*', '', generated_curl)
        generated_curl = re.sub(r'```\s*$', '', generated_curl)
        generated_curl = generated_curl.strip()
        
        # Ensure it starts with 'curl'
        if not generated_curl.startswith('curl'):
            # If Claude didn't generate proper cURL, create a basic one
            generated_curl = f"""curl -X {method} \\
  -H 'Content-Type: application/json' \\
  -H 'Authorization: Bearer <API_TOKEN>' \\
  {base_url}{endpoint}"""
        
        # Add common headers based on method
        if method in ["POST", "PUT", "PATCH"]:
            if "Content-Type: application/json" not in generated_curl:
                generated_curl = generated_curl.replace(
                    f"{base_url}{endpoint}",
                    f"-H 'Content-Type: application/json' \\\n  {base_url}{endpoint}"
                )
        
        # Add version header if endpoint suggests versioning
        if re.search(r'/v\d+', endpoint):
            version_match = re.search(r'/v(\d+)', endpoint)
            if version_match:
                version = f"v{version_match.group(1)}"
                if f"X-Api-Version: {version}" not in generated_curl:
                    generated_curl = generated_curl.replace(
                        f"{base_url}{endpoint}",
                        f"-H 'X-Api-Version: {version}' \\\n  {base_url}{endpoint}"
                )
        
        # Add API key header if not present
        if "x-api-key" not in generated_curl.lower() and "api_key" not in generated_curl.lower():
            generated_curl = generated_curl.replace(
                f"{base_url}{endpoint}",
                f"-H 'x-api-key: <API_KEY>' \\\n  {base_url}{endpoint}"
            )
        
        # Add sample data for POST/PUT/PATCH if not present
        if method in ["POST", "PUT", "PATCH"] and "-d" not in generated_curl:
            sample_data = {
                "POST": {"name": "Sample Name", "description": "Sample Description"},
                "PUT": {"id": "<ID>", "name": "Updated Name"},
                "PATCH": {"id": "<ID>", "status": "updated"}
            }
            
            data_json = json.dumps(sample_data.get(method, {}), indent=2)
            generated_curl = generated_curl.replace(
                f"{base_url}{endpoint}",
                f"-d '{data_json}' \\\n  {base_url}{endpoint}"
            )
        
        # Format the cURL for better readability
        formatted_curl = generated_curl.replace(" \\", " \\\n  ")
        
        return {
            "success": True,
            "curl": formatted_curl,
            "method": method,
            "endpoint": endpoint,
            "base_url": base_url,
            "placeholders": {
                "base_url": base_url if base_url != "<BASE_URL>" else "Base URL from your environment",
                "api_key": "Your API key",
                "api_token": "Your Bearer token",
                "user_id": "User ID or identifier",
                "id": "Resource ID"
            },
            "copy_ready": True,
            "generated_by": "Claude AI"
        }
        
    except Exception as e:
        print(f"Error generating cURL with Claude: {e}")
        # Fallback to basic cURL generation
        try:
            base_url = detected_base_url or "<BASE_URL>"
        except NameError:
            base_url = "<BASE_URL>"
        fallback_curl = f"""curl -X {method} \\
  -H 'Content-Type: application/json' \\
  -H 'Authorization: Bearer <API_TOKEN>' \\
  -H 'x-api-key: <API_KEY>' \\
  {base_url}{endpoint}"""
        
        if method in ["POST", "PUT", "PATCH"]:
            fallback_curl += f""" \\
  -d '{{
    "sample": "data"
  }}'"""
        
        return {
            "success": False,
            "error": str(e),
            "curl": fallback_curl,
            "method": method,
            "endpoint": endpoint,
            "base_url": base_url,
            "fallback": True
        }

def generate_curl_for_all_endpoints() -> Dict[str, Any]:
    """
    Generate cURL commands for all available endpoints in the documentation.
    Returns a comprehensive list of cURL commands for each endpoint.
    """
    try:
        try:
            if not extracted_endpoints:
                return {
                    "success": False,
                    "error": "No endpoints found in documentation",
                    "curls": []
                }
        except NameError:
            return {
                "success": False,
                "error": "No endpoints found in documentation",
                "curls": []
            }
        
        all_curls = []
        try:
            base_url = detected_base_url or "<BASE_URL>"
        except NameError:
            base_url = "<BASE_URL>"
        
        try:
            for endpoint_info in extracted_endpoints:
                method = endpoint_info.get("http_method", "GET")
                endpoint = endpoint_info.get("endpoint", "")
                summary = endpoint_info.get("summary", "")
                
                if not endpoint:
                    continue
                
                # Generate cURL for this endpoint
                curl_result = generate_curl_with_claude(
                    method=method,
                    endpoint=endpoint,
                    question=f"Generate cURL for {method} {endpoint}",
                    additional_context=summary
                )
                
                if curl_result.get("success"):
                    all_curls.append({
                        "method": method,
                        "endpoint": endpoint,
                        "summary": summary,
                        "curl": curl_result["curl"],
                        "placeholders": curl_result.get("placeholders", {}),
                        "copy_ready": True
                    })
                else:
                    # Use fallback cURL
                    all_curls.append({
                        "method": method,
                        "endpoint": endpoint,
                        "summary": summary,
                        "curl": curl_result["curl"],
                        "fallback": True,
                        "copy_ready": True
                    })
        except NameError:
            return {
                "success": False,
                "error": "No endpoints found in documentation",
                "curls": []
            }
        
        return {
            "success": True,
            "total_endpoints": len(all_curls),
            "base_url": base_url,
            "curls": all_curls,
            "instructions": "Copy any cURL command below and replace placeholders with actual values",
            "placeholders": {
                "base_url": base_url if base_url != "<BASE_URL>" else "Your API base URL",
                "api_key": "Your API key",
                "api_token": "Your Bearer token"
            }
        }
        
    except Exception as e:
        print(f"Error generating cURLs for all endpoints: {e}")
        return {
            "success": False,
            "error": str(e),
            "curls": []
        }

def build_endpoint_candidates_structured(limit: int = 10) -> Dict[str, Any]:
    """Return a structured table of available endpoints to help user specify target."""
    try:
        if 'extracted_endpoints' not in globals() or not extracted_endpoints:
            return {
                "type": "error",
                "errors": ["No API endpoints have been extracted yet. Please upload and process documentation first."]
            }
        
        headers = ["Method", "Path", "Summary", "Auth", "Has cURL"]
        rows: List[List[str]] = []
        for e in extracted_endpoints[:limit]:
            rows.append([
                e.get("http_method", ""),
                e.get("endpoint", ""),
                e.get("summary", ""),
                e.get("auth", "unknown"),
                str(e.get("has_curl", False))
            ])
        return {
            "title": "Endpoint candidates",
            "description": "Specify method and path (e.g., 'POST /folders') to target an endpoint.",
            "code_blocks": [],
            "tables": [{"headers": headers, "rows": rows}],
            "lists": [],
            "links": [],
            "notes": ["Grounded in extracted documentation."],
            "warnings": []
        }
    except NameError:
        return {
            "type": "error",
            "errors": ["No API endpoints have been extracted yet. Please upload and process documentation first."]
        }

def handle_curl_query(question: str) -> Dict[str, Any]:
    """Unified cURL handler covering: find, find all, generate, generate all, count.
    Returns a structured content dict or a typed error.
    """
    q = question.lower()
    explicit = parse_explicit_endpoint(question)
    method = explicit.get("http_method") if explicit else None
    endpoint = explicit.get("endpoint") if explicit else None
    want_all = any(tok in q for tok in ["all", "each", "every"]) or any(phrase in q for phrase in ["list all", "show all", "all curls", "all curl", "every curl", "each curl"])
    is_count = any(tok in q for tok in ["how many", "count", "number of"])
    is_generate = any(tok in q for tok in ["generate", "create", "build", "write", "make"]) and "curl" in q
    is_find = ("curl" in q) and (any(tok in q for tok in ["find", "show", "present", "list", "available", "examples"]) or not is_generate)
    # Extract keyword terms (e.g., 'templates') and api version hints
    crit = _extract_method_and_terms(question)
    keyword_terms = list(crit.get("terms", []))
    ver_match = re.search(r"(?i)\bv(\d)\b|version\s*(\d)", question)
    api_version = None
    if ver_match:
        api_version = ver_match.group(1) or ver_match.group(2)

    # Count cURLs present
    if is_count:
        # Global exact count from raw docs; filtered counts via Weaviate aggregate
        if not method and not endpoint and not keyword_terms:
            try:
                total = curl_examples_total_count if 'curl_examples_total_count' in globals() else 0
            except NameError:
                total = 0
        else:
            agg_count = _count_curl_examples_weaviate(method, endpoint, keyword_terms=keyword_terms)
            total = agg_count if isinstance(agg_count, int) else 0
        return {
            "title": "cURL examples count",
            "description": "Count of cURL examples matching your query.",
            "code_blocks": [],
            "tables": [],
            "lists": [],
            "links": [],
            "notes": [
                f"Scope: {'all' if not method and not endpoint else (method or '') + ' ' + (endpoint or '')}",
            ],
            "warnings": [],
            "values": {"curl_examples_count": total}
        }

    # Find all existing cURLs in docs (no synthesis)
    # If the user says 'list curls' or 'any curls present' without a specific endpoint,
    # return all discovered examples rather than endpoint candidates.
    if is_find and (want_all or not (method or endpoint)):
        return get_curl_from_docs(None, None, allow_synthesis=False, max_examples=200, keyword_terms=keyword_terms)

    # Find cURL for a specific endpoint (no synthesis)
    if is_find and (method or endpoint):
        return get_curl_from_docs(method, endpoint, allow_synthesis=False, max_examples=20, keyword_terms=keyword_terms)

    # Generate all cURLs (synthesis allowed) using Claude
    if is_generate and want_all:
        # Use Claude to generate cURLs for all endpoints
        all_curls_result = generate_curl_for_all_endpoints()
        
        if all_curls_result.get("success"):
            code_blocks = []
            for curl_info in all_curls_result.get("curls", []):
                code_blocks.append({
                    "language": "bash",
                    "title": f"{curl_info['method']} {curl_info['endpoint']}",
                    "code": curl_info["curl"]
                })
            
            return {
                "title": "Generated cURLs for All Endpoints",
                "description": f"AI-generated cURL commands for {all_curls_result.get('total_endpoints', 0)} endpoints. Ready for copy-paste.",
                "code_blocks": code_blocks,
                "tables": [],
                "lists": [],
                "links": [],
                "notes": [
                    f"Total endpoints: {all_curls_result.get('total_endpoints', 0)}",
                    f"Base URL: {all_curls_result.get('base_url', '<BASE_URL>')}",
                    "Instructions: Copy any cURL command below and replace placeholders with actual values",
                    "Placeholders to replace:",
                    *[f"- {k}: {v}" for k, v in all_curls_result.get('placeholders', {}).items()]
                ],
                "warnings": ["These are AI-generated cURLs. Verify against your API documentation."]
            }
        else:
            # Fallback to existing method
            return generate_curls_for_all_endpoints(api_version=api_version)

    # Generate for a specific endpoint using Claude
    if is_generate and (method and endpoint):
        # Use Claude to generate a comprehensive cURL
        curl_result = generate_curl_with_claude(
            method=method,
            endpoint=endpoint,
            question=question,
            additional_context=f"Generate cURL for {method} {endpoint}"
        )
        
        if curl_result.get("success"):
            return {
                "title": f"Generated cURL for {method} {endpoint}",
                "description": "AI-generated cURL command ready for copy-paste. Replace placeholders with actual values.",
                "code_blocks": [{
                    "language": "bash",
                    "title": f"{method} {endpoint}",
                    "code": curl_result["curl"]
                }],
                "tables": [],
                "lists": [],
                "links": [],
                "notes": [
                    f"Generated by: {curl_result.get('generated_by', 'Claude AI')}",
                    f"Base URL: {curl_result.get('base_url', '<BASE_URL>')}",
                    "Placeholders to replace:",
                    *[f"- {k}: {v}" for k, v in curl_result.get('placeholders', {}).items()]
                ],
                "warnings": ["This is an AI-generated cURL. Verify against your API documentation."]
            }
        else:
            # Fallback to existing method
            return get_curl_from_docs(method, endpoint, allow_synthesis=True, keyword_terms=keyword_terms, api_version=api_version)

    # Generate cURLs for a specific method (e.g., "generate curl for PUT endpoints")
    if is_generate and method and not endpoint:
        # Check if extracted_endpoints exists
        try:
            if 'extracted_endpoints' not in globals() or not extracted_endpoints:
                return {
                    "type": "error",
                    "errors": ["No API endpoints have been extracted yet. Please upload and process documentation first."]
                }
            
            # Filter endpoints by method and generate cURLs for each
            method_endpoints = [e for e in extracted_endpoints if e.get("http_method", "").upper() == method.upper()]
            
            if not method_endpoints:
                return {
                    "type": "error",
                    "errors": [f"No endpoints found with method {method}"]
                }
        except NameError:
            return {
                "type": "error",
                "errors": ["No API endpoints have been extracted yet. Please upload and process documentation first."]
            }
        
        # Generate cURLs for all endpoints of this method
        code_blocks = []
        for endpoint_info in method_endpoints:
            curl_result = generate_curl_with_claude(
                method=method,
                endpoint=endpoint_info.get("endpoint", ""),
                question=question,
                additional_context=f"Generate cURL for {method} {endpoint_info.get('endpoint', '')}"
            )
            
            if curl_result.get("success"):
                code_blocks.append({
                    "language": "bash",
                    "title": f"{method} {endpoint_info.get('endpoint', '')}",
                    "code": curl_result["curl"]
                })
        
        if code_blocks:
            return {
                "title": f"Generated cURLs for {method} Endpoints",
                "description": f"AI-generated cURL commands for all {method} endpoints. Ready for copy-paste.",
                "code_blocks": code_blocks,
                "tables": [],
                "lists": [],
                "links": [],
                "notes": [
                    f"Total {method} endpoints: {len(code_blocks)}",
                    "Base URL: <BASE_URL>",
                    "Instructions: Copy any cURL command below and replace placeholders with actual values"
                ],
                "warnings": ["These are AI-generated cURLs. Verify against your API documentation."]
            }
        else:
            return {
                "type": "error",
                "errors": [f"Failed to generate cURLs for {method} endpoints"]
            }

    # If user wants to generate cURL but didn't specify endpoint, list candidates
    # Only show candidates if user explicitly asks for them or is confused
    if "curl" in q and is_generate and not (method and endpoint):
        # Check if user wants all cURLs or just didn't specify clearly
        if want_all or any(tok in q for tok in ["all", "each", "every", "endpoints", "apis"]):
            # User wants all cURLs, generate them instead of showing candidates
            return generate_curl_for_all_endpoints()
        elif any(tok in q for tok in ["help", "what", "which", "show", "list"]):
            # User is asking for help/guidance, show candidates
            return build_endpoint_candidates_structured(limit=15)
        else:
            # User wants to generate cURLs but wasn't specific - generate for all endpoints
            return generate_curl_for_all_endpoints()

    # Fallback to not-a-curl question
    return {"type": "error", "errors": ["This request is not recognized as a cURL-related query."]}

def detect_base_url_from_text(text: str) -> Optional[str]:
    """Heuristically detect a base URL like https://api.example.com or https://host/v1."""
    # Prefer URLs that look like API hosts
    m = re.search(r"https?://[a-zA-Z0-9_.:-]+(?:/v\d+)?", text)
    return m.group(0) if m else None

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

def parse_structured_response(answer: str) -> Dict[str, Any]:
    """Parse the LLM response and structure it into different content types."""
    lines = answer.split('\n')
    structured_content = {
        'title': '',
        'description': '',
        'code_blocks': [],
        'tables': [],
        'lists': [],
        'links': [],
        'notes': [],
        'warnings': []
    }
    
    current_section = ''
    current_code = ''
    in_code_block = False
    code_language = 'bash'
    current_list = []
    in_list = False
    
    for line in lines:
        raw_line = line
        line = line.strip()
        if not line:
            # preserve blank separation for lists/code handling
            if in_list:
                in_list = False
                if current_list:
                    structured_content['lists'].append(current_list)
                    current_list = []
            continue
            
        # Detect headers
        if line.startswith('## '):
            structured_content['title'] = line.replace('## ', '')
            continue
        elif line.startswith('### '):
            current_section = line.replace('### ', '')
            continue
            
        # Detect code blocks
        if line.startswith('```'):
            if not in_code_block:
                in_code_block = True
                code_language = line.replace('```', '').strip() or 'bash'
                current_code = ''
            else:
                in_code_block = False
                if current_code.strip():
                    structured_content['code_blocks'].append({
                        'language': code_language,
                        'code': current_code.strip(),
                        'title': current_section or 'Code'
                    })
                current_code = ''
            continue
        if in_code_block:
            current_code += raw_line + '\n'
            continue
            
        # Detect tables
        if '|' in line and '---' in line:
            # This is a table separator, skip
            continue
        if '|' in line:
            # This is a table row
            cells = [cell.strip() for cell in line.split('|') if cell.strip()]
            if len(cells) > 1:
                if not structured_content['tables']:
                    structured_content['tables'].append({
                        'headers': cells,
                        'rows': []
                    })
                else:
                    structured_content['tables'][-1]['rows'].append(cells)
                continue
                    
        # Detect lists
        if line.startswith('- ') or line.startswith('* '):
            if not in_list:
                in_list = True
                current_list = []
            current_list.append(line[2:])
            continue
        if line[:3].isdigit() and line[3:4] == '.':
            if not in_list:
                in_list = True
                current_list = []
            # remove the leading "N. "
            idx = line.find('.')
            current_list.append(line[idx+1:].strip())
            continue
        if in_list and (line.startswith('- ') or line.startswith('* ') or (line[:3].isdigit() and line[3:4]=='.')):
            # continue list (redundant but safe)
            if line.startswith('- ') or line.startswith('* '):
                current_list.append(line[2:])
            else:
                idx = line.find('.')
                current_list.append(line[idx+1:].strip())
            continue
        if in_list:
            # End of list
            in_list = False
            if current_list:
                structured_content['lists'].append(current_list)
                current_list = []
        
        # Detect notes and warnings
        if 'note:' in line.lower() or 'important:' in line.lower():
            structured_content['notes'].append(line)
            continue
        if 'warning:' in line.lower() or 'caution:' in line.lower():
            structured_content['warnings'].append(line)
            continue
            
        # Detect links
        if 'http' in line and ('api' in line.lower() or 'endpoint' in line.lower()):
            structured_content['links'].append(line)
            continue
            
        # Everything else goes to description
        if structured_content['description']:
            structured_content['description'] += '\n' + line
        else:
            structured_content['description'] = line
    
    # Handle any remaining list
    if in_list and current_list:
        structured_content['lists'].append(current_list)
    
    return structured_content

def determine_response_type(structured_content: Dict[str, Any]) -> str:
    """Determine the type of response based on content."""
    code_blocks = structured_content.get('code_blocks', [])
    tables = structured_content.get('tables', [])
    lists = structured_content.get('lists', [])
    description = structured_content.get('description', '')

    if code_blocks and not description:
        return 'code'
    elif tables and not code_blocks:
        return 'table'
    elif lists and not code_blocks:
        return 'list'
    elif code_blocks and description:
        return 'api'
    elif len(description) > 100:
        return 'explanatory'
    else:
        return 'simple'

# --- Core processing: process_documentation (Weaviate integration) ---
def process_documentation(content: str, title: str = "API Documentation") -> dict:
    global vector_store, rag_chain, retriever, documents_count, db_size_mb, last_updated
    global weaviate_client_instance, weaviate_index_name

    # Strip yaml front matter
    raw = re.sub(r"^---\n.*?\n---\n", "", content, flags=re.DOTALL)
    # Keep a copy of raw text for cURL fallback/LLM filters
    global raw_document_text
    raw_document_text = raw

    # Split using Markdown headers
    headers_to_split_on = [("#","h1"),("##","h2"),("###","h3"),("####","h4")]
    md_splitter = MarkdownHeaderTextSplitter(headers_to_split_on=headers_to_split_on)
    docs = md_splitter.split_text(raw)

    for d in docs:
        d.metadata.setdefault("source", title)

    # Enrich metadata with section_path
    for d in docs:
        d.metadata["section_path"] = build_section_path(d.metadata)

    # Chunk documents
    splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)
    chunks: List[Document] = splitter.split_documents(docs)

    # Embeddings
    embeddings = CohereEmbeddings(model="embed-english-v3.0")

    # Sanitize and set index/class name
    index_name = sanitize_index_name(title)

    # Initialize explicit Weaviate client (recommended, fixes URL/auth errors)
    client = weaviate_client.Client(url=WEAVIATE_URL)

    # Store weaviate client & index globally so clear/status can use them
    weaviate_client_instance = client
    weaviate_index_name = index_name

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
    global extracted_endpoints, api_catalog_text, detected_base_url
    # Prefer OpenAPI structured parsing if available
    structured_eps = attempt_parse_openapi(raw)
    text_eps = extract_endpoints_from_text(raw)
    # LLM-assisted recall pass with validation
    llm_eps_raw = _llm_recall_endpoints(raw)
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
    extracted_endpoints = list(merged.values())
    api_catalog_text = build_catalog_text(title, extracted_endpoints) if extracted_endpoints else None
    detected_base_url = detect_base_url_from_text(raw)
    # Collect all base URLs for list_base_urls
    try:
        global base_urls_detected
        base_urls_detected = extract_all_base_urls(raw)
    except Exception:
        base_urls_detected = []
    # Precompute total cURL example count from raw docs for exact global counts
    try:
        global curl_examples_total_count
        curl_examples_total_count = len(_extract_curl_blocks_from_text(raw))
    except Exception:
        curl_examples_total_count = 0

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
                "source": title,
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
                "source": title,
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
                "source": title,
                "title": f"{title} Catalog",
                "section_path": "API > Catalog",
                "is_catalog": True,
            }
        ))

    # Add documents (chunks + endpoint summaries + catalog)
    all_docs: List[Document] = chunks + endpoint_docs + catalog_docs
    # Create Weaviate store and import docs in one step (more reliable schema creation)
    vector_store = WeaviateStore.from_documents(
        documents=all_docs,
        embedding=embeddings,
        client=client,
        index_name=index_name,
        text_key="page_content",
    )

    # Estimate db size / docs count
    documents_count = len(all_docs)
    content_size = sum(len(c.page_content.encode('utf-8')) for c in all_docs)
    metadata_size = sum(len(str(c.metadata).encode('utf-8')) for c in all_docs)
    approx_vector_bytes = len(chunks) * 1536 * 4 if len(chunks) > 0 else 0
    total_size_bytes = approx_vector_bytes + content_size + metadata_size + (1024 * 1024)
    db_size_mb = total_size_bytes / (1024 * 1024)

    # Create retriever (same MMR config you used)
    retriever = vector_store.as_retriever(
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
                    docs = retriever.invoke(f"{explicit['http_method']} {explicit['endpoint']}\n\n{user_input}")
            else:
                docs = hybrid_retrieve_documents(user_input, None, None, k_candidates=24, k_final=8, alpha=0.5)
                if not docs:
                    docs = retriever.invoke(user_input)
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
    rag_chain = retriever_chain | doc_chain

    last_updated = time.strftime('%Y-%m-%d %H:%M:%S', time.gmtime())

    return {
        "sections": len(docs),
        "chunks": len(chunks),
        "db_size_mb": round(db_size_mb, 2),
        "message": "Documentation processed successfully"
    }

def clear_vector_database():
    """Clear the vector database and reset the RAG system (delete Weaviate class)."""
    global vector_store, rag_chain, retriever, documents_count, db_size_mb, last_updated, weaviate_index_name
    if vector_store is not None:
        try:
            client = weaviate_client.Client(url=WEAVIATE_URL)
        except Exception:
            try:
                client = weaviate_client.WeaviateClient(url=WEAVIATE_URL)
            except Exception:
                client = None
        if client is not None:
            try:
                class_to_delete = weaviate_index_name if 'weaviate_index_name' in globals() and weaviate_index_name else WEAVIATE_INDEX_NAME
                client.schema.delete_class(class_to_delete)
            except Exception:
                pass
    vector_store = None
    rag_chain = None
    retriever = None
    documents_count = 0
    db_size_mb = 0.0
    last_updated = None

def clear_conversation_memory(session_id: Optional[str] = None):
    """Clear conversation memory for a specific session or all sessions."""
    global conversation_memories
    if session_id is None:
        # Clear all sessions
        cleared = len(conversation_memories)
        conversation_memories.clear()
        return {"message": "All conversation memories cleared", "cleared_sessions": cleared}
    elif session_id in conversation_memories:
        # Clear specific session
        del conversation_memories[session_id]
        return {"message": f"Conversation memory for session '{session_id}' cleared", "cleared_sessions": 1}
    else:
        return {"message": f"Session '{session_id}' not found", "cleared_sessions": 0}

@app.post("/process-documentation")
async def process_doc(request: DocumentationRequest):
    """Process API documentation and create RAG system."""
    try:
        result = process_documentation(request.content, request.title)
        return {"success": True, "data": result}
    except Exception as e:
        return {
            "type": "error",
            "errors": [f"Error processing documentation: {str(e)}"]
        }

@app.post("/ask")
async def ask_question(request: QuestionRequest):
    """Ask a question about the processed documentation."""
    global rag_chain, retriever
    
    if rag_chain is None:
        return {
            "type": "error",
            "errors": ["No documentation has been processed yet. Please upload documentation first."]
        }
    
    try:
        # Get memory for this session
        memory = get_memory_for_session(request.session_id)
        
        # Handle list APIs intent directly to ensure proper structured table
        intent_direct = detect_intent(request.question)
        if intent_direct in {"list_apis", "count_apis", "list_base_urls"}:
            try:
                if 'extracted_endpoints' not in globals() or not extracted_endpoints:
                    return {
                        "type": "error",
                        "errors": [
                            "No documentation has been processed yet or no endpoints were extracted. Please upload the API documentation first."
                        ]
                    }
            except NameError:
                return {
                    "type": "error",
                    "errors": [
                        "No documentation has been processed yet or no endpoints were extracted. Please upload the API documentation first."
                    ]
                }
            if intent_direct == "list_apis":
                headers = ["Method", "Path", "Summary", "Auth", "Has cURL"]
                rows: List[List[str]] = []
                filtered_eps = _filter_endpoints_for_query(extracted_endpoints, request.question)
                for e in filtered_eps:
                    rows.append([
                        e.get("http_method", ""),
                        e.get("endpoint", ""),
                        e.get("summary", ""),
                        str(e.get("auth", "unknown")),
                        str(bool(e.get("has_curl", False)))
                    ])
                structured_content = {
                    "title": "API Catalog",
                    "description": "List of endpoints discovered from the uploaded docs.",
                    "tables": [{"headers": headers, "rows": rows}],
                    "code_blocks": [],
                    "lists": [],
                    "links": [],
                    "notes": [
                        f"Base URL: {detected_base_url}" if 'detected_base_url' in globals() and detected_base_url else "Base URL: <BASE URL>",
                        "Grounded in uploaded documentation."
                    ],
                    "warnings": []
                }
                memory.chat_memory.add_user_message(request.question)
                memory.chat_memory.add_ai_message(json.dumps(structured_content))
                return StructuredResponse(
                    type="table",
                    content=structured_content,
                    memory_count=len(memory.chat_memory.messages)
                )
            if intent_direct == "count_apis":
                filtered_eps = _filter_endpoints_for_query(extracted_endpoints, request.question)
                distinct = {f"{e.get('http_method','')} {e.get('endpoint','')}" for e in filtered_eps}
                structured_content = {
                    "title": "API count",
                    "description": "Distinct endpoint count (method+path).",
                    "values": {"api_count": len(distinct)},
                    "code_blocks": [],
                    "tables": [],
                    "lists": [],
                    "links": [],
                    "notes": [],
                    "warnings": []
                }
                memory.chat_memory.add_user_message(request.question)
                memory.chat_memory.add_ai_message(json.dumps(structured_content))
                return StructuredResponse(
                    type="simple",
                    content=structured_content,
                    memory_count=len(memory.chat_memory.messages)
                )
            if intent_direct == "list_base_urls":
                try:
                    urls = set(base_urls_detected or []) if 'base_urls_detected' in globals() else set()
                    if 'detected_base_url' in globals() and detected_base_url:
                        urls.add(detected_base_url)
                except NameError:
                    urls = set()
                structured_content = {
                    "title": "Base URLs",
                    "description": "Base URL(s) detected in the documentation.",
                    "lists": [[u for u in urls]] if urls else [],
                    "code_blocks": [],
                    "tables": [],
                    "links": [],
                    "notes": [],
                    "warnings": []
                }
                memory.chat_memory.add_user_message(request.question)
                memory.chat_memory.add_ai_message(json.dumps(structured_content))
                return StructuredResponse(
                    type="list" if urls else "simple",
                    content=structured_content,
                    memory_count=len(memory.chat_memory.messages)
                )

        # Handle cURL intents up-front to avoid LLM reformatting
        intent_now = detect_intent(request.question)
        if intent_now in {"find_curl", "generate_curl"}:
            result_struct = handle_curl_query(request.question)
            # Save to memory
            memory.chat_memory.add_user_message(request.question)
            memory.chat_memory.add_ai_message(json.dumps(result_struct))
            # If error dict, return as-is
            if isinstance(result_struct, dict) and result_struct.get("type") == "error":
                return result_struct
            # Normal structured return
            response_type = determine_response_type(result_struct)
            return StructuredResponse(
                type=response_type,
                content=result_struct,
                memory_count=len(memory.chat_memory.messages)
            )
        
        # Get chat history (last 10 messages)
        chat_history = memory.chat_memory.messages
        print(f"DEBUG: chat_history: {chat_history}=================")
        
        # Prepare context
        context_with_history = {
            "input": request.question,
            "chat_history": "\n".join([f"{msg.type}: {msg.content}" for msg in chat_history[-10:]])
        }
        
        print("DEBUG: About to invoke rag_chain...")
        try:
            result = rag_chain.invoke(context_with_history)
            print(f"DEBUG: rag_chain.invoke returned: {result}=================")
        except Exception as e:
            print(f"DEBUG: Exception during rag_chain.invoke: {e}")
            raise
        
        # Robust answer extraction
        answer = None
        if isinstance(result, dict):
            # Try all common keys
            for key in ["output", "answer", "text", "result", "response"]:
                if key in result and isinstance(result[key], str):
                    answer = result[key]
                    break
            if answer is None:
                # Fallback: get first string value in dict
                for v in result.values():
                    if isinstance(v, str):
                        answer = v
                        break
            if answer is None:
                answer = str(result)
        else:
            answer = str(result)
        
        print(f"DEBUG: answer: {answer}=================")
        
        # Save conversation in memory
        memory.chat_memory.add_user_message(request.question)
        memory.chat_memory.add_ai_message(answer)
        
        # Post-process answer
        def post_process_answer(answer: str) -> str:
            answer = re.sub(r'([^\n])(##)', r'\1\n\n\2', answer)
            answer = re.sub(r'([^\n])(###)', r'\1\n\n\2', answer)
            answer = re.sub(r'([^\n])(- )', r'\1\n\n\2', answer)
            answer = re.sub(r'([^\n])(\d+\.)', r'\1\n\n\2', answer)
            answer = re.sub(r'([^\n])(```)', r'\1\n\n\2', answer)
            answer = re.sub(r'(```\n)([^\n])', r'\1\2', answer)
            answer = re.sub(r'([^\n])(>)', r'\1\n\n\2', answer)
            answer = re.sub(r'\n{3,}', r'\n\n', answer)
            return answer.strip()
        
        formatted_answer = post_process_answer(answer)

        # --- Defensive Parsing ---
        try:
            structured_content = parse_structured_response(formatted_answer)
            print(f"DEBUG: structured_content after parsing: {structured_content}")
        except Exception as e:
            print(f"DEBUG: parse_structured_response failed: {e}")
            # fallback: wrap raw text
            structured_content = {"title": "", "description": formatted_answer, "code_blocks": [], "tables": [], "lists": [], "links": [], "notes": [], "warnings": []}
        
        response_type = determine_response_type(structured_content)
        
        return StructuredResponse(
            type=response_type,
            content=structured_content,
            memory_count=len(memory.chat_memory.messages)
        )
    
    except Exception as e:
        error_message = f"Error processing question: {str(e)}"
        print(f"DEBUG: {error_message}")
        return {
            "type": "error",
            "errors": [error_message]
        }


@app.post("/ask/stream")
async def ask_question_stream(request: QuestionRequest):
    """Stream a question response character by character."""
    global rag_chain, retriever
    
    if rag_chain is None:
        def error_gen():
            error_json = json.dumps({"type": "error", "errors": ["No documentation has been processed yet. Please upload documentation first."]})
            yield f"data: {error_json}\n\n"
        return StreamingResponse(error_gen(), media_type="text/event-stream")
    
    try:
        # Get memory for this session
        memory = get_memory_for_session(request.session_id)
        
        # Get chat history
        chat_history = memory.chat_memory.messages
        
        # Create context with chat history
        context_with_history = {
            "input": request.question,
            "chat_history": "\n".join([f"{msg.type}: {msg.content}" for msg in chat_history[-10:]])  # Last 10 messages
        }
        
        result = rag_chain.invoke(context_with_history)
        # Robust answer extraction (same as /ask)
        answer = None
        if isinstance(result, dict):
            for key in ["output", "answer", "text", "result", "response"]:
                if key in result and isinstance(result[key], str):
                    answer = result[key]
                    break
            if answer is None:
                for v in result.values():
                    if isinstance(v, str):
                        answer = v
                        break
            if answer is None:
                answer = str(result)
        else:
            answer = str(result)
        
        # Save the conversation to memory
        memory.chat_memory.add_user_message(request.question)
        memory.chat_memory.add_ai_message(answer)
        
        # Post-process the answer to ensure proper formatting
        def post_process_answer(answer: str) -> str:
            """Post-process the answer to improve formatting and structure."""
            # Ensure proper spacing around headers
            answer = re.sub(r'([^\n])(##)', r'\1\n\n\2', answer)
            answer = re.sub(r'([^\n])(###)', r'\1\n\n\2', answer)
            
            # Ensure proper spacing around lists
            answer = re.sub(r'([^\n])(- )', r'\1\n\n\2', answer)
            answer = re.sub(r'([^\n])(\d+\.)', r'\1\n\n\2', answer)
            
            # Ensure proper spacing around code blocks
            answer = re.sub(r'([^\n])(```)', r'\1\n\n\2', answer)
            answer = re.sub(r'(```\n)([^\n])', r'\1\2', answer)
            
            # Ensure proper spacing around tables
            answer = re.sub(r'([^\n])(\|)', r'\1\n\n\2', answer)
            
            # Fix numbered lists formatting
            answer = re.sub(r"(?<!\n)(\d+\.)", r"\n\1", answer)
            answer = re.sub(r"(?<!\n)(- )", r"\n- ", answer)
            
            # Ensure proper spacing after headers
            answer = re.sub(r'(##[^\n]*\n)([^\n])', r'\1\n\2', answer)
            answer = re.sub(r'(###[^\n]*\n)([^\n])', r'\1\n\2', answer)
            
            # Add spacing around bold text for better readability
            answer = re.sub(r'(\*\*[^*]+\*\*)', r' \1 ', answer)
            
            # Ensure proper spacing around inline code
            answer = re.sub(r'([^\s])(`[^`]+`)', r'\1 \2', answer)
            answer = re.sub(r'(`[^`]+`)([^\s])', r'\1 \2', answer)
            
            # Add spacing around important notes (blockquotes)
            answer = re.sub(r'([^\n])(>)', r'\1\n\n\2', answer)
            
            # Ensure consistent spacing for code blocks
            answer = re.sub(r'```(\w+)\n', r'```\1\n', answer)
            
            # Add spacing before and after tables
            answer = re.sub(r'(\n\|[^\n]*\|[^\n]*\n)', r'\n\n\1\n\n', answer)
            
            # Ensure proper list indentation
            answer = re.sub(r'(\n- [^\n]*\n)(- )', r'\1  \2', answer)
            answer = re.sub(r'(\n\d+\. [^\n]*\n)(\d+\. )', r'\1  \2', answer)
            
            # Clean up multiple consecutive newlines
            answer = re.sub(r'\n{3,}', r'\n\n', answer)
            
            return answer.strip()
        
        # Apply post-processing to ensure proper formatting
        formatted_answer = post_process_answer(answer)
        
        def event_stream():
            # Stream the formatted answer character by character
            for char in formatted_answer:
                yield f"data: {json.dumps({'data': char})}\n\n"
                time.sleep(0.012)  # Natural typing speed
            
            # Send memory count
            yield f"data: {json.dumps({'memory_count': len(memory.chat_memory.messages)})}\n\n"
            
            # Send end signal
            yield f"data: {json.dumps({'data': '[END]'})}\n\n"
        
        return StreamingResponse(event_stream(), media_type="text/event-stream")
    except Exception as error:
        error_message = str(error)
        def error_gen():
            error_json = json.dumps({"type": "error", "errors": [f"Error processing question: {error_message}"]})
            yield f"data: {error_json}\n\n"
        return StreamingResponse(error_gen(), media_type="text/event-stream")

@app.post("/clear-vector-db")
async def clear_vector_db():
    """Clear the vector database."""
    try:
        clear_vector_database()
        return {"success": True, "message": "Vector database cleared successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error clearing vector database: {str(e)}")

@app.post("/clear-memory")
async def clear_memory(request: ClearMemoryRequest):
    """Clear conversation memory."""
    try:
        result = clear_conversation_memory(request.session_id)
        return {"success": True, **result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error clearing memory: {str(e)}")

@app.get("/vector-db-status")
async def get_vector_db_status():
    """Get the status of the vector database."""
    return VectorDBStatus(
        is_ready=rag_chain is not None,
        documents_count=documents_count,
        db_size_mb=round(db_size_mb, 2),
        last_updated=last_updated
    )

@app.get("/memory-status")
async def get_memory_status():
    """Get the status of conversation memories."""
    total_memories = sum(len(memory.chat_memory.messages) for memory in conversation_memories.values())
    memory_size_mb = get_memory_size_mb()
    
    return MemoryStatus(
        active_sessions=len(conversation_memories),
        total_memories=total_memories,
        memory_size_mb=round(memory_size_mb, 2)
    )

@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "rag_ready": rag_chain is not None}

@app.get("/")
async def root():
    """Root endpoint with API information."""
    return {
        "message": "RAG API Documentation Assistant",
        "version": "1.0.0",
        "endpoints": {
            "POST /process-documentation": "Process API documentation",
            "POST /ask": "Ask questions about the documentation",
            "POST /ask/stream": "Stream questions about the documentation",
            "POST /clear-vector-db": "Clear vector database",
            "POST /clear-memory": "Clear conversation memory",
            "GET /vector-db-status": "Get vector database status",
            "GET /memory-status": "Get memory status",
            "GET /health": "Health check"
        }
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
