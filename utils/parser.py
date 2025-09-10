import re
from typing import List, Dict, Any, Optional, Tuple
from pathlib import Path

def _get_curl_code_fence_spans(text: str) -> List[Tuple[int, int]]:
    """Get start/end positions of code fences containing cURL."""
    spans = []
    for m in re.finditer(r"```[a-zA-Z]*\n([\s\S]*?)```", text):
        if re.search(r"(?im)^\s*curl\b", m.group(1)):
            spans.append((m.start(), m.end()))
    return spans

def _pos_in_spans(pos: int, spans: List[Tuple[int, int]]) -> bool:
    """Check if position is inside any of the spans."""
    for start, end in spans:
        if start <= pos <= end:
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

    for match in pattern_no_slash.finditer(text):
        if _pos_in_spans(match.start(), curl_spans):
            continue
        method = match.group(1).upper()
        path = "/" + match.group(2).strip()  # Normalize to start with /
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

    return endpoints

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

def detect_base_url_from_text(text: str) -> Optional[str]:
    """
    Heuristically detect base URL from documentation text.
    Looks for common patterns like 'http://localhost:PORT' or 'https://api.example.com'
    """
    # Common base URL patterns
    patterns = [
        r"https?://localhost:\d+",  # http://localhost:3000
        r"https?://127\.0\.0\.1:\d+",  # http://127.0.0.1:3000
        r"https?://[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}",  # https://api.example.com
        r"https?://[a-zA-Z0-9.-]+\.com",  # https://example.com
        r"https?://[a-zA-Z0-9.-]+\.org",  # https://example.org
        r"https?://[a-zA-Z0-9.-]+\.net",  # https://example.net
    ]
    
    for pattern in patterns:
        match = re.search(pattern, text)
        if match:
            return match.group(0)
    
    return None

def extract_all_base_urls(text: str) -> List[str]:
    """Extract all potential base URLs from text."""
    urls = []
    patterns = [
        r"https?://localhost:\d+",
        r"https?://127\.0\.0\.1:\d+",
        r"https?://[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}",
        r"https?://[a-zA-Z0-9.-]+\.com",
        r"https?://[a-zA-Z0-9.-]+\.org",
        r"https?://[a-zA-Z0-9.-]+\.net",
    ]
    
    for pattern in patterns:
        matches = re.findall(pattern, text)
        urls.extend(matches)
    
    return list(set(urls))  # Remove duplicates

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



def build_catalog_text(title: str, endpoints: List[Dict[str, Any]]) -> str:
    """Create a synthetic API catalog markdown-like text for fast listing."""
    lines = [f"## {title} - API Catalog", "", "Method | Path | Summary | Auth | Has cURL", "---|---|---|---|---"]
    for e in endpoints:
        lines.append(f"{e.get('http_method','')} | {e.get('endpoint','')} | {e.get('summary','')} | {e.get('auth','')} | {str(e.get('has_curl', False))}")
    return "\n".join(lines)
