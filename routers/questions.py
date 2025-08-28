from fastapi import APIRouter, HTTPException
from models.requests import QuestionRequest
from models.responses import StructuredResponse, ErrorResponse
from core.memory import get_memory_for_session
from utils.helpers import detect_intent, determine_response_type, parse_structured_response, post_process_answer
from utils.parser import _filter_endpoints_for_query
from typing import List, Dict, Any, Optional
import json

router = APIRouter(prefix="/questions", tags=["questions"])

# Import shared state
from core.state import is_ready, get_endpoints, get_base_url, get_curl_count, get_state


@router.post("/ask", response_model=StructuredResponse)
async def ask_question(request: QuestionRequest):
    """Ask a question about the processed documentation."""
    if not is_ready():
        return StructuredResponse(
            type="error",
            content={
                "title": "Error",
                "description": "No documentation has been processed yet. Please upload documentation first.",
                "errors": ["No documentation has been processed yet. Please upload documentation first."],
                "code_blocks": [],
                "tables": [],
                "lists": [],
                "links": [],
                "notes": [],
                "warnings": []
            },
            memory_count=0
        )
    
    # Get current state
    state = get_state()
    rag_chain = state["rag_chain"]
    retriever = state["retriever"]
    extracted_endpoints = state["extracted_endpoints"]
    detected_base_url = state["detected_base_url"]
    base_urls_detected = state["base_urls_detected"]
    curl_examples_total_count = state["curl_examples_total_count"]
    
    try:
        # Get memory for this session
        memory = get_memory_for_session(request.session_id)
        
        # Handle list APIs intent directly to ensure proper structured table
        intent_direct = detect_intent(request.question)
        if intent_direct in {"list_apis", "count_apis", "list_base_urls"}:
            if not extracted_endpoints:
                return StructuredResponse(
                    type="error",
                    content={
                        "title": "Error",
                        "description": "No documentation has been processed yet or no endpoints were extracted. Please upload the API documentation first.",
                        "errors": [
                            "No documentation has been processed yet or no endpoints were extracted. Please upload the API documentation first."
                        ],
                        "code_blocks": [],
                        "tables": [],
                        "lists": [],
                        "links": [],
                        "notes": [],
                        "warnings": []
                    },
                    memory_count=0
                )
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
                urls = set(base_urls_detected or [])
                if detected_base_url:
                    urls.add(detected_base_url)
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
            # If error dict, convert to StructuredResponse
            if isinstance(result_struct, dict) and result_struct.get("type") == "error":
                return StructuredResponse(
                    type="error",
                    content={
                        "title": "Error",
                        "description": "Error processing cURL request",
                        "errors": result_struct.get("errors", ["Unknown error"]),
                        "code_blocks": [],
                        "tables": [],
                        "lists": [],
                        "links": [],
                        "notes": [],
                        "warnings": []
                    },
                    memory_count=len(memory.chat_memory.messages)
                )
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
        return StructuredResponse(
            type="error",
            content={
                "title": "Error",
                "description": "Internal server error",
                "errors": [error_message],
                "code_blocks": [],
                "tables": [],
                "lists": [],
                "links": [],
                "notes": [],
                "warnings": []
            },
            memory_count=0
        )

def handle_curl_query(question: str) -> Dict[str, Any]:
    """Unified cURL handler covering: find, find all, generate, generate all, count.
    Returns a structured content dict or a typed error.
    """
    from utils.helpers import parse_explicit_endpoint, _extract_method_and_terms
    from utils.parser import _extract_curl_blocks_from_text
    import re
    
    q = question.lower()
    explicit = parse_explicit_endpoint(question)
    method = explicit.get("http_method") if explicit else None
    endpoint = explicit.get("endpoint") if explicit else None
    want_all = any(tok in q for tok in ["all", "each", "every"]) or any(phrase in q for phrase in ["list all", "show all", "all curls", "all curl", "every curl", "each curl"])
    is_count = any(tok in q for tok in ["how many", "count", "number of"])
    is_generate = any(tok in q for tok in ["generate", "create", "build", "write", "make"]) and "curl" in q
    is_find = ("curl" in q) and (any(tok in q for tok in ["find", "show", "present", "list", "available", "examples"]) or not is_generate)
    
    # Extract keyword terms and api version hints
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
            total = curl_examples_total_count
        else:
            from core.vectorstore import _count_curl_examples_weaviate
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
    if is_find and (want_all or not (method or endpoint)):
        from utils.helpers import get_curl_from_docs
        return get_curl_from_docs(None, None, allow_synthesis=False, max_examples=200, keyword_terms=keyword_terms)

    # Find cURL for a specific endpoint (no synthesis)
    if is_find and (method or endpoint):
        from utils.helpers import get_curl_from_docs
        return get_curl_from_docs(method, endpoint, allow_synthesis=False, max_examples=20, keyword_terms=keyword_terms)

    # Generate all cURLs (synthesis allowed) using Claude
    if is_generate and want_all:
        from utils.helpers import generate_curl_for_all_endpoints
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
            from utils.helpers import generate_curls_for_all_endpoints
            return generate_curls_for_all_endpoints(api_version=api_version)

    # Generate for a specific endpoint using Claude
    if is_generate and (method and endpoint):
        from utils.helpers import generate_curl_with_claude
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
            from utils.helpers import get_curl_from_docs
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
        from utils.helpers import generate_curl_with_claude
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
    if "curl" in q and is_generate and not (method and endpoint):
        # Check if user wants all cURLs or just didn't specify clearly
        if want_all or any(tok in q for tok in ["all", "each", "every", "endpoints", "apis"]):
            # User wants all cURLs, generate them instead of showing candidates
            from utils.helpers import generate_curl_for_all_endpoints
            return generate_curl_for_all_endpoints()
        elif any(tok in q for tok in ["help", "what", "which", "show", "list"]):
            # User is asking for help/guidance, show candidates
            from utils.helpers import build_endpoint_candidates_structured
            return build_endpoint_candidates_structured(limit=15)
        else:
            # User wants to generate cURLs but wasn't specific - generate for all endpoints
            from utils.helpers import generate_curl_for_all_endpoints
            return generate_curl_for_all_endpoints()

    # Fallback to not-a-curl question
    return {"type": "error", "errors": ["This request is not recognized as a cURL-related query."]}

@router.post("/ask/stream")
async def ask_question_stream(request: QuestionRequest):
    """Stream a question response character by character."""
    from fastapi.responses import StreamingResponse
    import json
    import time
    
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
        
        # For now, we'll use the regular ask endpoint and stream the response
        # In a full implementation, you'd want to use the actual RAG chain
        result = await ask_question(request)
        
        # Convert result to string for streaming
        if hasattr(result, 'dict'):
            result_text = json.dumps(result.dict())
        else:
            result_text = str(result)
        
        def event_stream():
            # Stream the response character by character
            for char in result_text:
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
