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
  Brain,
  RefreshCw,
  BarChart3,
  Settings,
  Zap,
  BookOpen,
  Search
} from 'lucide-react';

const API_BASE_URL = 'http://localhost:8000';

function UploadPage() {
  const [documentation, setDocumentation] = useState('');
  const [title, setTitle] = useState('API Documentation');
  const [isProcessing, setIsProcessing] = useState(false);
  const [result, setResult] = useState(null);
  const [error, setError] = useState(null);
  const [processingProgress, setProcessingProgress] = useState(0);
  const [showAdvanced, setShowAdvanced] = useState(false);
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
      const response = await axios.get(`${API_BASE_URL}/docs/status`);
      // Handle new API response structure
      const data = response.data;
      setVectorDBStatus({
        is_ready: data.vectorstore?.status === "ready" || data.vectorstore?.status === "initialized",
        documents_count: data.vectorstore?.document_count || 0,
        db_size_mb: data.vectorstore?.db_size_mb || 0.0,
        last_updated: data.vectorstore?.last_updated || null
      });
    } catch (error) {
      console.error('Failed to check vector DB status:', error);
      // Set default values on error
      setVectorDBStatus({
        is_ready: false,
        documents_count: 0,
        db_size_mb: 0.0,
        last_updated: null
      });
    }
  };

  const checkMemoryStatus = async () => {
    try {
      const response = await axios.get(`${API_BASE_URL}/memory/health`);
      setMemoryStatus({
        active_sessions: response.data.active_sessions || 0,
        total_memories: response.data.total_messages || 0,
        memory_size_mb: 0.0 // Not provided by new API
      });
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
    
    // Start progress simulation
    const progressInterval = simulateProgress();

    try {
      const response = await axios.post(`${API_BASE_URL}/docs/process`, {
        content: documentation,
        title: title,
        session_id: "default"
      });

      setProcessingProgress(100);
      setResult(response.data.data);
      await checkVectorDBStatus();
    } catch (error) {
      setError(error.response?.data?.detail || 'Failed to process documentation.');
    } finally {
      clearInterval(progressInterval);
      setIsProcessing(false);
      setProcessingProgress(0);
    }
  };

  const clearVectorDB = async () => {
    try {
      await axios.post(`${API_BASE_URL}/docs/clear`);
      setResult(null);
      await checkVectorDBStatus();
    } catch (error) {
      setError('Failed to clear vector database.');
    }
  };

  const clearAllMemory = async () => {
    try {
      await axios.post(`${API_BASE_URL}/memory/clear-all`);
      await checkMemoryStatus();
    } catch (error) {
      setError('Failed to clear memory.');
    }
  };


  // Simulate processing progress
  const simulateProgress = () => {
    setProcessingProgress(0);
    const interval = setInterval(() => {
      setProcessingProgress(prev => {
        if (prev >= 90) {
          clearInterval(interval);
          return 90;
        }
        return prev + Math.random() * 15;
      });
    }, 200);
    return interval;
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 via-white to-indigo-50">
      <div className="max-w-6xl mx-auto p-6">
        {/* Header Section */}
        <div className="text-center mb-12">
          <div className="inline-flex items-center justify-center w-16 h-16 bg-gradient-to-r from-blue-600 to-indigo-600 rounded-full mb-4">
            <BookOpen className="w-8 h-8 text-white" />
          </div>
          <h1 className="text-4xl font-bold text-gray-900 mb-4">
            Smart Documentation Upload
          </h1>
          <p className="text-xl text-gray-600 max-w-2xl mx-auto">
            Transform your API documentation into an intelligent, searchable knowledge base with AI-powered insights
          </p>
        </div>

        {/* System Status Dashboard */}
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4 sm:gap-6 mb-8">
          {/* Vector Database Status */}
          <div className="bg-white rounded-xl shadow-lg border border-gray-100 p-6 hover:shadow-xl transition-all duration-300">
            <div className="flex items-center justify-between mb-4">
              <div className="flex items-center">
                <div className="p-2 bg-blue-100 rounded-lg mr-3">
                  <Database className="w-6 h-6 text-blue-600" />
                </div>
                <div>
                  <h3 className="text-lg font-semibold text-gray-900">Vector Database</h3>
                  <p className="text-sm text-gray-500">Knowledge Storage</p>
                </div>
              </div>
              {vectorDBStatus.is_ready ? (
                <div className="flex items-center text-green-600">
                  <CheckCircle className="w-5 h-5 mr-1" />
                  <span className="text-sm font-medium">Ready</span>
                </div>
              ) : (
                <div className="flex items-center text-gray-400">
                  <AlertCircle className="w-5 h-5 mr-1" />
                  <span className="text-sm font-medium">Not Ready</span>
                </div>
              )}
            </div>
            
            <div className="space-y-3">
              <div className="flex justify-between items-center">
                <span className="text-gray-600">Documents:</span>
                <span className="font-semibold text-lg text-gray-900">{vectorDBStatus.documents_count}</span>
              </div>
              <div className="flex justify-between items-center">
                <span className="text-gray-600">Size:</span>
                <span className="font-medium text-gray-900">{vectorDBStatus.db_size_mb.toFixed(2)} MB</span>
              </div>
              {vectorDBStatus.last_updated && (
                <div className="flex justify-between items-center">
                  <span className="text-gray-600">Updated:</span>
                  <span className="text-sm text-gray-500">{vectorDBStatus.last_updated}</span>
                </div>
              )}
            </div>

            {vectorDBStatus.is_ready && (
              <button
                onClick={clearVectorDB}
                className="mt-4 w-full px-4 py-2 bg-red-50 text-red-600 rounded-lg hover:bg-red-100 transition-colors flex items-center justify-center border border-red-200"
              >
                <Trash2 className="w-4 h-4 mr-2" />
                Clear Database
              </button>
            )}
          </div>

          {/* Memory Status */}
          <div className="bg-white rounded-xl shadow-lg border border-gray-100 p-6 hover:shadow-xl transition-all duration-300">
            <div className="flex items-center justify-between mb-4">
              <div className="flex items-center">
                <div className="p-2 bg-purple-100 rounded-lg mr-3">
                  <Brain className="w-6 h-6 text-purple-600" />
                </div>
                <div>
                  <h3 className="text-lg font-semibold text-gray-900">Memory System</h3>
                  <p className="text-sm text-gray-500">Conversation Context</p>
                </div>
              </div>
              {memoryStatus.active_sessions > 0 ? (
                <div className="flex items-center text-green-600">
                  <CheckCircle className="w-5 h-5 mr-1" />
                  <span className="text-sm font-medium">Active</span>
                </div>
              ) : (
                <div className="flex items-center text-gray-400">
                  <AlertCircle className="w-5 h-5 mr-1" />
                  <span className="text-sm font-medium">Inactive</span>
                </div>
              )}
            </div>
            
            <div className="space-y-3">
              <div className="flex justify-between items-center">
                <span className="text-gray-600">Sessions:</span>
                <span className="font-semibold text-lg text-gray-900">{memoryStatus.active_sessions}</span>
              </div>
              <div className="flex justify-between items-center">
                <span className="text-gray-600">Memories:</span>
                <span className="font-medium text-gray-900">{memoryStatus.total_memories}</span>
              </div>
              <div className="flex justify-between items-center">
                <span className="text-gray-600">Size:</span>
                <span className="font-medium text-gray-900">{memoryStatus.memory_size_mb.toFixed(2)} MB</span>
              </div>
            </div>

            {memoryStatus.active_sessions > 0 && (
              <button
                onClick={clearAllMemory}
                className="mt-4 w-full px-4 py-2 bg-red-50 text-red-600 rounded-lg hover:bg-red-100 transition-colors flex items-center justify-center border border-red-200"
              >
                <Trash2 className="w-4 h-4 mr-2" />
                Clear Memory
              </button>
            )}
          </div>

          {/* Quick Actions */}
          <div className="bg-white rounded-xl shadow-lg border border-gray-100 p-6 hover:shadow-xl transition-all duration-300">
            <div className="flex items-center justify-between mb-4">
              <div className="flex items-center">
                <div className="p-2 bg-green-100 rounded-lg mr-3">
                  <Zap className="w-6 h-6 text-green-600" />
                </div>
                <div>
                  <h3 className="text-lg font-semibold text-gray-900">Quick Actions</h3>
                  <p className="text-sm text-gray-500">System Controls</p>
                </div>
              </div>
            </div>
            
            <div className="space-y-3">
              <button
                onClick={checkVectorDBStatus}
                className="w-full px-4 py-2 bg-blue-50 text-blue-600 rounded-lg hover:bg-blue-100 transition-colors flex items-center justify-center border border-blue-200"
              >
                <RefreshCw className="w-4 h-4 mr-2" />
                Refresh Status
              </button>
              <button
                onClick={() => setShowAdvanced(!showAdvanced)}
                className="w-full px-4 py-2 bg-gray-50 text-gray-600 rounded-lg hover:bg-gray-100 transition-colors flex items-center justify-center border border-gray-200"
              >
                <Settings className="w-4 h-4 mr-2" />
                {showAdvanced ? 'Hide' : 'Show'} Advanced
              </button>
            </div>
          </div>
        </div>

        {/* Upload Section */}
        <div className="bg-white rounded-2xl shadow-xl border border-gray-100 p-8 mb-8">
          <div className="text-center mb-8">
            <h2 className="text-2xl font-bold text-gray-900 mb-2">Upload Your Documentation</h2>
            <p className="text-gray-600">Paste your API documentation content below</p>
          </div>

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
                  className="w-full px-4 py-3 border border-gray-300 rounded-xl focus:ring-2 focus:ring-blue-500 focus:border-transparent transition-all duration-200"
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
                  rows="12"
                  className="w-full px-4 py-3 border border-gray-300 rounded-xl focus:ring-2 focus:ring-blue-500 focus:border-transparent resize-none transition-all duration-200"
                  placeholder="Paste your API documentation here (Markdown format supported)..."
                />
              </div>

              {/* Progress Bar */}
              {isProcessing && (
                <div className="mb-6">
                  <div className="flex items-center justify-between mb-2">
                    <span className="text-sm font-medium text-gray-700">Processing Documentation</span>
                    <span className="text-sm text-gray-500">{Math.round(processingProgress)}%</span>
                  </div>
                  <div className="w-full bg-gray-200 rounded-full h-2">
                    <div
                      className="bg-gradient-to-r from-blue-500 to-indigo-600 h-2 rounded-full transition-all duration-300 ease-out"
                      style={{ width: `${processingProgress}%` }}
                    ></div>
                  </div>
                </div>
              )}

              {/* Error Message */}
              {error && (
                <div className="mb-6 p-4 bg-red-50 border border-red-200 rounded-xl">
                  <div className="flex items-center">
                    <AlertCircle className="w-5 h-5 text-red-600 mr-3" />
                    <span className="text-red-800 font-medium">{error}</span>
                  </div>
                </div>
              )}

              {/* Success Message */}
              {result && (
                <div className="mb-6 p-6 bg-green-50 border border-green-200 rounded-xl">
                  <div className="flex items-center mb-4">
                    <CheckCircle className="w-6 h-6 text-green-600 mr-3" />
                    <span className="text-green-800 font-semibold text-lg">{result.message}</span>
                  </div>
                  <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-3 sm:gap-4 text-sm">
                    <div className="bg-white rounded-lg p-3 border border-green-200">
                      <div className="text-green-600 font-medium">Sections</div>
                      <div className="text-2xl font-bold text-green-800">{result.sections || 0}</div>
                    </div>
                    <div className="bg-white rounded-lg p-3 border border-green-200">
                      <div className="text-green-600 font-medium">Chunks</div>
                      <div className="text-2xl font-bold text-green-800">{result.chunks || 0}</div>
                    </div>
                    <div className="bg-white rounded-lg p-3 border border-green-200">
                      <div className="text-green-600 font-medium">Database Size</div>
                      <div className="text-2xl font-bold text-green-800">{result.db_size_mb || 0} MB</div>
                    </div>
                  </div>
                </div>
              )}

              {/* Submit Button */}
              <button
                type="submit"
                disabled={isProcessing || !documentation.trim()}
                className="w-full px-8 py-4 bg-gradient-to-r from-blue-600 to-indigo-600 text-white rounded-xl hover:from-blue-700 hover:to-indigo-700 disabled:opacity-50 disabled:cursor-not-allowed transition-all duration-200 flex items-center justify-center font-semibold text-lg shadow-lg hover:shadow-xl transform hover:-translate-y-0.5"
              >
                {isProcessing ? (
                  <>
                    <Loader2 className="w-6 h-6 animate-spin mr-3" />
                    Processing Documentation...
                  </>
                ) : (
                  <>
                    <Upload className="w-6 h-6 mr-3" />
                    Process Documentation
                  </>
                )}
              </button>
          </form>
        </div>

        {/* Advanced Settings */}
        {showAdvanced && (
          <div className="bg-white rounded-2xl shadow-xl border border-gray-100 p-8">
            <h3 className="text-xl font-bold text-gray-900 mb-6">Advanced Settings</h3>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 sm:gap-6">
              <div className="space-y-4">
                <h4 className="font-semibold text-gray-700">System Information</h4>
                <div className="space-y-2 text-sm">
                  <div className="flex justify-between">
                    <span className="text-gray-600">Vector DB Status:</span>
                    <span className={vectorDBStatus.is_ready ? "text-green-600" : "text-red-600"}>
                      {vectorDBStatus.is_ready ? "Ready" : "Not Ready"}
                    </span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-gray-600">Memory Sessions:</span>
                    <span className="text-gray-900">{memoryStatus.active_sessions}</span>
                  </div>
                </div>
              </div>
              <div className="space-y-4">
                <h4 className="font-semibold text-gray-700">Quick Actions</h4>
                <div className="space-y-2">
                  <button
                    onClick={checkVectorDBStatus}
                    className="w-full px-4 py-2 bg-blue-50 text-blue-600 rounded-lg hover:bg-blue-100 transition-colors flex items-center justify-center"
                  >
                    <RefreshCw className="w-4 h-4 mr-2" />
                    Refresh Status
                  </button>
                </div>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

export default UploadPage; 