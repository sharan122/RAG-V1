from langchain.memory import ConversationBufferMemory
from typing import Dict, Optional, Any, List
import json

# Global memory storage
session_memories: Dict[str, ConversationBufferMemory] = {}

def get_memory_for_session(session_id: str) -> ConversationBufferMemory:
    """Get or create memory for a specific session."""
    if session_id not in session_memories:
        session_memories[session_id] = ConversationBufferMemory(
            memory_key="chat_history",
            return_messages=True,
            k=10  # Keep last 10 messages
        )
    return session_memories[session_id]

def clear_memory_for_session(session_id: str) -> bool:
    """Clear memory for a specific session."""
    if session_id in session_memories:
        del session_memories[session_id]
        return True
    return False

def get_memory_status(session_id: str) -> Dict[str, Any]:
    """Get memory status for a session."""
    if session_id not in session_memories:
        return {
            "session_id": session_id,
            "exists": False,
            "message_count": 0,
            "messages": []
        }
    
    memory = session_memories[session_id]
    messages = memory.chat_memory.messages
    
    return {
        "session_id": session_id,
        "exists": True,
        "message_count": len(messages),
        "messages": [
            {
                "type": msg.type,
                "content": msg.content
            }
            for msg in messages
        ]
    }

def clear_all_memories() -> int:
    """Clear all session memories. Returns number of cleared sessions."""
    count = len(session_memories)
    session_memories.clear()
    return count

def get_all_memory_sessions() -> List[str]:
    """Get list of all active session IDs."""
    return list(session_memories.keys())
