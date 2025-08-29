from fastapi import APIRouter, HTTPException
from models.requests import QuestionRequest
from models.responses import StructuredResponse
from core.state import is_ready, get_state
from utils.helpers import determine_response_type, parse_structured_response, post_process_answer
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
        
        # Post-process answer
        formatted_answer = post_process_answer(answer)

        # --- Defensive Parsing ---
        try:
            structured_content = parse_structured_response(formatted_answer)
            print(f"DEBUG: structured_content after parsing: {structured_content}")
        except Exception as e:
            print(f"DEBUG: parse_structured_response failed: {e}")
            # fallback: wrap raw text in new format
            structured_content = {
                "short_answers": [],
                "descriptions": [formatted_answer],
                "url": [],
                "curl": [],
                "values": {},
                "numbers": {}
            }
        
        # Return the new format directly
        return StructuredResponse(
            short_answers=structured_content.get("short_answers", []),
            descriptions=structured_content.get("descriptions", []),
            url=structured_content.get("url", []),
            curl=structured_content.get("curl", []),
            values=structured_content.get("values", {}),
            numbers=structured_content.get("numbers", {}),
            memory_count=len(memory.chat_memory.messages)
        )
    
    except Exception as e:
        error_message = f"Error processing question: {str(e)}"
        print(f"DEBUG: {error_message}")
        return StructuredResponse(
            short_answers=[],
            descriptions=[f"Error: {error_message}"],
            url=[],
            curl=[],
            values={"error": "internal_server_error", "details": error_message},
            numbers={},
            memory_count=0
        )
