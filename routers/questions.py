from fastapi import APIRouter, HTTPException
from models.requests import QuestionRequest
from models.responses import StructuredResponse
from core.state import is_ready, get_state
from utils.helpers import parse_structured_response
from langchain.memory import ConversationBufferMemory
from typing import Dict, Any
import json

router = APIRouter(prefix="/questions", tags=["questions"])

@router.post("/ask", response_model=StructuredResponse)
async def ask_question(request: QuestionRequest):
    """Ask a question about the processed documentation."""
    if not is_ready():
        return StructuredResponse(
            short_answers=[],
            descriptions=["No documentation has been processed yet. Please upload documentation first."],
            url=[],
            curl=[],
            values={"error": "no_documentation", "details": "No documentation has been processed yet. Please upload documentation first."},
            numbers={},
            memory_count=0
        )
    
    try:
        # Get current state
        state = get_state()
        rag_chain = state.get("rag_chain")
        retriever = state.get("retriever")
        
        # Check if RAG system is ready
        if not rag_chain:
            return StructuredResponse(
                short_answers=[],
                descriptions=["The RAG system is not ready. Please wait for the system to initialize or reload existing documentation."],
                url=[],
                curl=[],
                values={"error": "rag_not_ready", "details": "RAG system not initialized"},
                numbers={},
                memory_count=0
            )
        
        # Get memory for this session using the session_id
        from core.memory import get_memory_for_session
        session_id = request.session_id or "default"
        memory = get_memory_for_session(session_id)
        
        # Get chat history (last 10 messages)
        chat_history = memory.chat_memory.messages
        print(f"DEBUG: session_id: {session_id}, chat_history count: {len(chat_history)}=================")
        
        # Prepare context with proper chat history
        if chat_history:
            # TOKEN MANAGEMENT: Limit chat history to prevent token limit exceeded
            max_history_messages = 5  # Keep only last 5 messages to save tokens
            limited_history = chat_history[-max_history_messages:]
            context_with_history = {
                "input": request.question,
                "chat_history": "\n".join([f"{msg.type}: {msg.content}" for msg in limited_history])
            }
            print(f"DEBUG: Using limited chat history: {len(limited_history)} messages (from {len(chat_history)} total)")
        else:
            context_with_history = {
                "input": request.question,
                "chat_history": ""
            }
            print(f"DEBUG: No chat history available")
        
        print("DEBUG: About to invoke rag_chain...")
        try:
            # Add recursion depth protection
            import sys
            if sys.getrecursionlimit() < 1000:
                sys.setrecursionlimit(1000)
            
            result = rag_chain.invoke(context_with_history)
            print(f"DEBUG: rag_chain.invoke returned: {result}=================")
        except RecursionError as e:
            print(f"DEBUG: Recursion error during rag_chain.invoke: {e}")
            return StructuredResponse(
                short_answers=[],
                descriptions=["The system encountered a recursion error. Please try again or contact support."],
                url=[],
                curl=[],
                values={"error": "recursion_error", "details": "Maximum recursion depth exceeded"},
                numbers={},
                memory_count=len(memory.chat_memory.messages)
            )
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
        print(f"DEBUG: answer type: {type(answer)}")
        print(f"DEBUG: answer length: {len(answer) if isinstance(answer, str) else 'N/A'}")
        print(f"DEBUG: answer starts with '{{': {answer.strip().startswith('{') if isinstance(answer, str) else False}")
        print(f"DEBUG: answer ends with '}}': {answer.strip().endswith('}') if isinstance(answer, str) else False}")
        

        
        # Save conversation in memory
        memory.chat_memory.add_user_message(request.question)
        memory.chat_memory.add_ai_message(answer)
        print(f"DEBUG: Memory updated - User message: {request.question[:50]}..., AI message: {answer[:50]}...")
        print(f"DEBUG: Memory count after update: {len(memory.chat_memory.messages)}")
        
        # Parse the response directly (expects valid JSON per prompt). If the model
        # accidentally returns JSON-as-string under the "answer" key, unwrap it.
        structured_content = {}
        
        try:
            # First try to parse the entire response as JSON
            parsed = json.loads(answer) if isinstance(answer, str) else answer
            print(f"DEBUG: Initial JSON parse successful: {type(parsed)}")
            
            if isinstance(parsed, dict):
                # Check if the "answer" field contains a JSON string that needs unwrapping
                if "answer" in parsed and isinstance(parsed["answer"], str):
                    inner = parsed["answer"].strip()
                    print(f"DEBUG: Found answer field with string, length: {len(inner)}")
                    print(f"DEBUG: Starts with {{: {inner.startswith('{')}, Ends with }}: {inner.endswith('}')}")
                    
                    if inner.startswith("{") and inner.endswith("}"):
                        try:
                            # Try to parse the inner JSON
                            inner_parsed = json.loads(inner)
                            if isinstance(inner_parsed, dict):
                                print("DEBUG: Successfully unwrapped inner JSON")
                                # Use the unwrapped JSON
                                structured_content = inner_parsed
                            else:
                                print("DEBUG: Inner JSON is not a dict, using outer structure")
                                structured_content = parsed
                        except json.JSONDecodeError as e:
                            print(f"DEBUG: Inner JSON parsing failed: {e}")
                            # If inner JSON is malformed, use the outer structure
                            structured_content = parsed
                    else:
                        print("DEBUG: Answer field doesn't look like JSON, using outer structure")
                        structured_content = parsed
                else:
                    print("DEBUG: No answer field or not a string, using parsed structure")
                    structured_content = parsed
            else:
                print("DEBUG: Parsed result is not a dict, wrapping as answer")
                structured_content = {"answer": str(parsed)}
                
        except json.JSONDecodeError as e:
            print(f"DEBUG: Initial JSON parsing failed: {e}")
            # If JSON parsing fails, wrap the raw text
            structured_content = {
                "answer": answer if isinstance(answer, str) else str(answer),
                "description": "",
                "endpoints": [],
                "code_examples": None,
                "links": []
            }
        
        print(f"DEBUG: Final structured_content: {structured_content}")
        
        # Ensure all required fields exist with proper defaults
        structured_content = {
            "answer": structured_content.get("answer", ""),
            "description": structured_content.get("description", ""),
            "endpoints": structured_content.get("endpoints", []),
            "code_examples": structured_content.get("code_examples", None),
            "links": structured_content.get("links", [])
        }
        
        # Convert endpoints to EndpointInfo objects
        endpoints = []
        for endpoint_data in structured_content.get("endpoints", []):
            if isinstance(endpoint_data, dict):
                from models.responses import EndpointInfo
                endpoints.append(EndpointInfo(
                    method=endpoint_data.get("method", ""),
                    url=endpoint_data.get("url", ""),
                    params=endpoint_data.get("params"),
                    response_example=endpoint_data.get("response_example")
                ))
        
        # Convert code_examples to CodeExamples object
        code_examples = None
        if structured_content.get("code_examples"):
            from models.responses import CodeExamples
            code_examples = CodeExamples(
                curl=structured_content["code_examples"].get("curl"),
                python=structured_content["code_examples"].get("python"),
                javascript=structured_content["code_examples"].get("javascript")
            )
        
        # Return the response
        return StructuredResponse(
            answer=structured_content.get("answer", ""),
            description=structured_content.get("description", ""),
            endpoints=endpoints,
            code_examples=code_examples,
            links=structured_content.get("links", []),
            memory_count=len(memory.chat_memory.messages)
        )
    
    except Exception as e:
        error_message = f"Error processing question: {str(e)}"
        print(f"DEBUG: {error_message}")
        return StructuredResponse(
            answer=f"Error: {error_message}",
            description="An error occurred while processing your question.",
            endpoints=[],
            code_examples=None,
            links=[],
            memory_count=0
        )
