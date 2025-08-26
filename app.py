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

def extract_endpoints_from_text(text: str) -> List[Dict[str, Any]]:
    """Extract endpoint candidates (supports Markdown like '**POST** `/path`' as well).
    Returns list of dicts with http_method and endpoint.
    """
    endpoints: List[Dict[str, Any]] = []

    # Pattern A: Plain 'METHOD /path'
    pattern_plain = re.compile(r"(?im)\b(GET|POST|PUT|PATCH|DELETE|OPTIONS|HEAD)\s+(/[^\s`#]+)")
    # Pattern B: Markdown '**METHOD** `/path`'
    pattern_md = re.compile(r"(?is)\*\*\s*(GET|POST|PUT|PATCH|DELETE|OPTIONS|HEAD)\s*\*\*\s*`\s*(/[^`\s]+)\s*`")

    for match in pattern_plain.finditer(text):
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
    # Deduplicate by method+path while keeping first seen summary
    dedup: Dict[str, Dict[str, Any]] = {}
    for e in endpoints:
        key = f"{e['http_method']} {e['endpoint']}"
        if key not in dedup:
            dedup[key] = e
    return list(dedup.values())

def build_catalog_text(title: str, endpoints: List[Dict[str, Any]]) -> str:
    """Create a synthetic API catalog markdown-like text for fast listing."""
    lines = [f"## {title} - API Catalog", "", "Method | Path | Summary | Auth | Has cURL", "---|---|---|---|---"]
    for e in endpoints:
        lines.append(f"{e.get('http_method','')} | {e.get('endpoint','')} | {e.get('summary','')} | {e.get('auth','')} | {str(e.get('has_curl', False))}")
    return "\n".join(lines)

def detect_intent(question: str) -> str:
    """Simple intent detector: list_apis | get_payload | find_curl | generate_curl | other."""
    q = question.lower()
    if any(sig in q for sig in [
        "list apis", "list endpoints", "all apis", "available apis", "available endpoints", "api list", "endpoints list"
    ]):
        return "list_apis"
    if any(sig in q for sig in [
        "payload", "request body", "request schema", "response schema", "response body", "fields required", "parameters"
    ]):
        return "get_payload"
    if "curl" in q:
        if any(sig in q for sig in ["generate", "create", "make", "build", "write"]):
            return "generate_curl"
        if any(sig in q for sig in ["find", "show", "present", "any", "existing", "example", "available"]):
            return "find_curl"
        return "find_curl"
    return "other"

def parse_explicit_endpoint(question: str) -> Optional[Dict[str, str]]:
    """Parse patterns like 'GET /users/{id}' from the question."""
    m = re.search(r"(?im)\b(GET|POST|PUT|PATCH|DELETE|OPTIONS|HEAD)\s+(/[^\s#]+)", question)
    if m:
        return {"http_method": m.group(1).upper(), "endpoint": m.group(2)}
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

def _query_weaviate_for_curl(method: Optional[str], endpoint: Optional[str], limit: int = 5) -> List[Dict[str, Any]]:
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
        if endpoint:
            operands.append({"path": ["endpoint"], "operator": "Equal", "valueText": endpoint})
        if method:
            operands.append({"path": ["http_method"], "operator": "Equal", "valueText": method})
        if len(operands) == 1:
            query = query.with_where(operands[0])
        elif len(operands) > 1:
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

def _guess_headers_for_endpoint(method: str, endpoint: str) -> Dict[str, str]:
    """Minimal headers based on extracted metadata."""
    headers: Dict[str, str] = {}
    for e in extracted_endpoints:
        if e.get("endpoint") == endpoint and e.get("http_method") == method:
            if str(e.get("auth", "")).lower() == "bearer":
                headers["Authorization"] = "Bearer <API_TOKEN>"
            break
    if method in {"POST", "PUT", "PATCH"}:
        headers["Content-Type"] = "application/json"
    return headers

def _format_curl(method: str, url: str, headers: Dict[str, str], body: Optional[str]) -> str:
    parts: List[str] = [f"curl -X {method} {url}"]
    for k, v in headers.items():
        parts.append(f"  -H '{k}: {v}'")
    if body and body.strip():
        parts.append(f"  -d '{body.strip()}'")
    return " \\\n".join(parts)

def _synthesize_curl(method: str, endpoint: str, example_body: Optional[str] = None) -> str:
    base = detected_base_url or "<BASE URL>"
    url = f"{base.rstrip('/')}{endpoint}"
    headers = _guess_headers_for_endpoint(method, endpoint)
    return _format_curl(method, url, headers, example_body)

def get_curl_from_docs(method: Optional[str], endpoint: Optional[str], allow_synthesis: bool = False) -> Dict[str, Any]:
    """Find cURL in docs stored in Weaviate. If none and allow_synthesis=True, synthesize one.

    Returns a structured content dict with code_blocks and notes on success.
    Returns an error dict if not found and synthesis not allowed or method/path missing.
    """
    # 1) Find examples in docs
    examples = _query_weaviate_for_curl(method, endpoint, limit=3)
    if examples:
        code_blocks = [{"language": "bash", "title": e.get("title") or "cURL example", "code": e["code"]} for e in examples]
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
        target = f" for {method} {endpoint}" if method and endpoint else ""
        return {
            "type": "error",
            "errors": [f"No cURL example found in the documentation{target}."]
        }

    # 3) Synthesize only when explicitly allowed
    if method and endpoint:
        curl_cmd = _synthesize_curl(method, endpoint, example_body=None)
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

def generate_curls_for_all_endpoints() -> Dict[str, Any]:
    """Generate or retrieve cURLs for all extracted endpoints in one response."""
    code_blocks: List[Dict[str, str]] = []
    notes: List[str] = []
    if not extracted_endpoints:
        return {"type": "error", "errors": ["No endpoints found in the uploaded documentation."]}
    for e in extracted_endpoints:
        method = e.get("http_method")
        endpoint = e.get("endpoint")
        res = get_curl_from_docs(method, endpoint, allow_synthesis=True)
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
    base_note = f"Base URL: {detected_base_url}" if detected_base_url else "Base URL: <BASE URL>"
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

    # Extract endpoints, base URL and build a synthetic catalog
    global extracted_endpoints, api_catalog_text, detected_base_url
    extracted_endpoints = extract_endpoints_from_text(raw)
    api_catalog_text = build_catalog_text(title, extracted_endpoints) if extracted_endpoints else None
    detected_base_url = detect_base_url_from_text(raw)

    # Build Documents for endpoints and catalog
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
                "auth": e.get("auth", "unknown"),
                "has_curl": e.get("has_curl", False),
                "is_catalog": False,
            }
        )
        endpoint_docs.append(endpoint_doc)

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
                # Narrow the retriever search by appending method/path tokens
                biased_query = f"{explicit['http_method']} {explicit['endpoint']}\n\n{user_input}"
                docs = retriever.invoke(biased_query)
            else:
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
        if intent_direct == "list_apis":
            if not extracted_endpoints:
                return {
                    "type": "error",
                    "errors": [
                        "No documentation has been processed yet or no endpoints were extracted. Please upload the API documentation first."
                    ]
                }
            headers = ["Method", "Path", "Summary", "Auth", "Has cURL"]
            rows: List[List[str]] = []
            for e in extracted_endpoints:
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
                    f"Base URL: {detected_base_url}" if detected_base_url else "Base URL: <BASE URL>",
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

        # Handle cURL intents up-front to avoid LLM reformatting
        intent_now = detect_intent(request.question)
        if intent_now in {"find_curl", "generate_curl"}:
            explicit = parse_explicit_endpoint(request.question)
            method = explicit.get("http_method") if explicit else None
            endpoint = explicit.get("endpoint") if explicit else None
            allow_synth = intent_now == "generate_curl"
            # If the user asks for all endpoints’ cURLs
            if allow_synth and ("all" in request.question.lower() or "each" in request.question.lower()):
                result_struct = generate_curls_for_all_endpoints()
            else:
                result_struct = get_curl_from_docs(method, endpoint, allow_synthesis=allow_synth)
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
