import { useEffect, useState } from "react";
import { useParams, Link, useNavigate } from "react-router-dom";
import "../styles/DocumentDetailPage.css";

function DocumentDetailPage() {
  const { id } = useParams();
  const navigate = useNavigate();

  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const token = localStorage.getItem("accessToken");
    if (!token) return navigate("/");

    fetch(`http://localhost:7777/documents/${id}/`, {
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

  const handleLogout = () => {
    localStorage.removeItem('accessToken');
    localStorage.removeItem('refreshToken');
    navigate('/');
  };

  if (loading) return <div className="loading">A carregar…</div>;
  if (!data) return <div className="error">Documento não encontrado.</div>;

  return (
    
    

    <div className="detail-page">
      <header className="home-nav">
        <Link className="brand brand-link" to="/home">
          <div className="logo-dot" />
          <div>
            <p className="brand-kicker">AI4Juris</p>
            <strong className="brand-title">Workspace</strong>
          </div>
        </Link>
        <nav className="nav-actions">
          <Link className="nav-btn ghost" to="/groups">
            Chat de Grupos
          </Link>
          <Link className="nav-btn ghost" to="/profile">
            Perfil
          </Link>
          <button className="nav-btn" onClick={handleLogout}>
            Logout
          </button>
        </nav>
      </header>

      <main className="detail-shell">
        <header className="detail-heading">
          <h1>{data.filename}</h1>
          <span className={`status-pill status-${data.state.toLowerCase()}`}>
            {data.state}
          </span>
        </header>

        <section className="detail-section">
          <h2>Texto extraído</h2>
          <p className="doc-text">{data.text || "Sem texto extraído."}</p>
        </section>

        <section className="detail-section">
          <h2>Predições do Modelo</h2>
          {data.predictions.length === 0 ? (
            <p>Nenhuma predição disponível.</p>
          ) : (
            data.predictions.map((p) => (
              <div key={p.id} className="prediction-card">
                <h3>{p.descriptor}</h3>
                <p className="score">Score: {p.score.toFixed(3)}</p>

                {p.explanations.map((ex) => (
                  <div key={ex.id} className="explanation-box">
                    <p><strong>Trecho:</strong> {ex.text_span}</p>
                    <p>Score: {ex.score.toFixed(3)}</p>
                  </div>
                ))}
              </div>
            ))
          )}
        </section>

        <section className="detail-section">
          <h2>Métricas</h2>
          {data.metrics.map((m) => (
            <div key={m.id} className="metric-row">
              <p>{m.stage}</p>
              <p>{m.duration_ms} ms</p>
              <p>{new Date(m.created_at).toLocaleString()}</p>
            </div>
          ))}
        </section>
      </main>
    </div>
  );
}

export default DocumentDetailPage;
