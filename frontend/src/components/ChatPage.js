import React, { useState, useEffect, useRef } from 'react';
import axios from 'axios';
import ReactMarkdown from 'react-markdown';
import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter';
import { tomorrow } from 'react-syntax-highlighter/dist/esm/styles/prism';
import { 
  Send, 
  MessageCircle, 
  Loader2, 
  CheckCircle, 
  AlertCircle,
  Copy,
  Database,
  User,
  Bot,
  Brain,
  Trash2,
  Code,
  FileText,
  AlertTriangle,
  Info,
  Link,
  List,
  Table,
  Terminal
} from 'lucide-react';

const API_BASE_URL = 'http://localhost:8000';

function TypingDots() {
  return (
    <span className="inline-flex space-x-1">
      <span className="w-1 h-1 bg-blue-600 rounded-full animate-bounce"></span>
      <span className="w-1 h-1 bg-blue-600 rounded-full animate-bounce" style={{ animationDelay: '0.1s' }}></span>
      <span className="w-1 h-1 bg-blue-600 rounded-full animate-bounce" style={{ animationDelay: '0.2s' }}></span>
    </span>
  );
}

// Structured Response Component
function StructuredResponse({ type, content }) {
  // Add more explicit styling for each type
  switch (type) {
    case 'error':
      return (
        <div className="bg-red-50 border-l-4 border-red-500 rounded-r-lg p-4">
          <div className="flex items-start">
            <AlertCircle className="w-5 h-5 text-red-600 mr-3 mt-0.5 flex-shrink-0" />
            <div className="text-sm text-red-800">
              <div className="font-medium mb-1">Error:</div>
              {Array.isArray(content.errors)
                ? content.errors.map((err, idx) => <div key={idx}>{err}</div>)
                : content.errors}
            </div>
          </div>
        </div>
      );
    case 'warning':
      return (
        <div className="bg-yellow-50 border-l-4 border-yellow-500 rounded-r-lg p-4">
          <div className="flex items-start">
            <AlertTriangle className="w-5 h-5 text-yellow-600 mr-3 mt-0.5 flex-shrink-0" />
            <div className="text-sm text-yellow-800">
              <div className="font-medium mb-1">Warning:</div>
              {Array.isArray(content.warnings)
                ? content.warnings.map((warn, idx) => <div key={idx}>{warn}</div>)
                : content.warnings}
            </div>
          </div>
        </div>
      );
    case 'explanatory':
      return <ExplanatoryResponse content={content} />;
    case 'short_answer':
      return (
        <div className="bg-green-50 border border-green-200 rounded-lg p-4">
          <div className="flex items-center">
            <CheckCircle className="w-5 h-5 text-green-600 mr-2" />
            <span className="text-lg font-semibold text-green-800">Answer</span>
          </div>
          <div className="text-gray-800 mt-2 text-base">{content.short_answer}</div>
        </div>
      );
    case 'values':
      return (
        <div className="bg-gray-50 border border-gray-200 rounded-lg p-4">
          <div className="flex items-center mb-2">
            <Info className="w-5 h-5 text-blue-600 mr-2" />
            <span className="text-md font-semibold text-gray-900">Values</span>
          </div>
          <ul className="list-disc list-inside space-y-1 text-gray-700">
            {content.values && Object.entries(content.values).map(([key, value], idx) => (
              <li key={idx}><span className="font-semibold">{key}:</span> {String(value)}</li>
            ))}
          </ul>
        </div>
      );
    case 'links':
      return (
        <div className="space-y-2">
          {content.links && content.links.map((link, idx) => (
            <div key={idx} className="bg-green-50 border border-green-200 rounded-lg p-3">
              <div className="flex items-center">
                <Link className="w-4 h-4 text-green-600 mr-2" />
                <a href={link} target="_blank" rel="noopener noreferrer" className="text-sm text-green-800 hover:text-green-600">
                  {link}
                </a>
              </div>
            </div>
          ))}
        </div>
      );
    case 'simple':
      return <SimpleResponse content={content} />;
    case 'code':
      return <CodeResponse content={content} />;
    case 'api':
      return <ApiResponse content={content} />;
    case 'table':
      return <TableResponse content={content} />;
    case 'list':
      return <ListResponse content={content} />;
    default:
      return <SimpleResponse content={content} />;
  }
}

// Simple Response Component
function SimpleResponse({ content }) {
  return (
    <div className="bg-white rounded-lg border p-4">
      <div className="flex items-center mb-3">
        <Info className="w-5 h-5 text-blue-600 mr-2" />
        <h3 className="text-lg font-semibold text-gray-900">Response</h3>
      </div>
      <div className="text-gray-700 leading-relaxed">
        {content.description}
      </div>
    </div>
  );
}

// Code Response Component
function CodeResponse({ content }) {
  return (
    <div className="space-y-4">
      {content.code_blocks.map((block, index) => (
        <div key={index} className="bg-gray-900 rounded-lg p-4">
          <div className="flex items-center justify-between mb-3">
            <div className="flex items-center">
              <Terminal className="w-5 h-5 text-green-400 mr-2" />
              <span className="text-sm text-gray-300 uppercase font-medium">
                {block.language}
              </span>
            </div>
            <button
              onClick={() => copyToClipboard(block.code)}
              className="text-xs text-gray-400 hover:text-white transition-colors"
            >
              Copy
            </button>
          </div>
          <SyntaxHighlighter
            style={tomorrow}
            language={block.language}
            className="!bg-transparent !p-0"
          >
            {block.code}
          </SyntaxHighlighter>
        </div>
      ))}
    </div>
  );
}

// API Response Component
function ApiResponse({ content }) {
  return (
    <div className="space-y-4">
      {/* Title */}
      {content.title && (
        <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
          <div className="flex items-center">
            <FileText className="w-5 h-5 text-blue-600 mr-2" />
            <h3 className="text-lg font-semibold text-blue-900">{content.title}</h3>
          </div>
        </div>
      )}

      {/* Description */}
      {content.description && (
        <div className="bg-white rounded-lg border p-4">
          <div className="text-gray-700 leading-relaxed">
            {content.description}
          </div>
        </div>
      )}

      {/* Code Blocks */}
      {content.code_blocks.map((block, index) => (
        <div key={index} className="bg-gray-900 rounded-lg p-4">
          <div className="flex items-center justify-between mb-3">
            <div className="flex items-center">
              <Code className="w-5 h-5 text-green-400 mr-2" />
              <span className="text-sm text-gray-300 uppercase font-medium">
                {block.title} ({block.language})
              </span>
            </div>
            <button
              onClick={() => copyToClipboard(block.code)}
              className="text-xs text-gray-400 hover:text-white transition-colors"
            >
              Copy
            </button>
          </div>
          <SyntaxHighlighter
            style={tomorrow}
            language={block.language}
            className="!bg-transparent !p-0"
          >
            {block.code}
          </SyntaxHighlighter>
        </div>
      ))}

      {/* Tables */}
      {content.tables.map((table, index) => (
        <div key={index} className="bg-white rounded-lg border p-4">
          <div className="flex items-center mb-3">
            <Table className="w-5 h-5 text-purple-600 mr-2" />
            <h4 className="text-md font-semibold text-gray-900">Parameters</h4>
          </div>
          <div className="overflow-x-auto">
            <table className="min-w-full border border-gray-200 rounded-lg">
              <thead className="bg-gray-50">
                <tr>
                  {table.headers.map((header, idx) => (
                    <th key={idx} className="px-4 py-3 text-left text-sm font-medium text-gray-700 border-b border-gray-200">
                      {header}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {table.rows.map((row, rowIdx) => (
                  <tr key={rowIdx} className={rowIdx % 2 === 0 ? 'bg-white' : 'bg-gray-50'}>
                    {row.map((cell, cellIdx) => (
                      <td key={cellIdx} className="px-4 py-3 text-sm text-gray-600 border-b border-gray-100">
                        {cell}
                      </td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      ))}

      {/* Lists */}
      {content.lists.map((list, index) => (
        <div key={index} className="bg-white rounded-lg border p-4">
          <div className="flex items-center mb-3">
            <List className="w-5 h-5 text-orange-600 mr-2" />
            <h4 className="text-md font-semibold text-gray-900">Details</h4>
          </div>
          <ul className="list-disc list-inside space-y-2 text-gray-700">
            {list.map((item, itemIndex) => (
              <li key={itemIndex} className="leading-relaxed">{item}</li>
            ))}
          </ul>
        </div>
      ))}

      {/* Notes */}
      {content.notes.map((note, index) => (
        <div key={index} className="bg-blue-50 border-l-4 border-blue-500 rounded-r-lg p-4">
          <div className="flex items-start">
            <Info className="w-5 h-5 text-blue-600 mr-3 mt-0.5 flex-shrink-0" />
            <div className="text-sm text-blue-800">
              <div className="font-medium mb-1">Note:</div>
              {note}
            </div>
          </div>
        </div>
      ))}

      {/* Warnings */}
      {content.warnings.map((warning, index) => (
        <div key={index} className="bg-yellow-50 border-l-4 border-yellow-500 rounded-r-lg p-4">
          <div className="flex items-start">
            <AlertTriangle className="w-5 h-5 text-yellow-600 mr-3 mt-0.5 flex-shrink-0" />
            <div className="text-sm text-yellow-800">
              <div className="font-medium mb-1">Warning:</div>
              {warning}
            </div>
          </div>
        </div>
      ))}

      {/* Links */}
      {content.links.map((link, index) => (
        <div key={index} className="bg-green-50 border border-green-200 rounded-lg p-3">
          <div className="flex items-center">
            <Link className="w-4 h-4 text-green-600 mr-2" />
            <a href={link} target="_blank" rel="noopener noreferrer" className="text-sm text-green-800 hover:text-green-600">
              {link}
            </a>
          </div>
        </div>
      ))}
    </div>
  );
}

// Table Response Component
function TableResponse({ content }) {
  return (
    <div className="space-y-4">
      {content.tables.map((table, index) => (
        <div key={index} className="bg-white rounded-lg border p-4">
          <div className="flex items-center mb-3">
            <Table className="w-5 h-5 text-purple-600 mr-2" />
            <h3 className="text-lg font-semibold text-gray-900">Data Table</h3>
          </div>
          <div className="overflow-x-auto">
            <table className="min-w-full border border-gray-200 rounded-lg">
              <thead className="bg-gray-50">
                <tr>
                  {table.headers.map((header, idx) => (
                    <th key={idx} className="px-4 py-3 text-left text-sm font-medium text-gray-700 border-b border-gray-200">
                      {header}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {table.rows.map((row, rowIdx) => (
                  <tr key={rowIdx} className={rowIdx % 2 === 0 ? 'bg-white' : 'bg-gray-50'}>
                    {row.map((cell, cellIdx) => (
                      <td key={cellIdx} className="px-4 py-3 text-sm text-gray-600 border-b border-gray-100">
                        {cell}
                      </td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      ))}
    </div>
  );
}

// List Response Component
function ListResponse({ content }) {
  return (
    <div className="space-y-4">
      {content.lists.map((list, index) => (
        <div key={index} className="bg-white rounded-lg border p-4">
          <div className="flex items-center mb-3">
            <List className="w-5 h-5 text-orange-600 mr-2" />
            <h3 className="text-lg font-semibold text-gray-900">List</h3>
          </div>
          <ul className="list-disc list-inside space-y-2 text-gray-700">
            {list.map((item, itemIndex) => (
              <li key={itemIndex} className="leading-relaxed">{item}</li>
            ))}
          </ul>
        </div>
      ))}
    </div>
  );
}

// Explanatory Response Component
function ExplanatoryResponse({ content }) {
  return (
    <div className="space-y-4">
      <div className="bg-white rounded-lg border p-4">
        <div className="flex items-center mb-3">
          <Info className="w-5 h-5 text-blue-600 mr-2" />
          <h3 className="text-lg font-semibold text-gray-900">Explanation</h3>
        </div>
        <div className="text-gray-700 leading-relaxed whitespace-pre-wrap">
          {content.description}
        </div>
      </div>

      {/* Additional content */}
      {content.lists.length > 0 && <ListResponse content={content} />}
      {content.code_blocks.length > 0 && <CodeResponse content={content} />}
      {content.tables.length > 0 && <TableResponse content={content} />}
    </div>
  );
}

// Helper function to copy to clipboard
function copyToClipboard(text) {
  navigator.clipboard.writeText(text);
}

function ChatPage() {
  const [messages, setMessages] = useState([]);
  const [inputMessage, setInputMessage] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [streamMsg, setStreamMsg] = useState(null);
  const [streamType, setStreamType] = useState(null);
  const [streamContent, setStreamContent] = useState(null);
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
  const [showClearMemoryConfirm, setShowClearMemoryConfirm] = useState(false);
  const [sessionId] = useState(`session_${Date.now()}`);
  const messagesEndRef = useRef(null);

  // Check vector database status on component mount
  useEffect(() => {
    checkVectorDBStatus();
    checkMemoryStatus();
  }, []);

  // Auto-scroll to bottom when new messages are added
  useEffect(() => {
    scrollToBottom();
  }, [messages, streamMsg]);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

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

  const clearMemory = async () => {
    try {
      await axios.post(`${API_BASE_URL}/clear-memory`, {
        session_id: sessionId
      });
      setMessages([]);
      await checkMemoryStatus();
      setShowClearMemoryConfirm(false);
    } catch (error) {
      console.error('Failed to clear memory:', error);
    }
  };

  const handleStream = async (question) => {
    setStreamMsg(null);
    setStreamType(null);
    setStreamContent(null);
    setIsLoading(true);
    
    const userMessage = {
      id: Date.now(),
      type: 'user',
      content: question,
      timestamp: new Date().toLocaleTimeString()
    };
    
    setMessages(prev => [...prev, userMessage]);

    try {
      const response = await fetch(`${API_BASE_URL}/ask/stream`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          question: question,
          show_sources: false,
          session_id: sessionId
        })
      });

      console.log('Raw response object:', response);

      if (!response.body) throw new Error('No response body');
      
      const reader = response.body.getReader();
      let decoder = new TextDecoder();
      let answer = "";
      let memoryCount = 0;

      function readChunk() {
        reader.read().then(({ done, value }) => {
          if (done) {
            // Add the final message to history
            setMessages(prev => [...prev, {
              id: Date.now() + 1,
              type: 'bot',
              content: answer,
              timestamp: new Date().toLocaleTimeString()
            }]);
            setStreamMsg(null);
            setStreamType(null);
            setStreamContent(null);
            setIsLoading(false);
            checkMemoryStatus(); // Update memory status
            return;
          }

          const chunk = decoder.decode(value, { stream: true });
          console.log('Chunk received:', chunk);
          chunk.split("\n\n").forEach((event) => {
            if (event.startsWith("data: ")) {
              const data = event.slice(6);
              if (data === "[END]") {
                // End of answer
              } else {
                answer += data;
                setStreamMsg(answer);
              }
            } else if (event.startsWith("memory_count: ")) {
              try {
                memoryCount = parseInt(event.slice(14));
              } catch (e) {
                console.error('Error parsing memory count:', e);
              }
            }
          });
          readChunk();
        });
      }
      readChunk();
    } catch (error) {
      setMessages(prev => [...prev, {
        id: Date.now() + 1,
        type: 'bot',
        content: 'Error contacting backend.',
        timestamp: new Date().toLocaleTimeString()
      }]);
      setStreamMsg(null);
      setStreamType(null);
      setStreamContent(null);
      setIsLoading(false);
    }
  };

  const sendMessage = async () => {
    if (!inputMessage.trim() || isLoading) return;
    await handleStream(inputMessage);
    setInputMessage('');
  };

  const handleKeyPress = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    }
  };

  const copyToClipboard = (text) => {
    navigator.clipboard.writeText(text);
  };

  const renderMessageContent = (message) => {
    // Try to parse message.content as JSON
    let parsed = null;
    if (typeof message.content === 'string') {
      try {
        parsed = JSON.parse(message.content);
      } catch (e) {
        // Not JSON, fallback to markdown
      }
    } else if (typeof message.content === 'object' && message.content !== null) {
      parsed = message.content;
    }

    if (parsed && parsed.type) {
      // If error type, check for nested error object
      if (parsed.type === 'error' && parsed.error && parsed.error.message) {
        return <StructuredResponse type="error" content={{ errors: [parsed.error.message] }} />;
      }
      // Use StructuredResponse for all structured types
      return <StructuredResponse type={parsed.type} content={parsed} />;
    } else if (parsed && parsed.errors) {
      // Error type fallback
      return <StructuredResponse type="error" content={parsed} />;
    } else if (message.responseType && message.content) {
      return <StructuredResponse type={message.responseType} content={message.content} />;
    } else if (message.content) {
      // Fallback to markdown rendering
      return (
        <ReactMarkdown
          components={{
            h2: ({node, ...props}) => <h2 className="text-lg font-semibold text-gray-900 mb-3" {...props} />,
            h3: ({node, ...props}) => <h3 className="text-md font-semibold text-gray-800 mb-2" {...props} />,
            p: ({node, ...props}) => <p className="text-gray-700 leading-relaxed mb-3" {...props} />,
            ul: ({node, ...props}) => <ul className="list-disc list-inside space-y-1 mb-3" {...props} />,
            ol: ({node, ...props}) => <ol className="list-decimal list-inside space-y-1 mb-3" {...props} />,
            li: ({node, ...props}) => <li className="text-gray-700" {...props} />,
            table: ({node, ...props}) => (
              <div className="overflow-x-auto mb-4">
                <table className="min-w-full border border-gray-200 rounded-lg" {...props} />
              </div>
            ),
            th: ({node, ...props}) => (
              <th className="px-4 py-3 text-left text-sm font-medium text-gray-700 border-b border-gray-200 bg-gray-50" {...props} />
            ),
            td: ({node, ...props}) => (
              <td className="px-4 py-3 text-sm text-gray-600 border-b border-gray-100" {...props} />
            ),
            blockquote: ({node, ...props}) => (
              <div className="bg-blue-50 border-l-4 border-blue-500 rounded-r-lg p-4 mb-3">
                <div className="text-sm text-blue-800" {...props} />
              </div>
            ),
            strong: ({node, ...props}) => <strong className="font-semibold text-gray-900" {...props} />,
            code: ({node, inline, className, children, ...props}) => {
              const match = /language-(\w+)/.exec(className || '');
              return !inline ? (
                <div className="bg-gray-900 rounded-lg p-4 mb-3">
                  <div className="flex items-center justify-between mb-2">
                    <span className="text-sm text-gray-300 uppercase font-medium">
                      {match?.[1] || 'bash'}
                    </span>
                    <button
                      onClick={() => copyToClipboard(String(children))}
                      className="text-xs text-gray-400 hover:text-white transition-colors"
                    >
                      Copy
                    </button>
                  </div>
                  <SyntaxHighlighter
                    style={tomorrow}
                    language={match?.[1] || 'bash'}
                    className="!bg-transparent !p-0"
                    {...props}
                  >
                    {String(children).replace(/\n$/, '')}
                  </SyntaxHighlighter>
                </div>
              ) : (
                <code className="bg-gray-100 px-1 py-0.5 rounded text-sm font-mono" {...props}>
                  {children}
                </code>
              );
            }
          }}
        >
          {message.content}
        </ReactMarkdown>
      );
    }
    return null;
  };

  if (!vectorDBStatus.is_ready) {
    return (
      <div className="max-w-4xl mx-auto">
        <div className="text-center py-12">
          <Database className="w-16 h-16 text-gray-400 mx-auto mb-4" />
          <h2 className="text-2xl font-semibold text-gray-900 mb-2">Vector Database Not Ready</h2>
          <p className="text-gray-600 mb-6">
            Please upload documentation first to start chatting with your API documentation.
          </p>
          <div className="bg-blue-50 border border-blue-200 rounded-lg p-4 max-w-md mx-auto">
            <div className="flex items-center">
              <AlertCircle className="w-5 h-5 text-blue-600 mr-2" />
              <span className="text-blue-800 text-sm">
                Go to the Upload page to process your documentation
              </span>
            </div>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="max-w-5xl mx-auto h-screen flex flex-col">
      {/* Header */}
      <div className="bg-white border-b px-6 py-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center">
            <MessageCircle className="w-6 h-6 text-blue-600 mr-3" />
            <h1 className="text-xl font-semibold text-gray-900">Chat with Documentation</h1>
          </div>
          <div className="flex items-center space-x-4">
            <div className="text-sm text-gray-500">
              {vectorDBStatus.documents_count} documents • {vectorDBStatus.db_size_mb.toFixed(2)} MB
            </div>
            <div className="flex items-center space-x-2">
              <Brain className="w-4 h-4 text-purple-600" />
              <span className="text-sm text-gray-500">
                {memoryStatus.total_memories} memories • {memoryStatus.memory_size_mb.toFixed(2)} MB
              </span>
            </div>
            <button
              onClick={checkVectorDBStatus}
              className="text-sm text-blue-600 hover:text-blue-700"
            >
              Refresh Status
            </button>
            <button
              onClick={() => setShowClearMemoryConfirm(true)}
              className="text-sm text-red-600 hover:text-red-700 flex items-center"
            >
              <Trash2 className="w-4 h-4 mr-1" />
              Clear Memory
            </button>
          </div>
        </div>
      </div>

      {/* Memory Clear Confirmation Modal */}
      {showClearMemoryConfirm && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white rounded-lg p-6 max-w-md mx-4">
            <h3 className="text-lg font-semibold text-gray-900 mb-4">Clear Conversation Memory</h3>
            <p className="text-gray-600 mb-6">
              This will clear all conversation history for this session. The AI will no longer remember previous questions and answers.
            </p>
            <div className="flex space-x-3">
              <button
                onClick={clearMemory}
                className="flex-1 px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700"
              >
                Clear Memory
              </button>
              <button
                onClick={() => setShowClearMemoryConfirm(false)}
                className="flex-1 px-4 py-2 bg-gray-300 text-gray-700 rounded-lg hover:bg-gray-400"
              >
                Cancel
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Messages */}
      <div className="flex-1 overflow-y-auto p-6 space-y-6">
        {messages.length === 0 && streamMsg === null ? (
          <div className="text-center py-12">
            <MessageCircle className="w-12 h-12 text-gray-400 mx-auto mb-4" />
            <h3 className="text-lg font-medium text-gray-900 mb-2">Start a conversation</h3>
            <p className="text-gray-600">
              Ask questions about your API documentation and get structured, easy-to-read answers.
            </p>
          </div>
        ) : (
          <>
            {messages.map((message) => (
              <div
                key={message.id}
                className={`flex ${message.type === 'user' ? 'justify-end' : 'justify-start'}`}
              >
                <div className={`max-w-4xl ${message.type === 'user' ? 'bg-blue-600 text-white' : 'bg-gray-50 text-gray-900'} rounded-2xl px-6 py-4 shadow-sm`}>
                  <div className="flex items-start space-x-3">
                    <div className="flex-shrink-0 mt-1">
                      {message.type === 'user' ? (
                        <User className="w-5 h-5" />
                      ) : (
                        <Bot className="w-5 h-5 text-blue-600" />
                      )}
                    </div>
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center justify-between mb-3">
                        <span className="text-sm font-medium">
                          {message.type === 'user' ? 'You' : 'Assistant'}
                        </span>
                        <span className="text-xs opacity-70">{message.timestamp}</span>
                      </div>
                      
                      <div className="prose prose-sm max-w-none">
                        {renderMessageContent(message)}
                      </div>

                      {/* Copy button for bot messages */}
                      {message.type === 'bot' && message.content && (
                        <button
                          onClick={() => copyToClipboard(message.content)}
                          className="mt-3 text-xs text-blue-600 hover:text-blue-700 flex items-center"
                        >
                          <Copy className="w-3 h-3 mr-1" />
                          Copy response
                        </button>
                      )}
                    </div>
                  </div>
                </div>
              </div>
            ))}

            {/* Streaming message */}
            {streamMsg && (
              <div className="flex justify-start">
                <div className="max-w-4xl bg-gray-50 text-gray-900 rounded-2xl px-6 py-4 shadow-sm">
                  <div className="flex items-start space-x-3">
                    <div className="flex-shrink-0 mt-1">
                      <Bot className="w-5 h-5 text-blue-600" />
                    </div>
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center justify-between mb-3">
                        <span className="text-sm font-medium">Assistant</span>
                        <span className="text-xs opacity-70">{new Date().toLocaleTimeString()}</span>
                      </div>
                      
                      <div className="prose prose-sm max-w-none">
                        <ReactMarkdown
                          components={{
                            h2: ({node, ...props}) => <h2 className="text-lg font-semibold text-gray-900 mb-3" {...props} />,
                            h3: ({node, ...props}) => <h3 className="text-md font-semibold text-gray-800 mb-2" {...props} />,
                            p: ({node, ...props}) => <p className="text-gray-700 leading-relaxed mb-3" {...props} />,
                            ul: ({node, ...props}) => <ul className="list-disc list-inside space-y-1 mb-3" {...props} />,
                            ol: ({node, ...props}) => <ol className="list-decimal list-inside space-y-1 mb-3" {...props} />,
                            li: ({node, ...props}) => <li className="text-gray-700" {...props} />,
                            table: ({node, ...props}) => (
                              <div className="overflow-x-auto mb-4">
                                <table className="min-w-full border border-gray-200 rounded-lg" {...props} />
                              </div>
                            ),
                            th: ({node, ...props}) => (
                              <th className="px-4 py-3 text-left text-sm font-medium text-gray-700 border-b border-gray-200 bg-gray-50" {...props} />
                            ),
                            td: ({node, ...props}) => (
                              <td className="px-4 py-3 text-sm text-gray-600 border-b border-gray-100" {...props} />
                            ),
                            blockquote: ({node, ...props}) => (
                              <div className="bg-blue-50 border-l-4 border-blue-500 rounded-r-lg p-4 mb-3">
                                <div className="text-sm text-blue-800" {...props} />
                              </div>
                            ),
                            strong: ({node, ...props}) => <strong className="font-semibold text-gray-900" {...props} />,
                            code: ({node, inline, className, children, ...props}) => {
                              const match = /language-(\w+)/.exec(className || '');
                              return !inline ? (
                                <div className="bg-gray-900 rounded-lg p-4 mb-3">
                                  <div className="flex items-center justify-between mb-2">
                                    <span className="text-sm text-gray-300 uppercase font-medium">
                                      {match?.[1] || 'bash'}
                                    </span>
                                    <button
                                      onClick={() => copyToClipboard(String(children))}
                                      className="text-xs text-gray-400 hover:text-white transition-colors"
                                    >
                                      Copy
                                    </button>
                                  </div>
                                  <SyntaxHighlighter
                                    style={tomorrow}
                                    language={match?.[1] || 'bash'}
                                    className="!bg-transparent !p-0"
                                    {...props}
                                  >
                                    {String(children).replace(/\n$/, '')}
                                  </SyntaxHighlighter>
                                </div>
                              ) : (
                                <code className="bg-gray-100 px-1 py-0.5 rounded text-sm font-mono" {...props}>
                                  {children}
                                </code>
                              );
                            }
                          }}
                        >
                          {streamMsg}
                        </ReactMarkdown>
                        <TypingDots />
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            )}
          </>
        )}
        <div ref={messagesEndRef} />
      </div>

      {/* Input */}
      <div className="bg-white border-t p-6">
        <div className="flex space-x-4">
          <div className="flex-1">
            <textarea
              value={inputMessage}
              onChange={(e) => setInputMessage(e.target.value)}
              onKeyPress={handleKeyPress}
              placeholder="Ask a question about your API documentation... (Get structured, easy-to-read answers)"
              className="w-full p-4 border border-gray-300 rounded-xl resize-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              rows="2"
              disabled={isLoading || streamMsg !== null}
            />
          </div>
          <button
            onClick={sendMessage}
            disabled={isLoading || streamMsg !== null || !inputMessage.trim()}
            className="flex items-center px-6 py-4 bg-blue-600 text-white rounded-xl hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          >
            {isLoading ? (
              <Loader2 className="w-5 h-5 animate-spin" />
            ) : (
              <Send className="w-5 h-5" />
            )}
          </button>
        </div>
      </div>
    </div>
  );
}

export default ChatPage; 