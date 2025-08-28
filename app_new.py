from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from routers import docs, questions, memory
from core.config import APP_TITLE, APP_VERSION, APP_DESCRIPTION

# Create FastAPI app
app = FastAPI(
    title=APP_TITLE,
    version=APP_VERSION,
    description=APP_DESCRIPTION
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register routers
app.include_router(docs.router)
app.include_router(questions.router)
app.include_router(memory.router)

# Root endpoint
@app.get("/")
async def root():
    """Root endpoint with API information."""
    return {
        "message": "RAG API Documentation Assistant",
        "version": "1.0.0",
        "endpoints": {
            "POST /docs/process": "Process API documentation",
            "POST /questions/ask": "Ask questions about the documentation",
            "POST /memory/clear": "Clear conversation memory",
            "GET /docs/status": "Get documentation status",
            "GET /memory/health": "Get memory system health"
        }
    }

# Health check endpoint
@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "message": "RAG API Documentation Assistant is running"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
