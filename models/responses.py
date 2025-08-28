from pydantic import BaseModel
from typing import Optional, List, Dict, Any, Union

class StructuredContent(BaseModel):
    """Structured content for responses."""
    title: str = ""
    description: str = ""
    code_blocks: List[Dict[str, str]] = []
    tables: List[Dict[str, Any]] = []
    lists: List[List[str]] = []
    links: List[str] = []
    notes: List[str] = []
    warnings: List[str] = []
    values: Optional[Dict[str, Any]] = None

class StructuredResponse(BaseModel):
    """Main response model for structured content."""
    type: str  # "simple", "table", "list", "explanatory", "values", "error"
    content: StructuredContent
    memory_count: int = 0

class ErrorResponse(BaseModel):
    """Error response model."""
    type: str = "error"
    errors: List[str]

class SuccessResponse(BaseModel):
    """Success response model."""
    type: str = "success"
    message: str
    data: Optional[Dict[str, Any]] = None

class HealthResponse(BaseModel):
    """Health check response model."""
    status: str
    rag_ready: bool

class RootResponse(BaseModel):
    """Root endpoint response model."""
    message: str
    version: str
    endpoints: Dict[str, str]

class MemoryResponse(BaseModel):
    """Memory status response model."""
    session_id: str
    message_count: int
    messages: List[Dict[str, str]]

class VectorDBResponse(BaseModel):
    """Vector database status response model."""
    status: str
    index_name: str
    document_count: int
    message: str
