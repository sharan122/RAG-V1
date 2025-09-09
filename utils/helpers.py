import re
import json
from typing import Dict, Any, List, Optional

def parse_explicit_endpoint(question: str) -> Optional[Dict[str, str]]:
    """Parse patterns like 'GET /users/{id}' from the question."""
    # First try explicit method + path pattern
    import re
    m = re.search(r"(?im)\b(GET|POST|PUT|PATCH|DELETE|OPTIONS|HEAD)\s+(/[^\s#]+)", question)
    if m:
        return {"http_method": m.group(1).upper(), "endpoint": m.group(2)}
    
    # Then try to extract just the method if no path is specified
    # This helps with queries like "generate curl for PUT endpoints"
    method_match = re.search(r"(?im)\b(GET|POST|PUT|PATCH|DELETE|OPTIONS|HEAD)\b", question)
    if method_match:
        return {"http_method": method_match.group(1).upper(), "endpoint": None}
    
    return None

def detect_intent(question: str) -> str:
    """Simple intent detector: list_apis | get_payload | find_curl | generate_curl | count_apis | list_base_urls | comprehensive_list | other."""
    q = question.lower()
    
    # COMPREHENSIVE LISTING INTENT - HIGHEST PRIORITY
    if any(sig in q for sig in [
        "all apis", "all endpoints", "complete list", "full list", "entire api", "every endpoint", 
        "list all", "show all", "display all", "enumerate all", "comprehensive list", "complete api list"
    ]) or (
        ("all" in q or "complete" in q or "full" in q or "entire" in q) and 
        any(tok in q for tok in ["api", "endpoint", "list", "show", "display"])
    ):
        return "comprehensive_list"
    
    # REGULAR LISTING INTENT
    if any(sig in q for sig in [
        "list apis", "list endpoints", "list api endpoints", "available apis", "available endpoints", "api list", "endpoints list"
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

def determine_response_type(content: Dict[str, Any]) -> str:
    """Determine the response type based on new fixed JSON structure."""
    if content.get("type") == "error":
        return "error"
    elif content.get("curl") and len(content.get("curl", [])) > 0:
        return "curl"
    elif content.get("url") and len(content.get("url", [])) > 0:
        return "urls"
    elif content.get("values") and len(content.get("values", {})) > 0:
        return "values"
    elif content.get("numbers") and len(content.get("numbers", {})) > 0:
        return "numbers"
    elif content.get("short_answers") and len(content.get("short_answers", [])) > 0:
        return "short_answers"
    elif content.get("descriptions") and len(content.get("descriptions", [])) > 0:
        return "descriptions"
    else:
        return "simple"

def parse_structured_response(text: str) -> Dict[str, Any]:
    """Parse structured response from LLM output."""
    try:
        return json.loads(text)
    except:
        return {
            "answer": text,
            "description": "",
            "endpoints": [],
            "code_examples": None,
            "links": []
        }

def post_process_answer(answer: str) -> str:
    """Post-process LLM answer for better formatting."""
    # Add spacing around headers
    answer = re.sub(r'([^\n])(##)', r'\1\n\n\2', answer)
    answer = re.sub(r'([^\n])(###)', r'\1\n\n\2', answer)
    
    # Add spacing around list items
    answer = re.sub(r'([^\n])(- )', r'\1\n\n\2', answer)
    answer = re.sub(r'([^\n])(\d+\.)', r'\1\n\n\2', answer)
    
    # Add spacing around code blocks
    answer = re.sub(r'([^\n])(```)', r'\1\n\n\2', answer)
    answer = re.sub(r'(```\n)([^\n])', r'\1\2', answer)
    
    # Add spacing around blockquotes
    answer = re.sub(r'([^\n])(>)', r'\1\n\n\2', answer)
    
    # Clean up excessive newlines
    answer = re.sub(r'\n{3,}', r'\n\n', answer)
    
    return answer.strip()

def _synthesize_curl(method: str, endpoint: str, example_body: Optional[str] = None, api_version: Optional[str] = None) -> str:
    """Synthesize a basic cURL command from method and endpoint."""
    base_url = "<BASE_URL>"
    headers = []
    
    # Add common headers
    if method in ["POST", "PUT", "PATCH"]:
        headers.append("-H 'Content-Type: application/json'")
    
    # Add API version header if specified
    if api_version:
        headers.append(f"-H 'X-Api-Version: {api_version}'")
    
    # Add authorization header (common pattern)
    headers.append("-H 'Authorization: Bearer <API_TOKEN>'")
    
    # Add x-api-key header (common pattern)
    headers.append("-H 'x-api-key: <API_KEY>'")
    
    # Build the cURL command
    curl_parts = [f"curl -X {method}"]
    curl_parts.extend(headers)
    
    # Add body for POST/PUT/PATCH
    if method in ["POST", "PUT", "PATCH"]:
        if example_body:
            curl_parts.append(f"-d '{example_body}'")
        else:
            curl_parts.append("-d '{\"key\": \"value\"}'")
    
    # Add the URL
    curl_parts.append(f"'{base_url}{endpoint}'")
    
    return " \\\n".join(curl_parts)

def _filter_curl_snippets_by_terms(snippets: List[Dict[str, Any]], method: Optional[str], endpoint: Optional[str], keyword_terms: Optional[List[str]]) -> List[Dict[str, Any]]:
    """Filter cURL snippets based on method, endpoint, and keyword terms."""
    if not snippets:
        return []
    
    filtered = []
    for snippet in snippets:
        code = snippet.get("code", "").lower()
        title = snippet.get("title", "").lower()
        
        # Check method
        if method and method.lower() not in code:
            continue
        
        # Check endpoint
        if endpoint and endpoint.lower() not in code:
            continue
        
        # Check keyword terms
        if keyword_terms:
            if not any(term.lower() in code or term.lower() in title for term in keyword_terms):
                continue
        
        filtered.append(snippet)
    
    return filtered

def _llm_filter_curl_snippets(query: str, snippets: List[Dict[str, Any]], top_k: int = 5) -> List[Dict[str, Any]]:
    """Use LLM to filter and rank cURL snippets by relevance."""
    if not snippets or len(snippets) <= top_k:
        return snippets
    
    # Simple heuristic ranking for now
    # In a full implementation, you'd use an LLM to rank these
    ranked = sorted(snippets, key=lambda x: len(x.get("code", "")), reverse=True)
    return ranked[:top_k]

def _llm_recall_endpoints(text: str) -> List[Dict[str, Any]]:
    """Use LLM to recall additional endpoints that might have been missed by regex."""
    # This is a placeholder for LLM-based endpoint extraction
    # In a full implementation, you'd use an LLM to find endpoints
    return []

def _llm_recall_endpoints_full(text: str, max_chars: int = 160000) -> List[Dict[str, Any]]:
    """Use Claude to propose additional endpoints (method + path). Returns list of dicts.
    We cap input size to avoid token limits.
    """
    try:
        from core.config import ANTHROPIC_API_KEY, ANTHROPIC_MODEL
        if not ANTHROPIC_API_KEY:
            return []
        
        snippet = text[:max_chars]
        from langchain_anthropic import ChatAnthropic
        llm = ChatAnthropic(model=ANTHROPIC_MODEL, temperature=0, max_tokens=500)
        prompt = (
            "You are reading API docs. Extract unique endpoints explicitly mentioned.\n"
            "Return STRICT JSON: {\n  \"endpoints\": [ { \"method\": \"GET|POST|...\", \"path\": \"/path\", \"summary\": \"...\" } ]\n}\n"
            "Do not invent. Only include items that actually appear in the text.\n\nDOC:\n" + snippet
        )
        resp = llm.invoke(prompt)
        text_response = getattr(resp, 'content', None) or (resp if isinstance(resp, str) else str(resp))
        import re
        m = re.search(r"\{[\s\S]*\}", text_response)
        data = json.loads(m.group(0)) if m else json.loads(text_response)
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

def _validate_endpoint_presence(text: str, method: str, endpoint: str) -> bool:
    """Validate that an endpoint actually exists in the text."""
    # Simple validation - check if method and endpoint appear together
    pattern = rf"(?im)\b{re.escape(method)}\s+{re.escape(endpoint)}\b"
    return bool(re.search(pattern, text))

def get_curl_from_docs(method: Optional[str], endpoint: Optional[str], allow_synthesis: bool = False, max_examples: int = 10, keyword_terms: Optional[List[str]] = None, api_version: Optional[str] = None) -> Dict[str, Any]:
    """Find cURL in docs stored in Weaviate. If none and allow_synthesis=True, synthesize one."""
    # This is a simplified version - in the full implementation, this would integrate with Weaviate
    # For now, return a basic synthesized cURL if synthesis is allowed
    if allow_synthesis and method and endpoint:
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
    
    return {
        "type": "error",
        "errors": ["No cURL examples found in the documentation."]
    }

def generate_curls_for_all_endpoints(api_version: Optional[str] = None) -> Dict[str, Any]:
    """Generate or retrieve cURLs for all extracted endpoints in one response."""
    # This is a simplified version - in the full implementation, this would generate cURLs for all endpoints
    return {
        "title": "cURL commands for all endpoints",
        "description": "Generated from documentation context. Replace placeholders before use.",
        "code_blocks": [],
        "tables": [],
        "lists": [],
        "links": [],
        "notes": ["This feature is not yet fully implemented in the modular version."],
        "warnings": []
    }

def generate_curl_with_claude(method: str, endpoint: str, question: str = "", additional_context: str = "") -> Dict[str, Any]:
    """Generate a properly structured cURL command using Claude."""
    # This is a simplified version - in the full implementation, this would use Claude
    curl_cmd = _synthesize_curl(method, endpoint, example_body=None, api_version=None)
    return {
        "success": True,
        "curl": curl_cmd,
        "method": method,
        "endpoint": endpoint,
        "base_url": "<BASE_URL>",
        "placeholders": {
            "base_url": "Base URL from your environment",
            "api_key": "Your API key",
            "api_token": "Your Bearer token"
        },
        "copy_ready": True,
        "generated_by": "Synthesized"
    }

def generate_curl_for_all_endpoints() -> Dict[str, Any]:
    """Generate cURL commands for all available endpoints in the documentation."""
    # This is a simplified version - in the full implementation, this would generate cURLs for all endpoints
    return {
        "success": True,
        "total_endpoints": 0,
        "base_url": "<BASE_URL>",
        "curls": [],
        "instructions": "This feature is not yet fully implemented in the modular version.",
        "placeholders": {
            "base_url": "Your API base URL",
            "api_key": "Your API key",
            "api_token": "Your Bearer token"
        }
    }

def build_endpoint_candidates_structured(limit: int = 10) -> Dict[str, Any]:
    """Return a structured table of available endpoints to help user specify target."""
    # This is a simplified version - in the full implementation, this would return actual endpoints
    return {
        "title": "Endpoint candidates",
        "description": "Specify method and path (e.g., 'POST /folders') to target an endpoint.",
        "code_blocks": [],
        "tables": [{"headers": ["Method", "Path", "Summary", "Auth", "Has cURL"], "rows": []}],
        "lists": [],
        "links": [],
        "notes": ["This feature is not yet fully implemented in the modular version."],
        "warnings": []
    }

def build_section_path(metadata: Dict[str, Any]) -> str:
    """Build a breadcrumb-like section path from markdown header metadata."""
    keys_order = ["h1", "h2", "h3", "h4", "h5", "h6", "section", "title"]
    parts: List[str] = []
    for key in keys_order:
        if key in metadata and metadata[key]:
            parts.append(str(metadata[key]))
    return " > ".join(parts)

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

def build_catalog_text(title: str, endpoints: List[Dict[str, Any]]) -> str:
    """Create a synthetic API catalog markdown-like text for fast listing."""
    lines = [f"## {title} - API Catalog", "", "Method | Path | Summary | Auth | Has cURL", "---|---|---|---|---"]
    for e in endpoints:
        lines.append(f"{e.get('http_method','')} | {e.get('endpoint','')} | {e.get('summary','')} | {e.get('auth','')} | {str(e.get('has_curl', False))}")
    return "\n".join(lines)

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

def sanitize_index_name(name: str) -> str:
    """Sanitize index name for Weaviate."""
    import re
    s = re.sub(r'[^0-9a-zA-Z]', '_', name).strip('_')
    if not s:
        s = "RAGDocs"
    if not s[0].isalpha():
        s = "RAG_" + s
    return s[0].upper() + s[1:]
