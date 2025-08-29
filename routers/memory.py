from fastapi import APIRouter, HTTPException
from models.requests import MemoryRequest
from models.responses import MemoryResponse, SuccessResponse
from core.memory import get_memory_for_session, clear_memory_for_session, get_memory_status, clear_all_memories, get_all_memory_sessions
from typing import List

router = APIRouter(prefix="/memory", tags=["memory"])

@router.post("/clear", response_model=SuccessResponse)
async def clear_memory(request: MemoryRequest):
    """Clear memory for a specific session."""
    try:
        success = clear_memory_for_session(request.session_id)
        if success:
            return SuccessResponse(message=f"Memory cleared for session {request.session_id}")
        else:
            raise HTTPException(status_code=404, detail=f"Session {request.session_id} not found")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to clear memory: {str(e)}")

@router.post("/clear-all", response_model=SuccessResponse)
async def clear_all_memory():
    """Clear all session memories."""
    try:
        count = clear_all_memories()
        return SuccessResponse(message=f"Cleared {count} session memories")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to clear all memories: {str(e)}")

@router.get("/status/{session_id}", response_model=MemoryResponse)
async def get_memory_status_endpoint(session_id: str):
    """Get memory status for a specific session."""
    try:
        status = get_memory_status(session_id)
        return MemoryResponse(
            session_id=status["session_id"],
            message_count=status["message_count"],
            messages=status["messages"]
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get memory status: {str(e)}")

@router.get("/sessions", response_model=List[str])
async def get_all_sessions():
    """Get list of all active session IDs."""
    try:
        return get_all_memory_sessions()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get sessions: {str(e)}")

@router.get("/test/{session_id}")
async def test_memory(session_id: str):
    """Test memory functionality for a session."""
    try:
        from core.memory import get_memory_for_session
        
        # Get memory for session
        memory = get_memory_for_session(session_id)
        
        # Add a test message
        memory.chat_memory.add_user_message("Test user message")
        memory.chat_memory.add_ai_message("Test AI response")
        
        # Get status
        from core.memory import get_memory_status
        status = get_memory_status(session_id)
        
        print(f"DEBUG: Memory test for session {session_id} - Status: {status}")
        
        return {
            "session_id": session_id,
            "test_message_added": True,
            "memory_status": status,
            "message": f"Test message added to session {session_id}"
        }
    except Exception as e:
        print(f"ERROR: Memory test failed: {e}")
        raise HTTPException(status_code=500, detail=f"Memory test failed: {str(e)}")

@router.get("/health")
async def memory_health():
    """Get memory system health status."""
    try:
        sessions = get_all_memory_sessions()
        total_messages = 0
        
        for session_id in sessions:
            status = get_memory_status(session_id)
            total_messages += status["message_count"]
        
        return {
            "status": "healthy",
            "active_sessions": len(sessions),
            "total_messages": total_messages,
            "sessions": sessions
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "error": str(e),
            "active_sessions": 0,
            "total_messages": 0
        }
