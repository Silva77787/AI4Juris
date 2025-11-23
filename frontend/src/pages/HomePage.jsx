// src/pages/HomePage.jsx
import { useEffect, useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import '../styles/HomePage.css';

function HomePage() {
  const [documents, setDocuments] = useState([]);
  const [loading, setLoading] = useState(true);
  const [authenticated, setAuthenticated] = useState(null); // null = ainda a verificar
  const navigate = useNavigate();

  useEffect(() => {
    const token = localStorage.getItem('accessToken');

    if (!token) {
      navigate('/');
      return;
    }

    setAuthenticated(true);

    fetch('http://localhost:7777/documents/', {
      headers: {
        'Content-Type': 'application/json',
        Authorization: `Bearer ${token}`,
      },
    })
      .then((res) => {
        if (!res.ok) {
          if (res.status === 401) {
            localStorage.removeItem('accessToken');
            localStorage.removeItem('refreshToken');
            navigate('/');
          }
          throw new Error('Erro ao buscar documentos');
        }
        return res.json();
      })
      .then((data) => {
        setDocuments(data);
        setLoading(false);
      })
      .catch((err) => {
        console.error('Erro ao carregar documentos:', err);
        setLoading(false);
      });
  }, [navigate]);

  const handleLogout = () => {
    localStorage.removeItem('accessToken');
    localStorage.removeItem('refreshToken');
    navigate('/');
  };

  // Enquanto não sabemos se o utilizador está autenticado, não renderizamos nada
  if (authenticated === null) return null;

  return (
    <div className="home-page">
      <div className="home-hero-bg" />

      <header className="home-nav">
        <Link className="brand brand-link" to="/home" aria-label="Voltar ao início">
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

      <main className="home-shell">
        <header className="home-heading">
          <div>
            <p className="eyebrow">Histórico</p>
            <h1>Os teus uploads recentes</h1>
            <p className="subhead">
              Consulta PDFs enviados, estado de processamento e rótulos atribuídos. Etiquetas e justificações
              aparecem quando o modelo devolver resultados.
            </p>
          </div>
        </header>

        <section className="cards-grid">
          {loading ? (
            <div className="placeholder-card">A carregar documentos...</div>
          ) : documents.length === 0 ? (
            <div className="placeholder-card">
              <p className="empty-headline">Ainda não tens uploads.</p>
              <p className="empty-body">Carrega um PDF para veres o histórico aqui.</p>
            </div>
          ) : (
            documents.map((doc) => {
              const uploaded =
                doc.uploaded_at ? new Date(doc.uploaded_at).toLocaleString() : 'Data não disponível';
              const labels = doc.labels && doc.labels.length ? doc.labels : doc.classification ? [doc.classification] : [];
              const justification = doc.justification || doc.explanation || 'Sem justificação disponível.';

              return (
                <Link
                  key={doc.id}
                  to={`/documents/${doc.id}`}
                  className="doc-card-link"
                  style={{ textDecoration: "none", color: "inherit" }}
                >
                <article className="doc-card">
                  <div className="doc-card__top">
                    <div>
                      <p className="doc-date">{uploaded}</p>
                      <h3 className="doc-title">{doc.title || doc.filename}</h3>
                      <p className="doc-file">{doc.filename}</p>
                    </div>
                    <span className={`status-pill status-${(doc.status || 'pending').toLowerCase()}`}>
                      {doc.status || 'Pendente'}
                    </span>
                  </div>

                  {/* Labels e justificação que vêm do modelo */}
                  <div className="doc-body">
                    <div className="doc-tags">
                      {(labels.length ? labels : ['Sem rótulos']).map((label, idx) => (
                        <span key={idx} className="tag-chip">
                          {label}
                        </span>
                      ))}
                    </div>
                    <p className="doc-just">{justification}</p>
                  </div>
                </article>
                </Link>
              );
            })
          )}
        </section>
      </main>

      {/* Botão flutuante de upload */}
      <Link to="/upload" className="fab-upload" aria-label="Upload de PDF">
        <span className="fab-plus">+</span>
        <span className="fab-label">Upload PDF</span>
      </Link>
    </div>
  );
}

export default HomePage;
