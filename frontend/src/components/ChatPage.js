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
  
  // Helper function to parse JSON strings that might be embedded in descriptions
  const parseEmbeddedJson = (text) => {
    if (typeof text === 'string' && text.trim().startsWith('{') && text.trim().endsWith('}')) {
      try {
        // Replace single quotes with double quotes for valid JSON
        const cleanedText = text.replace(/'/g, '"').replace(/\n/g, '\\n');
        return JSON.parse(cleanedText);
      } catch (e) {
        console.log('Failed to parse embedded JSON:', e);
        return null;
      }
    }
    return null;
  };

  // Helper function to clean up text formatting
  const cleanText = (text) => {
    if (typeof text !== 'string') return text;
    return text
      .replace(/\\n/g, '\n')
      .replace(/\\'/g, "'")
      .replace(/\\"/g, '"')
      .trim();
  };

  // Extract data from the new response structure
  let short_answers = data.short_answers || [];
  let descriptions = data.descriptions || [];
  let url = data.url || [];
  let curl = data.curl || [];
  let values = data.values || {};
  let numbers = data.numbers || {};

  // Check if descriptions contain embedded JSON (malformed responses)
  if (descriptions.length > 0 && typeof descriptions[0] === 'string') {
    const embeddedJson = parseEmbeddedJson(descriptions[0]);
    if (embeddedJson) {
      // Use the embedded JSON data instead
      short_answers = embeddedJson.short_answers || short_answers;
      descriptions = embeddedJson.descriptions || descriptions;
      url = embeddedJson.url || url;
      curl = embeddedJson.curl || curl;
      values = embeddedJson.values || values;
      numbers = embeddedJson.numbers || numbers;
    }
  }

  return (
    <div className="resp-root">
      {/* Short Answers */}
      {short_answers && short_answers.length > 0 && (
        <div className="resp-section">
          <h3 className="resp-section-title">Quick Answers</h3>
          <div className="resp-short-answers">
            {short_answers.map((answer, i) => (
              <div key={i} className="resp-short-answer">{cleanText(answer)}</div>
            ))}
          </div>
        </div>
      )}

      {/* Descriptions */}
      {descriptions && descriptions.length > 0 && (
        <div className="resp-section">
          <h3 className="resp-section-title">Detailed Information</h3>
          <div className="resp-descriptions">
            {descriptions.map((desc, i) => (
              <div key={i} className="resp-description">{cleanText(desc)}</div>
            ))}
          </div>
        </div>
      )}

      {/* URLs */}
      {url && url.length > 0 && (
        <div className="resp-section">
          <h3 className="resp-section-title">Related URLs</h3>
          <div className="resp-urls">
            {url.map((link, i) => (
              <a key={i} href={link} target="_blank" rel="noopener noreferrer" className="resp-url">
                {link}
              </a>
            ))}
          </div>
        </div>
      )}

      {/* cURL Commands */}
      {curl && curl.length > 0 && (
        <div className="resp-section">
          <h3 className="resp-section-title">cURL Commands</h3>
          <div className="resp-curl-commands">
            {curl.map((command, i) => (
              <CodeBlock key={i} language="bash" code={cleanText(command)} />
            ))}
          </div>
        </div>
      )}

      {/* Values */}
      {values && Object.keys(values).length > 0 && (
        <div className="resp-section">
          <h3 className="resp-section-title">Key Values</h3>
          <div className="resp-values">
            {Object.entries(values).map(([key, value]) => (
              <div key={key} className="resp-value-item">
                <span className="resp-value-key">{key}:</span>
                <span className="resp-value-value">{value}</span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Numbers */}
      {numbers && Object.keys(numbers).length > 0 && (
        <div className="resp-section">
          <h3 className="resp-section-title">Statistics</h3>
          <div className="resp-numbers">
            {Object.entries(numbers).map(([key, value]) => (
              <div key={key} className="resp-number-item">
                <span className="resp-number-key">{key}:</span>
                <span className="resp-number-value">{value}</span>
              </div>
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

  const [useStreaming, setUseStreaming] = useState(false);


  const handleStream = (question) => {
    setStreamMsg("");
    setLoading(true);
    const userMessage = { role: "user", content: question };
    setHistory((h) => [...h, userMessage]);

    if (useStreaming) {
      // Use streaming endpoint
      handleStreamingQuestion(question);
    } else {
      // Use regular endpoint
      handleRegularQuestion(question);
    }
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
                  short_answers: [],
                  descriptions: [streamedResponse],
                  url: [],
                  curl: [],
                  values: {},
                  numbers: {}
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
                        short_answers: [],
                        descriptions: [streamedResponse],
                        url: [],
                        curl: [],
                        values: {},
                        numbers: {}
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
            short_answers: [],
            descriptions: ["Error in streaming response."],
            url: [],
            curl: [],
            values: { error: "streaming_error" },
            numbers: {}
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
            content: data.descriptions?.[0] || data.short_answers?.[0] || "Response received",
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
              short_answers: [],
              descriptions: ["Error contacting backend."],
              url: [],
              curl: [],
              values: { error: "backend_error" },
              numbers: {}
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
      
      {/* Streaming Toggle */}
      <div className="chat-controls">
        <label className="streaming-toggle">
          <input
            type="checkbox"
            checked={useStreaming}
            onChange={(e) => setUseStreaming(e.target.checked)}
          />
          <span>Use Streaming</span>
        </label>
      </div>
      
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