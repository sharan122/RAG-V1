import React, { useState, useRef } from "react";
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

function Chat() {
  const [input, setInput] = useState("");
  const [history, setHistory] = useState([]);
  const [loading, setLoading] = useState(false);
  const [streamMsg, setStreamMsg] = useState(null);
  const [streamSources, setStreamSources] = useState([]);
  const eventSourceRef = useRef(null);

  const handleStream = (question) => {
    setStreamMsg("");
    setStreamSources([]);
    setLoading(true);
    const userMessage = { role: "user", content: question };
    setHistory((h) => [...h, userMessage]);

    fetch("http://localhost:8000/ask", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ question, session_id: "default" }),
    })
      .then((res) => res.json())
      .then((data) => {
        setHistory((h) => [
          ...h,
          {
            role: "bot",
            content:
              data.answer ||
              (data.content && data.content.description) ||
              "No answer.",
            sources: data.sources || [],
          },
        ]);
        setStreamMsg(null);
        setStreamSources([]);
        setLoading(false);
      })
      .catch(() => {
        setHistory((h) => [
          ...h,
          { role: "bot", content: "Error contacting backend." },
        ]);
        setStreamMsg(null);
        setStreamSources([]);
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
            <div
              className="chat-content"
              style={{ whiteSpace: "pre-line" }}
            >
              {msg.content}
            </div>
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
            {streamSources && streamSources.length > 0 && (
              <div className="chat-sources">
                <b>Sources:</b>
                <ul>
                  {streamSources.map((src, j) => (
                    <li key={j}>
                      {src.title} — {src.source}
                    </li>
                  ))}
                </ul>
              </div>
            )}
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