import { useEffect, useMemo, useState } from "react";
import { chat, getHealth, getLogs } from "./api";

function riskTier(risk) {
  if (risk == null) return "unknown";
  if (risk >= 0.85) return "high";
  if (risk >= 0.7) return "med";
  return "low";
}

export default function App() {
  const [prompt, setPrompt] = useState("");
  const [chatResult, setChatResult] = useState(null);
  const [logs, setLogs] = useState([]);
  const [health, setHealth] = useState(null);
  const [loading, setLoading] = useState(false);
  const [err, setErr] = useState("");

  async function refresh() {
    try {
      const [h, l] = await Promise.all([getHealth(), getLogs()]);
      setHealth(h);
      setLogs(l.reverse());
    } catch (e) {
      setErr(e.message);
    }
  }

  useEffect(() => {
    refresh();
    const t = setInterval(refresh, 4000);
    return () => clearInterval(t);
  }, []);

  async function onSubmit(e) {
    e.preventDefault();
    setErr("");
    setChatResult(null);
    setLoading(true);
    try {
      const data = await chat(prompt);
      setChatResult(data);
      setPrompt("");
      await refresh();
    } catch (e) {
      setErr(e.message);
      await refresh();
    } finally {
      setLoading(false);
    }
  }

  const chatTier = useMemo(
    () => riskTier(chatResult?.risk),
    [chatResult?.risk],
  );

  return (
    <div className="page">
      <header className="topbar">
        <div>
          <h1 className="title">LLM LeakGuard Enterprise</h1>
          <p className="subtitle">
            Phase-0 Dashboard: prompt → risk score → logs (yes, we’re basically
            building Batman for data leaks)
          </p>
        </div>

        <div className="rightActions">
          <div className={`pill ${health ? "pill-ok" : "pill-warn"}`}>
            <span className="dot" />
            {health ? "Backend: Healthy" : "Backend: Connecting…"}
          </div>
          <button className="btn btn-ghost" onClick={refresh}>
            Refresh
          </button>
        </div>
      </header>

      <main className="grid">
        {/* Prompt Card */}
        <section className="card">
          <div className="cardHeader">
            <h2>Test Prompt</h2>
            <div className="muted">POST /chat</div>
          </div>

          <form onSubmit={onSubmit} className="stack">
            <textarea
              className="textarea"
              value={prompt}
              onChange={(e) => setPrompt(e.target.value)}
              placeholder='Try: "paypal login click here" or "OTP = 252584"'
              rows={6}
            />

            <div className="row">
              <button className="btn" disabled={loading || !prompt.trim()}>
                {loading ? "Scanning…" : "Send"}
              </button>
              <button
                type="button"
                className="btn btn-ghost"
                onClick={() => setPrompt("")}
              >
                Clear
              </button>
            </div>
          </form>

          {err && (
            <div className="alert alert-bad">
              <b>Blocked / Error:</b> {err}
            </div>
          )}

          {chatResult && (
            <div className={`result result-${chatTier}`}>
              <div className="resultTop">
                <div className="resultTitle">Result</div>
                <div className={`badge badge-${chatTier}`}>
                  Risk {chatResult.risk ?? "?"}
                </div>
              </div>

              <div className="kv">
                <div>
                  <span className="k">Response</span>
                  <span className="v">{chatResult.response}</span>
                </div>
                <div>
                  <span className="k">Threats</span>
                  <span className="v">
                    {chatResult.threats?.length
                      ? chatResult.threats.join(", ")
                      : "None"}
                  </span>
                </div>
                <div>
                  <span className="k">IP</span>
                  <span className="v">{chatResult.geo?.ip ?? "?"}</span>
                </div>
              </div>
            </div>
          )}
        </section>

        {/* Health Card */}
        <section className="card">
          <div className="cardHeader">
            <h2>Backend Status</h2>
            <div className="muted">GET /health</div>
          </div>

          {health ? (
            <div className="stack">
              <div className="kv">
                <div>
                  <span className="k">Status</span>
                  <span className="v">{health.status}</span>
                </div>
                <div>
                  <span className="k">Block Threshold</span>
                  <span className="v">{health.block_threshold}</span>
                </div>
              </div>

              <div>
                <div className="label">Security Context</div>
                <pre className="code">
                  {JSON.stringify(health.security, null, 2)}
                </pre>
              </div>
            </div>
          ) : (
            <div className="muted">Loading…</div>
          )}
        </section>

        {/* Logs */}
        <section className="card cardWide">
          <div className="cardHeader">
            <h2>Recent Logs</h2>
            <div className="muted">GET /logs</div>
          </div>

          {logs.length === 0 ? (
            <div className="muted">No logs yet. Go trigger something 😈</div>
          ) : (
            <div className="logList">
              {logs.map((l, idx) => {
                const tier = riskTier(l.risk);
                const action = (l.action || "UNKNOWN").toUpperCase();
                return (
                  <div key={idx} className="logItem">
                    <div className="logTop">
                      <div className="logLeft">
                        <span
                          className={`chip chip-${action === "BLOCKED" ? "bad" : "ok"}`}
                        >
                          {action}
                        </span>
                        <span className={`badge badge-${tier}`}>
                          Risk {l.risk ?? "?"}
                        </span>
                        <span className="muted">IP: {l.ip ?? "?"}</span>
                        {l.threats?.length ? (
                          <span className="muted">
                            • Threats: {l.threats.join(", ")}
                          </span>
                        ) : null}
                      </div>
                      <div className="muted">{l.timestamp}</div>
                    </div>

                    <div className="logPrompt">{l.prompt_preview}</div>
                  </div>
                );
              })}
            </div>
          )}
        </section>
      </main>

      <footer className="footer">
        <span className="muted">
          LeakGuard • Phase-0 UI • Your logs are safe. Your secrets are not. 😈
        </span>
      </footer>
    </div>
  );
}
