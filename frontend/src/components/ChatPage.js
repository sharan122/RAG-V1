import React, { useState, useEffect, useRef } from "react";
import "./Chat.css";
import { useTheme } from '../contexts/ThemeContext';
import { 
  Send, 
  Bot, 
  User, 
  Copy, 
  Download, 
  RefreshCw, 
  Settings, 
  MessageSquare, 
  Search,
  Zap,
  BookOpen,
  Trash2,
  MoreVertical,
  ThumbsUp,
  ThumbsDown
} from 'lucide-react';

function TypingDots() {
  return (
    <span className="typing-dots">
      <span>.</span>
      <span>.</span>
      <span>.</span>
    </span>
  );
}

function CodeBlock({ language = "bash", code = "" }) {
  const onCopy = () => navigator.clipboard.writeText(code);
  return (
    <div className="resp-code">
      <div className="resp-code-header">
        <span className="resp-code-lang">{language}</span>
        <button className="resp-copy" onClick={onCopy} title="Copy to clipboard">Copy</button>
      </div>
      <pre><code>{code}</code></pre>
    </div>
  );
}



function ResponseRenderer({ data }) {
  if (!data) return null;
  
  // Helper function to clean up text formatting
  const cleanText = (text) => {
    if (typeof text !== 'string') return text;
    return text
      .replace(/\n/g, '\n')
      .replace(/\\'/g, "'")
      .replace(/\\"/g, '"')
      .trim();
  };

  // Helper function to render code examples (handles both string and array)
  const renderCodeExample = (code, language) => {
    if (!code) return null;
    
    if (Array.isArray(code)) {
      // If it's an array, join with double newlines for separation
      const combinedCode = code.join('\n\n');
      return <CodeBlock language={language} code={cleanText(combinedCode)} />;
    } else {
      // If it's a string, use as-is
      return <CodeBlock language={language} code={cleanText(code)} />;
    }
  };

  // Normalize: if data.answer contains a JSON string with our structure, unwrap it
  const normalizeData = (raw) => {
    try {
      if (raw && typeof raw.answer === 'string') {
        const trimmed = raw.answer.trim();
        if (trimmed.startsWith('{') && trimmed.endsWith('}')) {
          const inner = JSON.parse(trimmed);
          if (inner && typeof inner === 'object') {
            return {
              answer: inner.answer ?? '',
              description: inner.description ?? '',
              endpoints: Array.isArray(inner.endpoints) ? inner.endpoints : [],
              code_examples: inner.code_examples ?? null,
              links: Array.isArray(inner.links) ? inner.links : [],
            };
          }
        }
      }
    } catch (e) {
      // fall through to return raw as-is
    }
    return {
      answer: raw?.answer ?? '',
      description: raw?.description ?? '',
      endpoints: Array.isArray(raw?.endpoints) ? raw.endpoints : [],
      code_examples: raw?.code_examples ?? null,
      links: Array.isArray(raw?.links) ? raw.links : [],
    };
  };

  const normalized = normalizeData(data);

  // Extract data from the normalized response structure
  const answer = normalized.answer || "";
  const description = normalized.description || "";
  const endpoints = normalized.endpoints || [];
  const code_examples = normalized.code_examples || null;
  const links = normalized.links || [];

  // Only render sections that have content
  const hasDescription = description && description.trim();
  const hasEndpoints = endpoints && endpoints.length > 0;
  const hasCodeExamples = code_examples && (
    code_examples.curl || 
    code_examples.python || 
    code_examples.javascript
  );
  const hasLinks = links && links.length > 0;

  return (
    <div className="resp-root">
      {/* Answer */}
      {answer && (
        <div className="resp-section">
          <h3 className="resp-section-title">Answer</h3>
          <div className="resp-answer">
            {cleanText(answer)}
          </div>
        </div>
      )}

      {/* Description */}
      {hasDescription && (
        <div className="resp-section">
          <h3 className="resp-section-title">Description</h3>
          <div className="resp-description">
            {cleanText(description)}
          </div>
        </div>
      )}

      {/* Endpoints */}
      {hasEndpoints && (
        <div className="resp-section">
          <h3 className="resp-section-title">API Endpoints</h3>
          <div className="resp-endpoints">
            {endpoints.map((endpoint, i) => (
              <div key={i} className="resp-endpoint">
                <div className="resp-endpoint-header">
                  <span className="resp-endpoint-method">{endpoint.method}</span>
                  <span className="resp-endpoint-url">{endpoint.url}</span>
                </div>
                
                {endpoint.params && Object.keys(endpoint.params).length > 0 && (
                  <div className="resp-endpoint-params">
                    <h4>Parameters:</h4>
                    <div className="resp-params">
                      {Object.entries(endpoint.params).map(([key, value]) => (
                        <div key={key} className="resp-param-item">
                          <span className="resp-param-key">{key}:</span>
                          <span className="resp-param-value">{value}</span>
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                {endpoint.response_example && (
                  <div className="resp-endpoint-response">
                    <h4>Response Example:</h4>
                    <CodeBlock 
                      language="json" 
                      code={JSON.stringify(endpoint.response_example, null, 2)} 
                    />
                  </div>
                )}
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Code Examples */}
      {hasCodeExamples && (
        <div className="resp-section">
          <h3 className="resp-section-title">Code Examples</h3>
          <div className="resp-code-examples">
            {code_examples.curl && (
              <div className="resp-code-example">
                <h4>cURL</h4>
                {renderCodeExample(code_examples.curl, "bash")}
              </div>
            )}
            {code_examples.python && (
              <div className="resp-code-example">
                <h4>Python</h4>
                {renderCodeExample(code_examples.python, "python")}
              </div>
            )}
            {code_examples.javascript && (
              <div className="resp-code-example">
                <h4>JavaScript</h4>
                {renderCodeExample(code_examples.javascript, "javascript")}
              </div>
            )}
          </div>
        </div>
      )}

      {/* Links */}
      {hasLinks && (
        <div className="resp-section">
          <h3 className="resp-section-title">Related Links</h3>
          <div className="resp-links">
            {links.map((link, i) => (
              <a key={i} href={link} target="_blank" rel="noopener noreferrer" className="resp-link">
                {link}
              </a>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

function Chat() {
  const { isDark } = useTheme();
  const [input, setInput] = useState("");
  const [history, setHistory] = useState([]);
  const [loading, setLoading] = useState(false);
  const [streamMsg, setStreamMsg] = useState(null);
  const [showSettings, setShowSettings] = useState(false);
  const [chatMode, setChatMode] = useState('normal'); // normal, streaming
  const [systemStatus, setSystemStatus] = useState({
    is_ready: false,
    documents_count: 0,
    memory_count: 0
  });
  const messagesEndRef = useRef(null);
  const inputRef = useRef(null);

  // Auto-scroll to bottom when new messages arrive
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [history, streamMsg]);

  // Check system status on mount
  useEffect(() => {
    checkSystemStatus();
  }, []);

  const checkSystemStatus = async () => {
    try {
      const response = await fetch('http://localhost:8000/docs/status');
      const data = await response.json();
      setSystemStatus({
        is_ready: data.vectorstore?.status === "ready",
        documents_count: data.vectorstore?.document_count || 0,
        memory_count: data.memory_count || 0
      });
    } catch (error) {
      console.error('Failed to check system status:', error);
    }
  };



  const handleStream = (question) => {
    setStreamMsg("");
    setLoading(true);
    const userMessage = { role: "user", content: question };
    setHistory((h) => [...h, userMessage]);

    // Use regular endpoint
    handleRegularQuestion(question);
  };

  const handleStreamingQuestion = (question) => {
    // Use fetch with streaming instead of EventSource
    fetch("http://localhost:8000/questions/ask/stream", {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ question, session_id: "default" })
    })
    .then(response => {
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }
      
      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let streamedResponse = "";

      const readStream = () => {
        return reader.read().then(({ done, value }) => {
          if (done) {
            // End of stream
            setStreamMsg(null);
            setLoading(false);
            
            // Add the complete response to history
            setHistory((h) => [
              ...h,
              {
                role: "bot",
                data: { 
                  answer: streamedResponse,
                  description: "",
                  endpoints: [],
                  code_examples: null,
                  links: []
                },
                content: streamedResponse,
                sources: [],
              },
            ]);
            return;
          }

          // Decode the chunk
          const chunk = decoder.decode(value, { stream: true });
          const lines = chunk.split('\n');
          
          for (const line of lines) {
            if (line.startsWith('data: ')) {
              try {
                const data = JSON.parse(line.slice(6));
                
                if (data.data === '[END]') {
                  // End of stream
                  setStreamMsg(null);
                  setLoading(false);
                  
                  // Add the complete response to history
                  setHistory((h) => [
                    ...h,
                    {
                      role: "bot",
                      data: { 
                        answer: streamedResponse,
                        description: "",
                        endpoints: [],
                        code_examples: null,
                        links: []
                      },
                      content: streamedResponse,
                      sources: [],
                    },
                  ]);
                  return;
                } else if (data.memory_count) {
                  // Memory count received
                  console.log("Memory count:", data.memory_count);
                } else if (data.data) {
                  // Character data
                  streamedResponse += data.data;
                  setStreamMsg(streamedResponse);
                }
              } catch (error) {
                console.error("Error parsing stream data:", error);
              }
            }
          }
          
          // Continue reading
          return readStream();
        });
      };

      return readStream();
    })
    .catch(error => {
      console.error("Stream error:", error);
      setStreamMsg(null);
      setLoading(false);
      
      setHistory((h) => [
        ...h,
        { 
          role: "bot", 
          data: {
            answer: "Error in streaming response.",
            description: "An error occurred while processing the streaming response.",
            endpoints: [],
            code_examples: null,
            links: []
          },
          content: "Error in streaming response." 
        },
      ]);
    });
  };

  const handleRegularQuestion = (question) => {
    // Use new modular API endpoint
    fetch("http://localhost:8000/questions/ask", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ 
        question, 
        session_id: "default" 
      }),
    })
      .then((res) => res.json())
      .then((data) => {
        setHistory((h) => [
          ...h,
          {
            role: "bot",
            data,
            content: data.answer || data.description || "Response received",
            sources: data.sources || [],
          },
        ]);
        setStreamMsg(null);
        setLoading(false);
      })
      .catch(() => {
        setHistory((h) => [
          ...h,
          { 
            role: "bot", 
            data: {
              answer: "Error contacting backend.",
              description: "Unable to connect to the backend service.",
              endpoints: [],
              code_examples: null,
              links: []
            },
            content: "Error contacting backend." 
          },
        ]);
        setStreamMsg(null);
        setLoading(false);
      });
  };

  const handleSend = (e) => {
    e.preventDefault();
    if (!input.trim()) return;
    
    if (chatMode === 'streaming') {
      handleStreamingQuestion(input);
    } else {
      handleStream(input);
    }
    setInput("");
  };

  const clearChat = () => {
    setHistory([]);
    setStreamMsg(null);
  };

  const copyToClipboard = (text) => {
    navigator.clipboard.writeText(text);
  };

  const downloadChat = () => {
    const chatData = {
      timestamp: new Date().toISOString(),
      messages: history
    };
    const blob = new Blob([JSON.stringify(chatData, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `chat-export-${new Date().toISOString().split('T')[0]}.json`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  };

  const handleKeyPress = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend(e);
    }
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 via-white to-indigo-50 dark:from-gray-900 dark:via-gray-800 dark:to-gray-900 transition-colors duration-200">
      <div className="max-w-6xl mx-auto p-6">
        {/* Header */}
        <div className="bg-white dark:bg-gray-800 rounded-2xl shadow-xl border border-gray-100 dark:border-gray-700 p-6 mb-6">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between">
            <div className="flex items-center mb-4 sm:mb-0">
              <div className="p-3 bg-gradient-to-r from-blue-600 to-indigo-600 rounded-xl mr-4">
                <MessageSquare className="w-8 h-8 text-white" />
              </div>
              <div>
                <h1 className="text-xl sm:text-2xl font-bold text-gray-900 dark:text-white">AI Documentation Assistant</h1>
                <p className="text-sm sm:text-base text-gray-600 dark:text-gray-300">Ask questions about your API documentation</p>
              </div>
            </div>
            <div className="flex items-center space-x-3">
              {/* System Status */}
              <div className="flex items-center space-x-2 px-3 py-2 bg-gray-50 dark:bg-gray-700 rounded-lg">
                <div className={`w-2 h-2 rounded-full ${systemStatus.is_ready ? 'bg-green-500' : 'bg-red-500'}`}></div>
                <span className="text-sm text-gray-600 dark:text-gray-300">
                  {systemStatus.is_ready ? 'Ready' : 'Not Ready'}
                </span>
              </div>
              {/* Settings Button */}
              <button
                onClick={() => setShowSettings(!showSettings)}
                className="p-2 text-gray-400 dark:text-gray-500 hover:text-gray-600 dark:hover:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700 rounded-lg transition-colors"
              >
                <Settings className="w-5 h-5" />
              </button>
            </div>
          </div>

          {/* Settings Panel */}
          {showSettings && (
            <div className="mt-6 p-4 bg-gray-50 dark:bg-gray-700 rounded-xl border border-gray-200 dark:border-gray-600">
              <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">Chat Mode</label>
                  <select
                    value={chatMode}
                    onChange={(e) => setChatMode(e.target.value)}
                    className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent bg-white dark:bg-gray-800 text-gray-900 dark:text-white"
                  >
                    <option value="normal">Normal</option>
                    <option value="streaming">Streaming</option>
                  </select>
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">System Status</label>
                  <div className="text-sm text-gray-600 dark:text-gray-300">
                    <div>Documents: {systemStatus.documents_count}</div>
                    <div>Memory: {systemStatus.memory_count} messages</div>
                  </div>
                </div>
                <div className="flex items-end space-x-2">
                  <button
                    onClick={clearChat}
                    className="px-4 py-2 bg-red-50 text-red-600 rounded-lg hover:bg-red-100 transition-colors flex items-center"
                  >
                    <Trash2 className="w-4 h-4 mr-2" />
                    Clear Chat
                  </button>
                  <button
                    onClick={downloadChat}
                    className="px-4 py-2 bg-blue-50 text-blue-600 rounded-lg hover:bg-blue-100 transition-colors flex items-center"
                  >
                    <Download className="w-4 h-4 mr-2" />
                    Export
                  </button>
                </div>
              </div>
            </div>
          )}
        </div>

        {/* Chat Interface */}
        <div className="bg-white dark:bg-gray-800 rounded-2xl shadow-xl border border-gray-100 dark:border-gray-700 overflow-hidden">
          {/* Chat Messages */}
          <div className="h-96 overflow-y-auto p-6 space-y-4">
            {history.length === 0 ? (
              <div className="text-center py-12">
                <div className="w-16 h-16 bg-gray-100 dark:bg-gray-700 rounded-full flex items-center justify-center mx-auto mb-4">
                  <Bot className="w-8 h-8 text-gray-400 dark:text-gray-500" />
                </div>
                <h3 className="text-lg font-medium text-gray-900 dark:text-white mb-2">Start a conversation</h3>
                <p className="text-gray-500 dark:text-gray-400">Ask me anything about your API documentation</p>
                <div className="mt-6 grid grid-cols-1 sm:grid-cols-2 gap-3 max-w-md mx-auto">
                  <button
                    onClick={() => setInput("What endpoints are available?")}
                    className="p-3 text-left bg-gray-50 dark:bg-gray-700 hover:bg-gray-100 dark:hover:bg-gray-600 rounded-lg transition-colors text-gray-900 dark:text-white"
                  >
                    <Search className="w-4 h-4 inline mr-2" />
                    What endpoints are available?
                  </button>
                  <button
                    onClick={() => setInput("How do I authenticate?")}
                    className="p-3 text-left bg-gray-50 dark:bg-gray-700 hover:bg-gray-100 dark:hover:bg-gray-600 rounded-lg transition-colors text-gray-900 dark:text-white"
                  >
                    <Zap className="w-4 h-4 inline mr-2" />
                    How do I authenticate?
                  </button>
                </div>
              </div>
            ) : (
              history.map((msg, i) => (
                <div
                  key={i}
                  className={`flex ${msg.role === "user" ? "justify-end" : "justify-start"}`}
                >
                  <div
                    className={`max-w-3xl px-4 py-3 rounded-2xl ${
                      msg.role === "user"
                        ? "bg-gradient-to-r from-blue-600 to-indigo-600 text-white"
                        : "bg-gray-100 dark:bg-gray-700 text-gray-900 dark:text-white"
                    }`}
                  >
                    <div className="flex items-start space-x-3">
                      <div className={`p-1 rounded-full ${
                        msg.role === "user" ? "bg-white/20" : "bg-gray-200 dark:bg-gray-600"
                      }`}>
                        {msg.role === "user" ? (
                          <User className="w-4 h-4" />
                        ) : (
                          <Bot className="w-4 h-4" />
                        )}
                      </div>
                      <div className="flex-1">
                        {msg.role === "bot" && msg.data ? (
                          <ResponseRenderer data={msg.data} />
                        ) : (
                          <div className="whitespace-pre-wrap">{msg.content}</div>
                        )}
                        {msg.role === "bot" && msg.sources && msg.sources.length > 0 && (
                          <div className="mt-3 pt-3 border-t border-gray-300 dark:border-gray-600">
                            <div className="text-sm font-medium text-gray-600 dark:text-gray-300 mb-2">Sources:</div>
                            <ul className="text-sm space-y-1">
                              {msg.sources.map((src, j) => (
                                <li key={j} className="text-gray-500 dark:text-gray-400">
                                  {src.title} — {src.source}
                                </li>
                              ))}
                            </ul>
                          </div>
                        )}
                      </div>
                    </div>
                  </div>
                </div>
              ))
            )}
            
            {streamMsg !== null && (
              <div className="flex justify-start">
                <div className="max-w-3xl px-4 py-3 rounded-2xl bg-gray-100 dark:bg-gray-700 text-gray-900 dark:text-white">
                  <div className="flex items-start space-x-3">
                    <div className="p-1 rounded-full bg-gray-200 dark:bg-gray-600">
                      <Bot className="w-4 h-4" />
                    </div>
                    <div className="flex-1">
                      <div className="whitespace-pre-wrap">{streamMsg}</div>
                      <TypingDots />
                    </div>
                  </div>
                </div>
              </div>
            )}
            <div ref={messagesEndRef} />
          </div>

          {/* Input Area */}
          <div className="border-t border-gray-200 dark:border-gray-700 p-4">
            <form onSubmit={handleSend} className="flex flex-col sm:flex-row space-y-3 sm:space-y-0 sm:space-x-3">
              <div className="flex-1 relative">
                <input
                  ref={inputRef}
                  type="text"
                  value={input}
                  onChange={(e) => setInput(e.target.value)}
                  onKeyPress={handleKeyPress}
                  placeholder="Ask a question about your API documentation..."
                  className="w-full px-4 py-3 pr-12 border border-gray-300 dark:border-gray-600 rounded-xl focus:ring-2 focus:ring-blue-500 focus:border-transparent transition-all duration-200 bg-white dark:bg-gray-700 text-gray-900 dark:text-white placeholder-gray-500 dark:placeholder-gray-400"
                  disabled={loading || streamMsg !== null}
                />
                {input && (
                  <button
                    type="button"
                    onClick={() => copyToClipboard(input)}
                    className="absolute right-3 top-1/2 transform -translate-y-1/2 p-1 text-gray-400 dark:text-gray-500 hover:text-gray-600 dark:hover:text-gray-300"
                  >
                    <Copy className="w-4 h-4" />
                  </button>
                )}
              </div>
              <button
                type="submit"
                disabled={loading || streamMsg !== null || !input.trim()}
                className="px-6 py-3 bg-gradient-to-r from-blue-600 to-indigo-600 text-white rounded-xl hover:from-blue-700 hover:to-indigo-700 disabled:opacity-50 disabled:cursor-not-allowed transition-all duration-200 flex items-center space-x-2 shadow-lg hover:shadow-xl"
              >
                <Send className="w-5 h-5" />
                <span>Send</span>
              </button>
            </form>
          </div>
        </div>
      </div>
    </div>
  );
}

export default Chat;