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

function TableView({ headers = [], rows = [] }) {
  return (
    <div className="resp-table-wrap">
      <table className="resp-table">
        {headers && headers.length > 0 && (
          <thead>
            <tr>
              {headers.map((h, i) => (
                <th key={i}>{h}</th>
              ))}
            </tr>
          </thead>
        )}
        <tbody>
          {rows && rows.map((r, i) => (
            <tr key={i}>
              {r.map((c, j) => (
                <td key={j}>{String(c)}</td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function ResponseRenderer({ data }) {
  if (!data) return null;
  if (data.type === "error") {
    const errs = (data.errors || data.content?.errors) || [];
    return (
      <div className="resp-error">
        <b>Error</b>
        <ul>{errs.map((e, i) => (<li key={i}>{e}</li>))}</ul>
      </div>
    );
  }

  const content = data.content || {};
  const {
    title, description, code_blocks = [], tables = [], lists = [], links = [], notes = [], warnings = []
  } = content;

  return (
    <div className="resp-root">
      {title ? <div className="resp-title">{title}</div> : null}
      {description ? <div className="resp-desc">{description}</div> : null}

      {tables && tables.length > 0 && (
        <div className="resp-section">
          {tables.map((t, i) => (
            <TableView key={i} headers={t.headers} rows={t.rows} />
          ))}
        </div>
      )}

      {code_blocks && code_blocks.length > 0 && (
        <div className="resp-section">
          {code_blocks.map((b, i) => (
            <CodeBlock key={i} language={b.language} code={b.code} />
          ))}
        </div>
      )}

      {lists && lists.length > 0 && (
        <div className="resp-section">
          {lists.map((lst, i) => (
            <ul key={i} className="resp-list">
              {lst.map((item, j) => (<li key={j}>{item}</li>))}
            </ul>
          ))}
        </div>
      )}

      {links && links.length > 0 && (
        <div className="resp-section resp-links">
          {links.map((u, i) => (
            <a key={i} href={u} target="_blank" rel="noreferrer">{u}</a>
          ))}
        </div>
      )}

      {(notes && notes.length > 0) || (warnings && warnings.length > 0) ? (
        <div className="resp-meta">
          {notes && notes.length > 0 && (
            <div className="resp-notes">
              <b>Notes</b>
              <ul>{notes.map((n, i) => (<li key={i}>{n}</li>))}</ul>
            </div>
          )}
          {warnings && warnings.length > 0 && (
            <div className="resp-warnings">
              <b>Warnings</b>
              <ul>{warnings.map((w, i) => (<li key={i}>{w}</li>))}</ul>
            </div>
          )}
        </div>
      ) : null}
    </div>
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
            data,
            content: data.answer || data.content?.description || "",
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