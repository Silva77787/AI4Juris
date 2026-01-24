import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { useParams, useNavigate } from "react-router-dom";
import "../styles/DocumentDetailPage.css";
import TopBar from "../components/TopBar.jsx";
import { config } from "../utils/config";  

function DocumentDetailPage() {
  const { id } = useParams();
  const navigate = useNavigate();

  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [chatSessionId, setChatSessionId] = useState(null);
  const [chatMessages, setChatMessages] = useState([]);
  const [chatInput, setChatInput] = useState("");
  const [chatBusy, setChatBusy] = useState(false);
  const [chatError, setChatError] = useState("");
  const chatInitRef = useRef(false);

  const authFetch = useCallback(
    (path, options = {}) => {
      const token = localStorage.getItem("accessToken");
      if (!token) {
        navigate("/");
        return Promise.reject(new Error("Missing token"));
      }

      const headers = {
        Authorization: `Bearer ${token}`,
        ...(options.headers || {}),
      };
      if (!headers["Content-Type"] && options.body) {
        headers["Content-Type"] = "application/json";
      }

      return fetch(`${config.apiUrl}${path}`, {
        ...options,
        headers,
      });
    },
    [navigate]
  );

  const fetchDocument = useCallback(
    (options = {}) => {
      const token = localStorage.getItem("accessToken");
      if (!token) return navigate("/");

      if (!options.silent) {
        setLoading(true);
      }

      fetch(`${config.apiUrl}/documents/${id}/`, {
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`
        }
      })
        .then((res) => {
          if (!res.ok) throw new Error("Erro a carregar");
          return res.json();
        })
        .then((doc) => {
          setData(doc);
          setLoading(false);
        })
        .catch((err) => {
          console.error(err);
          setLoading(false);
        });
    },
    [id, navigate]
  );

  useEffect(() => {
    fetchDocument();
  }, [fetchDocument]);

  useEffect(() => {
    const status = (data?.state || data?.status || "").toLowerCase();
    const isPending = status === "queued" || status === "processing";
    if (!isPending) return;

    const interval = setInterval(() => {
      fetchDocument({ silent: true });
    }, 4000);

    return () => clearInterval(interval);
  }, [data, fetchDocument]);

  useEffect(() => {
    const status = (data?.state || data?.status || "").toLowerCase();
    if (status !== "done") return;
    if (chatSessionId || chatInitRef.current) return;

    chatInitRef.current = true;
    setChatBusy(true);
    setChatError("");

    authFetch(`/documents/${id}/chat/create/`, { method: "POST" })
      .then((res) => {
        if (!res.ok) throw new Error("Falha a iniciar chat.");
        return res.json();
      })
      .then((payload) => {
        if (payload?.session_id) {
          setChatSessionId(payload.session_id);
          setChatMessages([
            {
              role: "assistant",
              text: "Chat iniciado. Podes colocar perguntas sobre o documento.",
            },
          ]);
        } else {
          throw new Error("Session id em falta.");
        }
      })
      .catch((err) => {
        setChatError(err.message || "Falha a iniciar chat.");
        chatInitRef.current = false;
      })
      .finally(() => {
        setChatBusy(false);
      });
  }, [authFetch, chatSessionId, data, id]);

  useEffect(() => {
    if (!chatSessionId) return;

    const handlePageHide = () => {
      authFetch(`/documents/${id}/chat/close/`, {
        method: "POST",
        body: JSON.stringify({ session_id: chatSessionId }),
        keepalive: true,
      }).catch(() => {});
    };

    window.addEventListener("pagehide", handlePageHide);

    return () => {
      window.removeEventListener("pagehide", handlePageHide);
    };
  }, [authFetch, chatSessionId, id]);


  const snippets = useMemo(() => {
    const collected = [];
    if (data?.justification) {
      collected.push(data.justification);
    }
    const predictions = Array.isArray(data?.predictions) ? data.predictions : [];
    predictions.forEach((prediction) => {
      const explanations = Array.isArray(prediction.explanations)
        ? prediction.explanations
        : [];
      explanations.forEach((ex) => {
        if (ex.text_span) collected.push(ex.text_span);
      });
    });
    return [...new Set(collected)].slice(0, 3);
  }, [data]);

  if (loading) return <div className="loading">A carregar…</div>;
  if (!data) return <div className="error">Documento não encontrado.</div>;

  const labels = (() => {
    if (Array.isArray(data.labels) && data.labels.length) return data.labels;
    if (data.classification) return [data.classification];
    if (Array.isArray(data.predictions) && data.predictions.length) {
      const descriptors = data.predictions
        .map((prediction) => prediction.descriptor)
        .filter(Boolean);
      if (descriptors.length) return descriptors;
    }
    return [];
  })();
  const status = (data.state || data.status || "pending").toLowerCase();
  const uploadedAt = data.uploaded_at || data.created_at;
  const chatDisabled = status !== "done" || !chatSessionId || chatBusy;

  return (
    <div className="detail-page">
      <TopBar title="Detalhes" />

      <main className="detail-shell">
        <div className="detail-layout">
          <div className="detail-main">
        <header className="detail-heading">
          <button type="button" className="back-btn" onClick={() => navigate(-1)} aria-label="Voltar" />
          <div className="detail-title">
            <h1>{data.filename}</h1>
            {data.group_id && data.uploaded_by && (
              <span className="detail-sub">Enviado por {data.uploaded_by}</span>
            )}
          </div>
          <div className="detail-heading-actions">
            {data.file_url && (
              <a className="detail-open-link" href={data.file_url} target="_blank" rel="noreferrer">
                Abrir PDF
              </a>
            )}
            <span className={`status-pill status-${status}`}>
              {data.state || data.status || "Pendente"}
            </span>
          </div>
        </header>

        {data.file_url && (
          <section className="detail-section">
            <h2>Previsualizacao do documento</h2>
            <div className="detail-pdf-preview">
              <iframe title="Preview PDF" src={data.file_url} />
            </div>
          </section>
        )}

        <section className="detail-section detail-summary">
          <h2>Essencial</h2>
          <div className="summary-grid">
            <div className="summary-item">
              <p className="summary-label">Ficheiro</p>
              <p className="summary-value">{data.filename || "—"}</p>
            </div>
            <div className="summary-item">
              <p className="summary-label">Data de upload</p>
              <p className="summary-value">
                {uploadedAt ? new Date(uploadedAt).toLocaleString() : "—"}
              </p>
            </div>
            <div className="summary-item">
              <p className="summary-label">Páginas</p>
              <p className="summary-value">{data.page_count || data.pages || "—"}</p>
            </div>
          </div>
        </section>

        <section className="detail-section">
          <h2>Classificação</h2>
          <div className="tags-row">
            {(labels.length ? labels : ["Sem rótulos"]).map((label, idx) => (
              <span key={`${label}-${idx}`} className="tag-chip">
                {label}
              </span>
            ))}
          </div>
        </section>

        <section className="detail-section">
          <h2>Trechos relevantes</h2>
          {snippets.length ? (
            <div className="snippet-list">
              {snippets.map((snippet, idx) => (
                <div key={`snippet-${idx}`} className="snippet-card">
                  {snippet}
                </div>
              ))}
            </div>
          ) : (
            <p>Sem trechos relevantes disponíveis.</p>
          )}
        </section>
          </div>

          <aside className="detail-chat">
            <div className="chat-header">
              <h2>Chat do documento</h2>
              <span className={`status-pill status-${status}`}>
                {data.state || data.status || "Pendente"}
              </span>
            </div>
            <div className="chat-body">
              {chatError && <div className="chat-error">{chatError}</div>}
              {!chatError && !chatMessages.length && (
                <div className="chat-empty">
                  {status === "done"
                    ? "A iniciar chat..."
                    : "Aguardar classificacao para iniciar o chat."}
                </div>
              )}
              {chatMessages.map((msg, idx) => (
                <div key={`msg-${idx}`} className={`chat-bubble chat-${msg.role}`}>
                  {msg.text}
                </div>
              ))}
            </div>
            <form
              className="chat-input-row"
              onSubmit={(event) => {
                event.preventDefault();
                if (chatDisabled || !chatInput.trim()) return;

                const content = chatInput.trim();
                setChatInput("");
                setChatBusy(true);
                setChatMessages((prev) => [...prev, { role: "user", text: content }]);

                authFetch(`/documents/${id}/chat/message/`, {
                  method: "POST",
                  body: JSON.stringify({
                    session_id: chatSessionId,
                    message: content,
                  }),
                })
                  .then((res) => {
                    if (!res.ok) throw new Error("Erro a enviar mensagem.");
                    return res.json();
                  })
                  .then((payload) => {
                    const rawReply = payload?.response;
                    const reply =
                      typeof rawReply === "string"
                        ? rawReply
                        : rawReply != null
                          ? JSON.stringify(rawReply)
                          : "Sem resposta.";
                    setChatMessages((prev) => [...prev, { role: "assistant", text: reply }]);
                  })
                  .catch((err) => {
                    setChatError(err.message || "Erro a enviar mensagem.");
                  })
                  .finally(() => {
                    setChatBusy(false);
                  });
              }}
            >
              <input
                type="text"
                value={chatInput}
                onChange={(event) => setChatInput(event.target.value)}
                placeholder="Escreve a tua pergunta..."
                disabled={chatDisabled}
              />
              <button type="submit" disabled={chatDisabled}>
                {chatBusy ? "..." : "Enviar"}
              </button>
            </form>
          </aside>
        </div>
      </main>
    </div>
  );
}

export default DocumentDetailPage;
