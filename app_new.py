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

# Startup event to reload existing Weaviate data
@app.on_event("startup")
async def startup_event():
    """Reload existing Weaviate data on application startup."""
    try:
        from routers.docs import reload_existing_data
        
        print("🔄 Starting up - attempting to reload existing Weaviate data...")
        success = await reload_existing_data()
        
        if success:
            # Import state after reload to get updated values
            import core.state as state
            print(f"✅ Startup complete - existing data reloaded successfully")
            print(f"📊 Loaded {state.documents_count} documents from Weaviate")
            print(f"🔗 RAG system ready: {state.rag_chain is not None}")
        else:
            print("ℹ️ No existing data found - ready for new documentation upload")
            
    except Exception as e:
        print(f"⚠️ Startup warning - could not reload existing data: {e}")
        print("ℹ️ This is normal for first-time startup")

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
