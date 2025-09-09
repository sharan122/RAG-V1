from pydantic import BaseModel
from typing import Optional, List, Dict, Any, Union

class EndpointInfo(BaseModel):
    """Information about a specific API endpoint."""
    method: str
    url: str
    params: Optional[Dict[str, str]] = None
    response_example: Optional[Dict[str, Any]] = None

class CodeExamples(BaseModel):
    """Code examples for the API."""
    curl: Optional[Union[str, List[str]]] = None
    python: Optional[Union[str, List[str]]] = None
    javascript: Optional[Union[str, List[str]]] = None

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
    """Main response model for structured content with new API-focused format."""
    answer: str = ""
    description: str = ""
    endpoints: List[EndpointInfo] = []
    code_examples: Optional[CodeExamples] = None
    links: List[str] = []
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
