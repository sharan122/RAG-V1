import React, { useState } from "react";
import "./Chat.css";

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
  const [input, setInput] = useState("");
  const [history, setHistory] = useState([]);
  const [loading, setLoading] = useState(false);
  const [streamMsg, setStreamMsg] = useState(null);



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
    handleStream(input);
    setInput("");
  };

  return (
    <div className="chat-root">
      <h2 className="chat-title">RAG Chat</h2>
      
      
      <div className="chat-window">
        {history.map((msg, i) => (
          <div
            key={i}
            className={`chat-bubble ${msg.role === "user" ? "user" : "bot"}`}
          >
            {msg.role === "bot" && msg.data ? (
              <ResponseRenderer data={msg.data} />
            ) : (
              <div className="chat-content" style={{ whiteSpace: "pre-line" }}>
                {msg.content}
              </div>
            )}
            {msg.role === "bot" && msg.sources && msg.sources.length > 0 && (
              <div className="chat-sources">
                <b>Sources:</b>
                <ul>
                  {msg.sources.map((src, j) => (
                    <li key={j}>
                      {src.title} — {src.source}
                    </li>
                  ))}
                </ul>
              </div>
            )}
          </div>
        ))}
        {streamMsg !== null && (
          <div className="chat-bubble bot">
            <div
              className="chat-content"
              style={{ whiteSpace: "pre-line" }}
            >
              {streamMsg}
              <TypingDots />
            </div>

          </div>
        )}
      </div>
      <form onSubmit={handleSend} className="chat-form">
        <input
          type="text"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="Ask a question..."
          className="chat-input"
          disabled={loading || streamMsg !== null}
        />
        <button
          type="submit"
          className="chat-send"
          disabled={loading || streamMsg !== null || !input.trim()}
        >
          Send
        </button>
      </form>
    </div>
  );
}

export default Chat;