# RAG API Documentation Assistant

A beautiful web application that allows you to upload API documentation and ask intelligent questions about it using Retrieval-Augmented Generation (RAG). Built with FastAPI, React, LangChain, Cohere embeddings, and Claude AI.

## Features

- 📝 **Text-based Documentation Upload**: Paste your API documentation directly into the interface
- 🤖 **Intelligent Q&A**: Ask questions about your API documentation and get accurate answers
- 📊 **Source Attribution**: See which parts of the documentation were used to answer your questions
- 🎨 **Beautiful UI**: Modern, responsive interface with smooth animations
- 📋 **Markdown Support**: Full Markdown rendering for documentation and answers
- 🔍 **Smart Search**: Uses MMR (Maximum Marginal Relevance) for better search results
- 📱 **Responsive Design**: Works perfectly on desktop and mobile devices

## Tech Stack

### Backend
- **FastAPI**: Modern, fast web framework for building APIs
- **LangChain**: Framework for building LLM applications
- **Cohere**: For text embeddings
- **Anthropic Claude**: For generating intelligent responses
- **FAISS**: For vector similarity search
- **Weaviate**: For vector database

### Frontend
- **React**: Modern JavaScript library for building user interfaces
- **Tailwind CSS**: Utility-first CSS framework
- **Axios**: HTTP client for API calls
- **React Markdown**: Markdown rendering
- **Lucide React**: Beautiful icons
- **React Syntax Highlighter**: Code syntax highlighting

## Quick Start

### Prerequisites

- Python 3.8+
- Node.js 16+
- npm or yarn
- Docker (for Weaviate)

### Installation

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd Task-11-RAG
   ```

2. **Install Python dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Install frontend dependencies**
   ```bash
   cd frontend
   npm install
   ```

4. **Start Weaviate (optional, for vector database)**
   - Weaviate is included in the `docker-compose.yml` file. To start Weaviate, run:
     ```powershell
     docker-compose up -d
     ```
   - The Weaviate REST API and Console will be available at [http://127.0.0.1:8080](http://127.0.0.1:8080)

### Running the Application

1. **Start the FastAPI backend**
   ```bash
   # From the root directory
   python app.py
   ```
   The backend will be available at `http://localhost:8000`

2. **Start the React frontend**
   ```bash
   # From the frontend directory
   cd frontend
   npm start
   ```
   The frontend will be available at `http://localhost:3000`

3. **Open your browser**
   Navigate to `http://localhost:3000` to use the application

## Usage

### 1. Upload Documentation
- Paste your API documentation into the text area on the left
- Click "Process Documentation" or press `Ctrl+Enter`
- The system will process your documentation and create embeddings

### 2. Ask Questions
- Once documentation is processed, you can ask questions in the right panel
- Type your question and click "Ask Question" or press `Ctrl+Enter`
- Get intelligent answers with source attribution

### 3. Sample Questions
Try asking questions like:
- "What are the authentication requirements?"
- "List all the endpoints for user management"
- "What parameters are required for the upload file API?"
- "Show me the error codes and their meanings"
- "What file types are supported for upload?"

## API Endpoints

### Backend API (FastAPI)

- `POST /process-documentation`: Process API documentation
- `POST /ask`: Ask questions about the documentation
- `GET /health`: Health check endpoint
- `GET /`: API information

### Request/Response Examples

**Process Documentation:**
```bash
curl -X POST "http://localhost:8000/process-documentation" \
  -H "Content-Type: application/json" \
  -d '{
    "content": "# API Documentation\n\n## Overview\n...",
    "title": "My API Docs"
  }'
```

**Ask Question:**
```bash
curl -X POST "http://localhost:8000/ask" \
  -H "Content-Type: application/json" \
  -d '{
    "question": "What are the authentication requirements?",
    "show_sources": true
  }'
```

## Configuration

### Environment Variables

The application uses the following API keys (already configured in the code):

- `ANTHROPIC_API_KEY`: For Claude AI access
- `COHERE_API_KEY`: For text embeddings

### Customization

You can modify the following in `app.py`:

- **Chunk Size**: Change `chunk_size=1000` for different text chunk sizes
- **Overlap**: Change `chunk_overlap=200` for different overlap amounts
- **Model**: Change the Claude model or Cohere embedding model
- **Temperature**: Adjust `temperature=0.2` for different response creativity

## Features in Detail

### RAG System
- **Document Processing**: Splits documentation by headers and chunks for optimal retrieval
- **Embeddings**: Uses Cohere's `embed-english-v3.0` model for high-quality embeddings
- **Vector Search**: FAISS with MMR for diverse and relevant results
- **LLM**: Claude 3.5 Sonnet for intelligent responses

### Frontend Features
- **Real-time Processing**: Live feedback during documentation processing
- **Markdown Rendering**: Beautiful rendering of documentation and answers
- **Syntax Highlighting**: Code blocks are properly highlighted
- **Copy to Clipboard**: Easy copying of answers and sources
- **Responsive Design**: Works on all screen sizes
- **Loading States**: Smooth loading animations

### Error Handling
- **Graceful Degradation**: Handles API errors gracefully
- **User Feedback**: Clear error messages and success notifications
- **Validation**: Input validation for documentation and questions

## Development

### Project Structure
```
Task-11-RAG/
├── app.py                 # FastAPI backend
├── requirements.txt       # Python dependencies
├── api_doc.md           # Sample API documentation
├── main.py              # Original RAG script
├── frontend/            # React frontend
│   ├── src/
│   │   ├── App.js       # Main React component
│   │   ├── index.js     # React entry point
│   │   └── index.css    # Styles
│   ├── package.json     # Node.js dependencies
│   └── public/          # Static files
└── README.md           # This file
```

### Adding New Features

1. **Backend**: Add new endpoints in `app.py`
2. **Frontend**: Add new components in `frontend/src/`
3. **Styling**: Modify `frontend/src/index.css` or add Tailwind classes

## Troubleshooting

### Common Issues

1. **Port already in use**
   - Change the port in `app.py` or kill the process using the port

2. **API key errors**
   - Verify your API keys are correct and have sufficient credits

3. **CORS errors**
   - The backend is configured to allow all origins in development

4. **Memory issues with large documents**
   - Reduce chunk size in the backend configuration

### Performance Tips

- **Large Documents**: Consider splitting very large documents into smaller sections
- **Frequent Questions**: The system caches embeddings, so repeated questions are faster
- **Concurrent Users**: The current setup is for single-user use; for multiple users, consider database storage

## Vector Database: Weaviate

This project uses [Weaviate](https://weaviate.io/) as the vector database for storing and retrieving document embeddings.

### Setup Weaviate Locally

1. **Docker Compose**
   - Weaviate is included in the `docker-compose.yml` file:
     ```yaml
     services:
       weaviate:
         image: semitechnologies/weaviate:latest
         ports:
           - "8080:8080"    # REST / Console
           - "50051:50051"  # gRPC
         environment:
           AUTHENTICATION_ANONYMOUS_ACCESS_ENABLED: 'true'
           PERSISTENCE_DATA_PATH: './data'
           QUERY_DEFAULTS_LIMIT: 25
           ENABLE_MODULES: ''
           CLUSTER_HOSTNAME: 'node1'
     ```
   - To start Weaviate, run:
     ```powershell
     docker-compose up -d
     ```
   - The Weaviate REST API and Console will be available at [http://127.0.0.1:8080](http://127.0.0.1:8080)

2. **Python Client**
   - The backend uses the `weaviate-client` Python package (v3):
     ```powershell
     pip install "weaviate-client>=3.26.7,<4.0.0"
     ```
   - The FastAPI backend connects to Weaviate at `http://127.0.0.1:8080`.

3. **Integration in Backend**
   - Embeddings are stored and retrieved using LangChain's Weaviate integration.
   - All document chunks are indexed in Weaviate for fast semantic search.

### Useful Links
- [Weaviate Documentation](https://weaviate.io/developers/weaviate)
- [Weaviate Console](http://127.0.0.1:8080)

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test thoroughly
5. Submit a pull request

## License

This project is licensed under the MIT License.

## Acknowledgments

- **LangChain**: For the RAG framework
- **Cohere**: For text embeddings
- **Anthropic**: For Claude AI
- **FastAPI**: For the backend framework
- **React**: For the frontend framework
- **Tailwind CSS**: For the beautiful styling