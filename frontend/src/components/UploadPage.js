import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { 
  Upload, 
  FileText, 
  CheckCircle, 
  AlertCircle, 
  Loader2, 
  Database,
  Trash2,
  Brain
} from 'lucide-react';

const API_BASE_URL = 'http://localhost:8000';

function UploadPage() {
  const [documentation, setDocumentation] = useState('');
  const [title, setTitle] = useState('API Documentation');
  const [isProcessing, setIsProcessing] = useState(false);
  const [result, setResult] = useState(null);
  const [error, setError] = useState(null);
  const [vectorDBStatus, setVectorDBStatus] = useState({
    is_ready: false,
    documents_count: 0,
    db_size_mb: 0.0,
    last_updated: null
  });
  const [memoryStatus, setMemoryStatus] = useState({
    active_sessions: 0,
    total_memories: 0,
    memory_size_mb: 0.0
  });

  useEffect(() => {
    checkVectorDBStatus();
    checkMemoryStatus();
  }, []);

  const checkVectorDBStatus = async () => {
    try {
      const response = await axios.get(`${API_BASE_URL}/vector-db-status`);
      setVectorDBStatus(response.data);
    } catch (error) {
      console.error('Failed to check vector DB status:', error);
    }
  };

  const checkMemoryStatus = async () => {
    try {
      const response = await axios.get(`${API_BASE_URL}/memory-status`);
      setMemoryStatus(response.data);
    } catch (error) {
      console.error('Failed to check memory status:', error);
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!documentation.trim()) {
      setError('Please enter some documentation content.');
      return;
    }

    setIsProcessing(true);
    setError(null);
    setResult(null);

    try {
      const response = await axios.post(`${API_BASE_URL}/process-documentation`, {
        content: documentation,
        title: title
      });

      setResult(response.data.data);
      await checkVectorDBStatus();
    } catch (error) {
      setError(error.response?.data?.detail || 'Failed to process documentation.');
    } finally {
      setIsProcessing(false);
    }
  };

  const clearVectorDB = async () => {
    try {
      await axios.post(`${API_BASE_URL}/clear-vector-db`);
      setResult(null);
      await checkVectorDBStatus();
    } catch (error) {
      setError('Failed to clear vector database.');
    }
  };

  const clearAllMemory = async () => {
    try {
      await axios.post(`${API_BASE_URL}/clear-memory`, {
        session_id: null // Clear all sessions
      });
      await checkMemoryStatus();
    } catch (error) {
      setError('Failed to clear memory.');
    }
  };

  return (
    <div className="max-w-4xl mx-auto p-6">
      <div className="mb-8">
        <h1 className="text-3xl font-bold text-gray-900 mb-2">Upload Documentation</h1>
        <p className="text-gray-600">
          Paste your API documentation here to create a searchable knowledge base.
        </p>
      </div>

      {/* Status Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mb-8">
        {/* Vector Database Status */}
        <div className="bg-white rounded-lg border p-6">
          <div className="flex items-center justify-between mb-4">
            <div className="flex items-center">
              <Database className="w-5 h-5 text-blue-600 mr-2" />
              <h3 className="text-lg font-semibold text-gray-900">Vector Database</h3>
            </div>
            {vectorDBStatus.is_ready ? (
              <CheckCircle className="w-5 h-5 text-green-600" />
            ) : (
              <AlertCircle className="w-5 h-5 text-gray-400" />
            )}
          </div>
          
          <div className="space-y-2">
            <div className="flex justify-between">
              <span className="text-gray-600">Status:</span>
              <span className={vectorDBStatus.is_ready ? "text-green-600 font-medium" : "text-gray-500"}>
                {vectorDBStatus.is_ready ? "Ready" : "Not Ready"}
              </span>
            </div>
            <div className="flex justify-between">
              <span className="text-gray-600">Documents:</span>
              <span className="font-medium">{vectorDBStatus.documents_count}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-gray-600">Database Size:</span>
              <span className="font-medium">{vectorDBStatus.db_size_mb.toFixed(2)} MB</span>
            </div>
            {vectorDBStatus.last_updated && (
              <div className="flex justify-between">
                <span className="text-gray-600">Last Updated:</span>
                <span className="text-sm text-gray-500">{vectorDBStatus.last_updated}</span>
              </div>
            )}
          </div>

          {vectorDBStatus.is_ready && (
            <button
              onClick={clearVectorDB}
              className="mt-4 w-full px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700 transition-colors flex items-center justify-center"
            >
              <Trash2 className="w-4 h-4 mr-2" />
              Clean Vector DB
            </button>
          )}
        </div>

        {/* Memory Status */}
        <div className="bg-white rounded-lg border p-6">
          <div className="flex items-center justify-between mb-4">
            <div className="flex items-center">
              <Brain className="w-5 h-5 text-purple-600 mr-2" />
              <h3 className="text-lg font-semibold text-gray-900">Conversation Memory</h3>
            </div>
            {memoryStatus.active_sessions > 0 ? (
              <CheckCircle className="w-5 h-5 text-green-600" />
            ) : (
              <AlertCircle className="w-5 h-5 text-gray-400" />
            )}
          </div>
          
          <div className="space-y-2">
            <div className="flex justify-between">
              <span className="text-gray-600">Active Sessions:</span>
              <span className="font-medium">{memoryStatus.active_sessions}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-gray-600">Total Memories:</span>
              <span className="font-medium">{memoryStatus.total_memories}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-gray-600">Memory Size:</span>
              <span className="font-medium">{memoryStatus.memory_size_mb.toFixed(2)} MB</span>
            </div>
          </div>

          {memoryStatus.active_sessions > 0 && (
            <button
              onClick={clearAllMemory}
              className="mt-4 w-full px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700 transition-colors flex items-center justify-center"
            >
              <Trash2 className="w-4 h-4 mr-2" />
              Clear All Memory
            </button>
          )}
        </div>
      </div>

      {/* Upload Form */}
      <div className="bg-white rounded-lg border p-6">
        <form onSubmit={handleSubmit}>
          <div className="mb-6">
            <label htmlFor="title" className="block text-sm font-medium text-gray-700 mb-2">
              Documentation Title
            </label>
            <input
              type="text"
              id="title"
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              placeholder="Enter a title for your documentation"
            />
          </div>

          <div className="mb-6">
            <label htmlFor="documentation" className="block text-sm font-medium text-gray-700 mb-2">
              Documentation Content
            </label>
            <textarea
              id="documentation"
              value={documentation}
              onChange={(e) => setDocumentation(e.target.value)}
              rows="15"
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent resize-none"
              placeholder="Paste your API documentation here (Markdown format supported)..."
            />
          </div>

          {error && (
            <div className="mb-4 p-4 bg-red-50 border border-red-200 rounded-lg">
              <div className="flex items-center">
                <AlertCircle className="w-5 h-5 text-red-600 mr-2" />
                <span className="text-red-800">{error}</span>
              </div>
            </div>
          )}

          {result && (
            <div className="mb-4 p-4 bg-green-50 border border-green-200 rounded-lg">
              <div className="flex items-center">
                <CheckCircle className="w-5 h-5 text-green-600 mr-2" />
                <span className="text-green-800">{result.message}</span>
              </div>
              <div className="mt-2 text-sm text-green-700">
                <div>Sections: {result.sections}</div>
                <div>Chunks: {result.chunks}</div>
                <div>Database Size: {result.db_size_mb} MB</div>
              </div>
            </div>
          )}

          <button
            type="submit"
            disabled={isProcessing || !documentation.trim()}
            className="w-full px-6 py-3 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors flex items-center justify-center"
          >
            {isProcessing ? (
              <>
                <Loader2 className="w-5 h-5 animate-spin mr-2" />
                Processing...
              </>
            ) : (
              <>
                <Upload className="w-5 h-5 mr-2" />
                Process Documentation
              </>
            )}
          </button>
        </form>
      </div>
    </div>
  );
}

export default UploadPage; 