from pydantic import BaseModel
from typing import Optional, List, Dict, Any

class DocumentationRequest(BaseModel):
    """Request model for processing documentation."""
    content: str
    title: Optional[str] = "API Documentation"
    session_id: Optional[str] = "default"

class QuestionRequest(BaseModel):
    """Request model for asking questions."""
    question: str
    session_id: Optional[str] = "default"

class MemoryRequest(BaseModel):
    """Request model for memory operations."""
    session_id: str
    action: str  # "clear", "status", "get"
    limit: Optional[int] = 10

class VectorDBRequest(BaseModel):
    """Request model for vector database operations."""
    action: str  # "clear", "status"
    session_id: Optional[str] = "default"
