import { useEffect, useMemo, useState } from "react";
import { useParams, useNavigate } from "react-router-dom";
import "../styles/DocumentDetailPage.css";
import TopBar from "../components/TopBar.jsx";
import { config } from "../utils/config";  

function DocumentDetailPage() {
  const { id } = useParams();
  const navigate = useNavigate();

  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const token = localStorage.getItem("accessToken");
    if (!token) return navigate("/");

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
  }, [id, navigate]);

  const snippets = useMemo(() => {
    const collected = [];
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
  const justification = data.justification || data.explanation || data.summary || "";
  const status = (data.state || data.status || "pending").toLowerCase();
  const uploadedAt = data.uploaded_at || data.created_at;

  return (
    <div className="detail-page">
      <TopBar title="Detalhes" />

      <main className="detail-shell">
        <header className="detail-heading">
          <h1>{data.filename}</h1>
          <span className={`status-pill status-${status}`}>
            {data.state || data.status || "Pendente"}
          </span>
        </header>

        <section className="detail-section detail-summary">
          <h2>Essencial</h2>
          <div className="summary-grid">
            <div>
              <p className="summary-label">Ficheiro</p>
              <p className="summary-value">{data.filename || "—"}</p>
            </div>
            <div>
              <p className="summary-label">Data de upload</p>
              <p className="summary-value">
                {uploadedAt ? new Date(uploadedAt).toLocaleString() : "—"}
              </p>
            </div>
            <div>
              <p className="summary-label">Páginas</p>
              <p className="summary-value">{data.page_count || data.pages || "—"}</p>
            </div>
            <div>
              <p className="summary-label">Origem</p>
              <p className="summary-value">{data.source || "—"}</p>
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
          <h2>Justificação</h2>
          <div className="just-box">
            {justification ? <p>{justification}</p> : <p>Sem justificação disponível.</p>}
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
      </main>
    </div>
  );
}

export default DocumentDetailPage;
