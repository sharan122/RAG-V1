import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import axios from 'axios';
import toast from 'react-hot-toast';
import { useTheme } from '../contexts/ThemeContext';
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
  Search,
  MessageSquare
} from 'lucide-react';

const API_BASE_URL = 'http://localhost:8000';

function UploadPage() {
  const navigate = useNavigate();
  const { isDark } = useTheme();
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

  const checkVectorDBStatus = async (showToast = false) => {
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
      if (showToast) {
        toast.success('Status refreshed successfully!');
      }
    } catch (error) {
      console.error('Failed to check vector DB status:', error);
      // Set default values on error
      setVectorDBStatus({
        is_ready: false,
        documents_count: 0,
        db_size_mb: 0.0,
        last_updated: null
      });
      if (showToast) {
        toast.error('Failed to refresh status.');
      }
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
      toast.error('Please enter some documentation content.');
      setError('Please enter some documentation content.');
      return;
    }

    setIsProcessing(true);
    setError(null);
    setResult(null);
    
    // Show loading toast
    const loadingToast = toast.loading('Processing documentation...', {
      duration: Infinity,
    });
    
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
      
      // Dismiss loading toast and show success
      toast.dismiss(loadingToast);
      toast.success('Documentation processed successfully!', {
        duration: 3000,
      });
      
      // Redirect to chat page after a short delay
      setTimeout(() => {
        navigate('/chat');
      }, 1500);
      
    } catch (error) {
      // Dismiss loading toast and show error
      toast.dismiss(loadingToast);
      toast.error(error.response?.data?.detail || 'Failed to process documentation.');
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
      toast.success('Vector database cleared successfully!');
    } catch (error) {
      toast.error('Failed to clear vector database.');
      setError('Failed to clear vector database.');
    }
  };

  const clearAllMemory = async () => {
    try {
      await axios.post(`${API_BASE_URL}/memory/clear-all`);
      await checkMemoryStatus();
      toast.success('Memory cleared successfully!');
    } catch (error) {
      toast.error('Failed to clear memory.');
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
    <div className="min-h-screen bg-gradient-to-br from-blue-50 via-white to-indigo-50 dark:from-gray-900 dark:via-gray-800 dark:to-gray-900 transition-colors duration-200">
      <div className="max-w-6xl mx-auto p-6">
        {/* Header Section */}
        <div className="text-center mb-12">
          <div className="inline-flex items-center justify-center w-16 h-16 bg-gradient-to-r from-blue-600 to-indigo-600 rounded-full mb-4">
            <BookOpen className="w-8 h-8 text-white" />
          </div>
          <h1 className="text-4xl font-bold text-gray-900 dark:text-white mb-4">
            Smart Documentation Upload
          </h1>
          <p className="text-xl text-gray-600 dark:text-gray-300 max-w-2xl mx-auto">
            Transform your API documentation into an intelligent, searchable knowledge base with AI-powered insights
          </p>
        </div>

        {/* System Status Dashboard */}
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4 sm:gap-6 mb-8">
          {/* Vector Database Status */}
          <div className="bg-white dark:bg-gray-800 rounded-xl shadow-lg border border-gray-100 dark:border-gray-700 p-6 hover:shadow-xl transition-all duration-300">
            <div className="flex items-center justify-between mb-4">
              <div className="flex items-center">
                <div className="p-2 bg-blue-100 rounded-lg mr-3">
                  <Database className="w-6 h-6 text-blue-600" />
                </div>
                <div>
                  <h3 className="text-lg font-semibold text-gray-900 dark:text-white">Vector Database</h3>
                  <p className="text-sm text-gray-500 dark:text-gray-400">Knowledge Storage</p>
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
                <span className="text-gray-600 dark:text-gray-300">Documents:</span>
                <span className="font-semibold text-lg text-gray-900 dark:text-white">{vectorDBStatus.documents_count}</span>
              </div>
              <div className="flex justify-between items-center">
                <span className="text-gray-600 dark:text-gray-300">Size:</span>
                <span className="font-medium text-gray-900 dark:text-white">{vectorDBStatus.db_size_mb.toFixed(2)} MB</span>
              </div>
              {vectorDBStatus.last_updated && (
                <div className="flex justify-between items-center">
                  <span className="text-gray-600 dark:text-gray-300">Updated:</span>
                  <span className="text-sm text-gray-500 dark:text-gray-400">{vectorDBStatus.last_updated}</span>
                </div>
              )}
            </div>

            {vectorDBStatus.is_ready && (
              <button
                onClick={clearVectorDB}
                className="mt-4 w-full px-4 py-2 bg-red-50 dark:bg-red-900/20 text-red-600 dark:text-red-400 rounded-lg hover:bg-red-100 dark:hover:bg-red-900/30 transition-colors flex items-center justify-center border border-red-200 dark:border-red-800"
              >
                <Trash2 className="w-4 h-4 mr-2" />
                Clear Database
              </button>
            )}
          </div>

          {/* Memory Status */}
          <div className="bg-white dark:bg-gray-800 rounded-xl shadow-lg border border-gray-100 dark:border-gray-700 p-6 hover:shadow-xl transition-all duration-300">
            <div className="flex items-center justify-between mb-4">
              <div className="flex items-center">
                <div className="p-2 bg-purple-100 rounded-lg mr-3">
                  <Brain className="w-6 h-6 text-purple-600" />
                </div>
                <div>
                  <h3 className="text-lg font-semibold text-gray-900 dark:text-white">Memory System</h3>
                  <p className="text-sm text-gray-500 dark:text-gray-400">Conversation Context</p>
                </div>
              </div>
              {memoryStatus.active_sessions > 0 ? (
                <div className="flex items-center text-green-600 dark:text-green-400">
                  <CheckCircle className="w-5 h-5 mr-1" />
                  <span className="text-sm font-medium">Active</span>
                </div>
              ) : (
                <div className="flex items-center text-gray-400 dark:text-gray-500">
                  <AlertCircle className="w-5 h-5 mr-1" />
                  <span className="text-sm font-medium">Inactive</span>
                </div>
              )}
            </div>
            
            <div className="space-y-3">
              <div className="flex justify-between items-center">
                <span className="text-gray-600 dark:text-gray-300">Sessions:</span>
                <span className="font-semibold text-lg text-gray-900 dark:text-white">{memoryStatus.active_sessions}</span>
              </div>
              <div className="flex justify-between items-center">
                <span className="text-gray-600 dark:text-gray-300">Memories:</span>
                <span className="font-medium text-gray-900 dark:text-white">{memoryStatus.total_memories}</span>
              </div>
              <div className="flex justify-between items-center">
                <span className="text-gray-600 dark:text-gray-300">Size:</span>
                <span className="font-medium text-gray-900 dark:text-white">{memoryStatus.memory_size_mb.toFixed(2)} MB</span>
              </div>
            </div>

            {memoryStatus.active_sessions > 0 && (
              <button
                onClick={clearAllMemory}
                className="mt-4 w-full px-4 py-2 bg-red-50 dark:bg-red-900/20 text-red-600 dark:text-red-400 rounded-lg hover:bg-red-100 dark:hover:bg-red-900/30 transition-colors flex items-center justify-center border border-red-200 dark:border-red-800"
              >
                <Trash2 className="w-4 h-4 mr-2" />
                Clear Memory
              </button>
            )}
          </div>

          {/* Quick Actions */}
          <div className="bg-white dark:bg-gray-800 rounded-xl shadow-lg border border-gray-100 dark:border-gray-700 p-6 hover:shadow-xl transition-all duration-300">
            <div className="flex items-center justify-between mb-4">
              <div className="flex items-center">
                <div className="p-2 bg-green-100 rounded-lg mr-3">
                  <Zap className="w-6 h-6 text-green-600" />
                </div>
                <div>
                  <h3 className="text-lg font-semibold text-gray-900 dark:text-white">Quick Actions</h3>
                  <p className="text-sm text-gray-500 dark:text-gray-400">System Controls</p>
                </div>
              </div>
            </div>
            
            <div className="space-y-3">
              <button
                onClick={() => checkVectorDBStatus(true)}
                className="w-full px-4 py-2 bg-blue-50 dark:bg-blue-900/20 text-blue-600 dark:text-blue-400 rounded-lg hover:bg-blue-100 dark:hover:bg-blue-900/30 transition-colors flex items-center justify-center border border-blue-200 dark:border-blue-800"
              >
                <RefreshCw className="w-4 h-4 mr-2" />
                Refresh Status
              </button>
              <button
                onClick={() => setShowAdvanced(!showAdvanced)}
                className="w-full px-4 py-2 bg-gray-50 dark:bg-gray-700 text-gray-600 dark:text-gray-300 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-600 transition-colors flex items-center justify-center border border-gray-200 dark:border-gray-600"
              >
                <Settings className="w-4 h-4 mr-2" />
                {showAdvanced ? 'Hide' : 'Show'} Advanced
              </button>
            </div>
          </div>
        </div>

        {/* Upload Section */}
        <div className="bg-white dark:bg-gray-800 rounded-2xl shadow-xl border border-gray-100 dark:border-gray-700 p-8 mb-8">
          <div className="text-center mb-8">
            <h2 className="text-2xl font-bold text-gray-900 dark:text-white mb-2">Upload Your Documentation</h2>
            <p className="text-gray-600 dark:text-gray-300">Paste your API documentation content below</p>
          </div>

          <form onSubmit={handleSubmit}>
              <div className="mb-6">
                <label htmlFor="title" className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                  Documentation Title
                </label>
                <input
                  type="text"
                  id="title"
                  value={title}
                  onChange={(e) => setTitle(e.target.value)}
                  className="w-full px-4 py-3 border border-gray-300 dark:border-gray-600 rounded-xl focus:ring-2 focus:ring-blue-500 focus:border-transparent transition-all duration-200 bg-white dark:bg-gray-700 text-gray-900 dark:text-white placeholder-gray-500 dark:placeholder-gray-400"
                  placeholder="Enter a title for your documentation"
                />
              </div>

              <div className="mb-6">
                <label htmlFor="documentation" className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                  Documentation Content
                </label>
                <textarea
                  id="documentation"
                  value={documentation}
                  onChange={(e) => setDocumentation(e.target.value)}
                  rows="12"
                  className="w-full px-4 py-3 border border-gray-300 dark:border-gray-600 rounded-xl focus:ring-2 focus:ring-blue-500 focus:border-transparent resize-none transition-all duration-200 bg-white dark:bg-gray-700 text-gray-900 dark:text-white placeholder-gray-500 dark:placeholder-gray-400"
                  placeholder="Paste your API documentation here (Markdown format supported)..."
                />
              </div>

              {/* Progress Bar */}
              {isProcessing && (
                <div className="mb-6">
                  <div className="flex items-center justify-between mb-2">
                    <span className="text-sm font-medium text-gray-700 dark:text-gray-300">Processing Documentation</span>
                    <span className="text-sm text-gray-500 dark:text-gray-400">{Math.round(processingProgress)}%</span>
                  </div>
                  <div className="w-full bg-gray-200 dark:bg-gray-700 rounded-full h-2">
                    <div
                      className="bg-gradient-to-r from-blue-500 to-indigo-600 h-2 rounded-full transition-all duration-300 ease-out"
                      style={{ width: `${processingProgress}%` }}
                    ></div>
                  </div>
                </div>
              )}

              {/* Error Message */}
              {error && (
                <div className="mb-6 p-4 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-xl">
                  <div className="flex items-center">
                    <AlertCircle className="w-5 h-5 text-red-600 dark:text-red-400 mr-3" />
                    <span className="text-red-800 dark:text-red-200 font-medium">{error}</span>
                  </div>
                </div>
              )}

              {/* Success Message */}
              {result && (
                <div className="mb-6 p-6 bg-green-50 dark:bg-green-900/20 border border-green-200 dark:border-green-800 rounded-xl">
                  <div className="flex items-center mb-4">
                    <CheckCircle className="w-6 h-6 text-green-600 dark:text-green-400 mr-3" />
                    <span className="text-green-800 dark:text-green-200 font-semibold text-lg">{result.message}</span>
                  </div>
                  <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-3 sm:gap-4 text-sm mb-4">
                    <div className="bg-white dark:bg-gray-800 rounded-lg p-3 border border-green-200 dark:border-green-700">
                      <div className="text-green-600 dark:text-green-400 font-medium">Sections</div>
                      <div className="text-2xl font-bold text-green-800 dark:text-green-200">{result.sections || 0}</div>
                    </div>
                    <div className="bg-white dark:bg-gray-800 rounded-lg p-3 border border-green-200 dark:border-green-700">
                      <div className="text-green-600 dark:text-green-400 font-medium">Chunks</div>
                      <div className="text-2xl font-bold text-green-800 dark:text-green-200">{result.chunks || 0}</div>
                    </div>
                    <div className="bg-white dark:bg-gray-800 rounded-lg p-3 border border-green-200 dark:border-green-700">
                      <div className="text-green-600 dark:text-green-400 font-medium">Database Size</div>
                      <div className="text-2xl font-bold text-green-800 dark:text-green-200">{result.db_size_mb || 0} MB</div>
                    </div>
                  </div>
                  <div className="flex flex-col sm:flex-row gap-3">
                    <button
                      onClick={() => navigate('/chat')}
                      className="flex-1 px-6 py-3 bg-gradient-to-r from-green-600 to-emerald-600 text-white rounded-lg hover:from-green-700 hover:to-emerald-700 transition-all duration-200 flex items-center justify-center font-semibold shadow-lg hover:shadow-xl transform hover:-translate-y-0.5"
                    >
                      <MessageSquare className="w-5 h-5 mr-2" />
                      Start Chatting
                    </button>
                    <button
                      onClick={() => {
                        setResult(null);
                        setDocumentation('');
                        setTitle('API Documentation');
                      }}
                      className="flex-1 px-6 py-3 bg-gray-100 text-gray-700 rounded-lg hover:bg-gray-200 transition-all duration-200 flex items-center justify-center font-semibold"
                    >
                      <Upload className="w-5 h-5 mr-2" />
                      Upload Another
                    </button>
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
          <div className="bg-white dark:bg-gray-800 rounded-2xl shadow-xl border border-gray-100 dark:border-gray-700 p-8">
            <h3 className="text-xl font-bold text-gray-900 dark:text-white mb-6">Advanced Settings</h3>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 sm:gap-6">
              <div className="space-y-4">
                <h4 className="font-semibold text-gray-700 dark:text-gray-300">System Information</h4>
                <div className="space-y-2 text-sm">
                  <div className="flex justify-between">
                    <span className="text-gray-600 dark:text-gray-400">Vector DB Status:</span>
                    <span className={vectorDBStatus.is_ready ? "text-green-600 dark:text-green-400" : "text-red-600 dark:text-red-400"}>
                      {vectorDBStatus.is_ready ? "Ready" : "Not Ready"}
                    </span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-gray-600 dark:text-gray-400">Memory Sessions:</span>
                    <span className="text-gray-900 dark:text-white">{memoryStatus.active_sessions}</span>
                  </div>
                </div>
              </div>
              <div className="space-y-4">
                <h4 className="font-semibold text-gray-700 dark:text-gray-300">Quick Actions</h4>
                <div className="space-y-2">
                  <button
                    onClick={() => checkVectorDBStatus(true)}
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