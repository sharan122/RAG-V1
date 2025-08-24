import os
from dotenv import load_dotenv
import re
import json
import time
import sys
from typing import List, Optional, Dict, Any
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from langchain_text_splitters import MarkdownHeaderTextSplitter
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.schema import Document
from langchain_cohere import CohereEmbeddings
from langchain_anthropic import ChatAnthropic
from langchain_community.vectorstores import Weaviate
from langchain_core.prompts import ChatPromptTemplate
from langchain.chains.combine_documents import create_stuff_documents_chain
from langchain.chains import create_retrieval_chain
from langchain.memory import ConversationBufferMemory
import weaviate as weaviate_client

load_dotenv()
# API keys are now loaded from .env file
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
COHERE_API_KEY = os.getenv("COHERE_API_KEY")
os.environ["ANTHROPIC_API_KEY"] = ANTHROPIC_API_KEY
os.environ["COHERE_API_KEY"] = COHERE_API_KEY

app = FastAPI(title="RAG API Documentation Assistant", version="1.0.0")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify your React app URL
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Pydantic models
class DocumentationRequest(BaseModel):
    content: str
    title: Optional[str] = "API Documentation"

class QuestionRequest(BaseModel):
    question: str
    show_sources: bool = True
    session_id: Optional[str] = "default"

class QuestionResponse(BaseModel):
    answer: str
    sources: List[dict]
    processing_info: dict
    memory_count: int

class StructuredResponse(BaseModel):
    type: str  # "simple", "code", "api", "list", "table", "mixed"
    content: Dict[str, Any]
    memory_count: int

class VectorDBStatus(BaseModel):
    is_ready: bool
    documents_count: int
    db_size_mb: float
    last_updated: Optional[str] = None

class MemoryStatus(BaseModel):
    active_sessions: int
    total_memories: int
    memory_size_mb: float

class ClearMemoryRequest(BaseModel):
    session_id: Optional[str] = None  # None means clear all sessions

# Global variables to store the RAG system
vector_store = None
rag_chain = None
retriever = None
documents_count = 0
db_size_mb = 0.0
last_updated = None

# Memory management
conversation_memories: Dict[str, ConversationBufferMemory] = {}

def get_object_size_mb(obj):
    """Calculate the size of an object in MB."""
    size = sys.getsizeof(obj)
    # For complex objects, we need to estimate better
    if hasattr(obj, '__dict__'):
        size += sum(get_object_size_mb(v) for v in obj.__dict__.values())
    return size / (1024 * 1024)  # Convert to MB

def get_memory_size_mb():
    """Calculate the total size of all conversation memories in MB."""
    total_size = 0
    for session_id, memory in conversation_memories.items():
        # Estimate memory size based on chat history
        chat_history = memory.chat_memory.messages
        for message in chat_history:
            total_size += len(message.content.encode('utf-8'))
            total_size += len(message.type.encode('utf-8'))
    return total_size / (1024 * 1024)

def get_memory_for_session(session_id: str) -> ConversationBufferMemory:
    """Get or create memory for a session."""
    if session_id not in conversation_memories:
        conversation_memories[session_id] = ConversationBufferMemory(
            memory_key="chat_history",
            return_messages=True
        )
    return conversation_memories[session_id]

def parse_structured_response(answer: str) -> Dict[str, Any]:
    """Parse the LLM response and structure it into different content types."""
    lines = answer.split('\n')
    structured_content = {
        'title': '',
        'description': '',
        'code_blocks': [],
        'tables': [],
        'lists': [],
        'links': [],
        'notes': [],
        'warnings': []
    }
    
    current_section = ''
    current_code = ''
    in_code_block = False
    code_language = 'bash'
    current_list = []
    in_list = False
    
    for line in lines:
        line = line.strip()
        if not line:
            continue
            
        # Detect headers
        if line.startswith('## '):
            structured_content['title'] = line.replace('## ', '')
        elif line.startswith('### '):
            current_section = line.replace('### ', '')
            
        # Detect code blocks
        elif line.startswith('```'):
            if not in_code_block:
                in_code_block = True
                code_language = line.replace('```', '').strip() or 'bash'
                current_code = ''
            else:
                in_code_block = False
                if current_code.strip():
                    structured_content['code_blocks'].append({
                        'language': code_language,
                        'code': current_code.strip(),
                        'title': current_section or 'Code'
                    })
                current_code = ''
        elif in_code_block:
            current_code += line + '\n'
            
        # Detect tables
        elif '|' in line and '---' in line:
            # This is a table separator, skip
            continue
        elif '|' in line:
            # This is a table row
            cells = [cell.strip() for cell in line.split('|') if cell.strip()]
            if len(cells) > 1:
                if not structured_content['tables']:
                    structured_content['tables'].append({
                        'headers': cells,
                        'rows': []
                    })
                else:
                    structured_content['tables'][-1]['rows'].append(cells)
                    
        # Detect lists
        elif line.startswith('- ') or line.startswith('* '):
            if not in_list:
                in_list = True
                current_list = []
            current_list.append(line[2:])
        elif line.startswith('1. ') or line.startswith('2. ') or line.startswith('3. '):
            if not in_list:
                in_list = True
                current_list = []
            current_list.append(line[3:])
        elif in_list and (line.startswith('- ') or line.startswith('* ') or line.startswith('1. ') or line.startswith('2. ')):
            # Continue list
            if line.startswith('- ') or line.startswith('* '):
                current_list.append(line[2:])
            else:
                current_list.append(line[3:])
        elif in_list:
            # End of list
            in_list = False
            if current_list:
                structured_content['lists'].append(current_list)
                current_list = []
                
        # Detect notes and warnings
        elif 'note:' in line.lower() or 'important:' in line.lower():
            structured_content['notes'].append(line)
        elif 'warning:' in line.lower() or 'caution:' in line.lower():
            structured_content['warnings'].append(line)
            
        # Detect links
        elif 'http' in line and ('api' in line.lower() or 'endpoint' in line.lower()):
            structured_content['links'].append(line)
            
        # Everything else goes to description
        elif not in_code_block and not in_list:
            if structured_content['description']:
                structured_content['description'] += '\n' + line
            else:
                structured_content['description'] = line
    
    # Handle any remaining list
    if in_list and current_list:
        structured_content['lists'].append(current_list)
    
    return structured_content

def determine_response_type(structured_content: Dict[str, Any]) -> str:
    """Determine the type of response based on content."""
    if structured_content['code_blocks'] and not structured_content['description']:
        return 'code'
    elif structured_content['tables'] and not structured_content['code_blocks']:
        return 'table'
    elif structured_content['lists'] and not structured_content['code_blocks']:
        return 'list'
    elif structured_content['code_blocks'] and structured_content['description']:
        return 'api'
    elif len(structured_content['description']) > 100:
        return 'explanatory'
    else:
        return 'simple'

def process_documentation(content: str, title: str = "API Documentation") -> dict:
    """Process the documentation content and create the RAG system."""
    global vector_store, rag_chain, retriever, documents_count, db_size_mb, last_updated
    
    # Strip YAML front matter if present
    raw = re.sub(r"^---\n.*?\n---\n", "", content, flags=re.DOTALL)
    
    # Split by headings so sections stay intact
    headers_to_split_on = [
        ("#", "h1"),
        ("##", "h2"),
        ("###", "h3"),
        ("####", "h4"),
    ]
    md_splitter = MarkdownHeaderTextSplitter(headers_to_split_on=headers_to_split_on)
    docs = md_splitter.split_text(raw)
    
    # Add metadata
    for d in docs:
        d.metadata.setdefault("source", title)
    
    # Then do chunking with overlap for embeddings/RAG
    splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)
    chunks: List[Document] = splitter.split_documents(docs)
    
    # Create embeddings and vector store
    embeddings = CohereEmbeddings(model="embed-english-v3.0")
    # Use the correct v4 Weaviate client initialization
    import weaviate as weaviate_client
    client = weaviate_client.Client(url="http://127.0.0.1:8080")
    vector_store = Weaviate.from_documents(
        chunks,
        embeddings,
        client=client,
        by_text=False,
        index_name="RAGDocs"
    )
    
    # Estimate db size (Weaviate doesn't provide direct size, so use chunk count)
    db_size_mb = len(chunks) * 6.5 / 1024  # Rough estimate: 6.5KB per vector
    
    # Use MMR to reduce redundancy
    retriever = vector_store.as_retriever(
        search_type="mmr",
        search_kwargs={"k": 6, "fetch_k": 24, "lambda_mult": 0.3},
    )
    
    # Create LLM and chain
    llm = ChatAnthropic(
        model="claude-3-5-sonnet-20240620",
        temperature=0.2,
        max_tokens=600,
    )
    
    SYSTEM_PROMPT = """
You are an expert technical assistant. Always respond in a structured JSON format, using key-value pairs for each type of information. Your response must be valid JSON and include only the following top-level keys as needed:

{{
    "type": "simple|code|api|table|list|explanatory|error|warning|values|links|short_answer",
    "title": "string (if applicable)",
    "description": "string (main explanation or answer)",
    "code_blocks": [ {{ "language": "string", "code": "string", "title": "string" }} ],
    "tables": [ {{ "headers": ["string"], "rows": [["string"]] }} ],
    "lists": [ ["string"] ],
    "links": [ "string (URL)" ],
    "notes": [ "string" ],
    "warnings": [ "string" ],
    "errors": [ "string" ],
    "values": {{ "key": "value", ... }},
    "short_answer": "string (if a brief answer is appropriate)"
}}

Guidelines:
- If the user requests an explanation, set "type": "explanatory" and provide a detailed answer in "description".
- If the user requests to find, create, or get something, respond with direct, actionable information ("type": "simple", "code", "api", "table", "list", etc. as appropriate).
- Always fill in the relevant keys. If a section is not needed, omit it from the JSON.
- For errors or warnings, use the "errors" or "warnings" keys.
- For links, use the "links" key.
- For tables, use the "tables" key with headers and rows.
- For code, use "code_blocks" with language and title.
- For short answers, use "short_answer".
- For values, use the "values" key as a dictionary.
- Do not include any extra text outside the JSON object.
- Do not use markdown formatting, only valid JSON.
- If you do not know the answer, reply with:
    {{ "type": "error", "errors": ["I don't know based on the provided context."] }}
"""
    
    HUMAN_PROMPT = """CONTEXT:
{context}

CHAT HISTORY:
{chat_history}

QUESTION:
{input}

Answer:"""
    
    prompt = ChatPromptTemplate.from_messages([
        ("system", SYSTEM_PROMPT),
        ("human", HUMAN_PROMPT),
    ])
    
    doc_chain = create_stuff_documents_chain(llm=llm, prompt=prompt)
    rag_chain = create_retrieval_chain(retriever, doc_chain)
    
    # Update global counters
    documents_count = len(chunks)
    last_updated = "now"
    
    return {
        "sections": len(docs),
        "chunks": len(chunks),
        "db_size_mb": round(db_size_mb, 2),
        "message": "Documentation processed successfully"
    }

def clear_vector_database():
    """Clear the vector database and reset the RAG system."""
    global vector_store, rag_chain, retriever, documents_count, db_size_mb, last_updated
    if vector_store is not None:
        import weaviate as weaviate_client
        client = weaviate_client.Client(url="http://127.0.0.1:8080")
        try:
            client.schema.delete_class("RAGDocs")
        except Exception:
            pass
    vector_store = None
    rag_chain = None
    retriever = None
    documents_count = 0
    db_size_mb = 0.0
    last_updated = None

def clear_conversation_memory(session_id: Optional[str] = None):
    """Clear conversation memory for a specific session or all sessions."""
    global conversation_memories
    if session_id is None:
        # Clear all sessions
        conversation_memories.clear()
        return {"message": "All conversation memories cleared", "cleared_sessions": len(conversation_memories)}
    elif session_id in conversation_memories:
        # Clear specific session
        del conversation_memories[session_id]
        return {"message": f"Conversation memory for session '{session_id}' cleared", "cleared_sessions": 1}
    else:
        return {"message": f"Session '{session_id}' not found", "cleared_sessions": 0}

@app.post("/process-documentation")
async def process_doc(request: DocumentationRequest):
    """Process API documentation and create RAG system."""
    try:
        result = process_documentation(request.content, request.title)
        return {"success": True, "data": result}
    except Exception as e:
        return {
            "type": "error",
            "errors": [f"Error processing documentation: {str(e)}"]
        }

@app.post("/ask")
async def ask_question(request: QuestionRequest):
    """Ask a question about the processed documentation."""
    global rag_chain, retriever
    
    if rag_chain is None:
        return {
            "type": "error",
            "errors": ["No documentation has been processed yet. Please upload documentation first."]
        }
    try:
        # Get memory for this session
        memory = get_memory_for_session(request.session_id)
        
        # Get chat history
        chat_history = memory.chat_memory.messages
        
        # Create context with chat history
        context_with_history = {
            "input": request.question,
            "chat_history": "\n".join([f"{msg.type}: {msg.content}" for msg in chat_history[-10:]])  # Last 10 messages
        }
        
        result = rag_chain.invoke(context_with_history)
        answer = result.get("answer")
        if answer is None:
            raise ValueError(f"RAG chain did not return an 'answer' key. Got: {result}")
        
        # Save the conversation to memory
        memory.chat_memory.add_user_message(request.question)
        memory.chat_memory.add_ai_message(answer)
        
        # Parse and structure the response
        structured_content = parse_structured_response(answer)
        response_type = determine_response_type(structured_content)
        
        return StructuredResponse(
            type=response_type,
            content=structured_content,
            memory_count=len(memory.chat_memory.messages)
        )
    except Exception as e:
        return {
            "type": "error",
            "errors": [f"Error processing question: {str(e)}"]
        }

@app.post("/ask/stream")
async def ask_question_stream(request: QuestionRequest):
    """Stream a question response character by character."""
    global rag_chain, retriever
    
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
        
        # Create context with chat history
        context_with_history = {
            "input": request.question,
            "chat_history": "\n".join([f"{msg.type}: {msg.content}" for msg in chat_history[-10:]])  # Last 10 messages
        }
        
        result = rag_chain.invoke(context_with_history)
        answer = result.get("answer") if isinstance(result, dict) else None
        if answer is None:
            raise ValueError(f"RAG chain did not return an 'answer' key. Got: {result}")
        
        # Save the conversation to memory
        memory.chat_memory.add_user_message(request.question)
        memory.chat_memory.add_ai_message(answer)
        
        # Post-process the answer to ensure proper formatting
        def post_process_answer(answer: str) -> str:
            """Post-process the answer to improve formatting and structure."""
            # Ensure proper spacing around headers
            answer = re.sub(r'([^\n])(##)', r'\1\n\n\2', answer)
            answer = re.sub(r'([^\n])(###)', r'\1\n\n\2', answer)
            
            # Ensure proper spacing around lists
            answer = re.sub(r'([^\n])(- )', r'\1\n\n\2', answer)
            answer = re.sub(r'([^\n])(\d+\.)', r'\1\n\n\2', answer)
            
            # Ensure proper spacing around code blocks
            answer = re.sub(r'([^\n])(```)', r'\1\n\n\2', answer)
            answer = re.sub(r'(```\n)([^\n])', r'\1\2', answer)
            
            # Ensure proper spacing around tables
            answer = re.sub(r'([^\n])(\|)', r'\1\n\n\2', answer)
            
            # Fix numbered lists formatting
            answer = re.sub(r"(?<!\n)(\d+\.)", r"\n\1", answer)
            answer = re.sub(r"(?<!\n)(- )", r"\n- ", answer)
            
            # Ensure proper spacing after headers
            answer = re.sub(r'(##[^\n]*\n)([^\n])', r'\1\n\2', answer)
            answer = re.sub(r'(###[^\n]*\n)([^\n])', r'\1\n\2', answer)
            
            # Add spacing around bold text for better readability
            answer = re.sub(r'(\*\*[^*]+\*\*)', r' \1 ', answer)
            
            # Ensure proper spacing around inline code
            answer = re.sub(r'([^\s])(`[^`]+`)', r'\1 \2', answer)
            answer = re.sub(r'(`[^`]+`)([^\s])', r'\1 \2', answer)
            
            # Add spacing around important notes (blockquotes)
            answer = re.sub(r'([^\n])(>)', r'\1\n\n\2', answer)
            
            # Ensure consistent spacing for code blocks
            answer = re.sub(r'```(\w+)\n', r'```\1\n', answer)
            
            # Add spacing before and after tables
            answer = re.sub(r'(\n\|[^\n]*\|[^\n]*\n)', r'\n\n\1\n\n', answer)
            
            # Ensure proper list indentation
            answer = re.sub(r'(\n- [^\n]*\n)(- )', r'\1  \2', answer)
            answer = re.sub(r'(\n\d+\. [^\n]*\n)(\d+\. )', r'\1  \2', answer)
            
            # Clean up multiple consecutive newlines
            answer = re.sub(r'\n{3,}', r'\n\n', answer)
            
            return answer.strip()
        
        # Apply post-processing to ensure proper formatting
        formatted_answer = post_process_answer(answer)
        
        def event_stream():
            # Stream the formatted answer character by character
            for char in formatted_answer:
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

@app.post("/clear-vector-db")
async def clear_vector_db():
    """Clear the vector database."""
    try:
        clear_vector_database()
        return {"success": True, "message": "Vector database cleared successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error clearing vector database: {str(e)}")

@app.post("/clear-memory")
async def clear_memory(request: ClearMemoryRequest):
    """Clear conversation memory."""
    try:
        result = clear_conversation_memory(request.session_id)
        return {"success": True, **result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error clearing memory: {str(e)}")

@app.get("/vector-db-status")
async def get_vector_db_status():
    """Get the status of the vector database."""
    return VectorDBStatus(
        is_ready=rag_chain is not None,
        documents_count=documents_count,
        db_size_mb=round(db_size_mb, 2),
        last_updated=last_updated
    )

@app.get("/memory-status")
async def get_memory_status():
    """Get the status of conversation memories."""
    total_memories = sum(len(memory.chat_memory.messages) for memory in conversation_memories.values())
    memory_size_mb = get_memory_size_mb()
    
    return MemoryStatus(
        active_sessions=len(conversation_memories),
        total_memories=total_memories,
        memory_size_mb=round(memory_size_mb, 2)
    )

@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "rag_ready": rag_chain is not None}

@app.get("/")
async def root():
    """Root endpoint with API information."""
    return {
        "message": "RAG API Documentation Assistant",
        "version": "1.0.0",
        "endpoints": {
            "POST /process-documentation": "Process API documentation",
            "POST /ask": "Ask questions about the documentation",
            "POST /ask/stream": "Stream questions about the documentation",
            "POST /clear-vector-db": "Clear vector database",
            "POST /clear-memory": "Clear conversation memory",
            "GET /vector-db-status": "Get vector database status",
            "GET /memory-status": "Get memory status",
            "GET /health": "Health check"
        }
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)