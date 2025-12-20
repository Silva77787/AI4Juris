// src/pages/HomePage.jsx
import { useEffect, useMemo, useRef, useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import '../styles/HomePage.css';
import TopBar from '../components/TopBar.jsx';

function HomePage() {
  const [documents, setDocuments] = useState([]);
  const [loading, setLoading] = useState(true);
  const [authenticated, setAuthenticated] = useState(null); // null = ainda a verificar
  const [searchTerm, setSearchTerm] = useState('');
  const [sortOrder, setSortOrder] = useState('desc'); // asc | desc
  const [labelFilter, setLabelFilter] = useState('all'); // all | with | none
  const [showUpload, setShowUpload] = useState(false);
  const [selectedFile, setSelectedFile] = useState(null);
  const [isDragging, setIsDragging] = useState(false);
  const [uploadError, setUploadError] = useState('');
  const fileInputRef = useRef(null);
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

  const filteredDocs = useMemo(() => {
    const bySearch = documents.filter((doc) => {
      if (!searchTerm.trim()) return true;
      const query = searchTerm.toLowerCase();
      return (
        (doc.title && doc.title.toLowerCase().includes(query)) ||
        (doc.filename && doc.filename.toLowerCase().includes(query))
      );
    });

    const byLabels = bySearch.filter((doc) => {
      const hasLabels = doc.labels && doc.labels.length;
      if (labelFilter === 'with') return hasLabels;
      if (labelFilter === 'none') return !hasLabels;
      return true;
    });

    const sorted = [...byLabels].sort((a, b) => {
      const da = a.uploaded_at ? new Date(a.uploaded_at).getTime() : 0;
      const db = b.uploaded_at ? new Date(b.uploaded_at).getTime() : 0;
      return sortOrder === 'asc' ? da - db : db - da;
    });

    return sorted;
  }, [documents, labelFilter, searchTerm, sortOrder]);

  const handleFileSelect = (file) => {
    if (!file) return;
    if (file.type !== 'application/pdf') {
      setUploadError('Formato inválido. O ficheiro tem de ser PDF.');
      setSelectedFile(null);
      return;
    }
    setUploadError('');
    setSelectedFile(file);
  };

  const handleFileChange = (event) => {
    const file = event.target.files && event.target.files[0];
    handleFileSelect(file);
  };

  const handleDrop = (event) => {
    event.preventDefault();
    setIsDragging(false);
    const file = event.dataTransfer.files && event.dataTransfer.files[0];
    handleFileSelect(file);
  };

  const handleDragOver = (event) => {
    event.preventDefault();
  };

  const handleDragEnter = (event) => {
    event.preventDefault();
    setIsDragging(true);
  };

  const handleDragLeave = (event) => {
    event.preventDefault();
    if (event.currentTarget === event.target) {
      setIsDragging(false);
    }
  };

  // Enquanto não sabemos se o utilizador está autenticado, não renderizamos nada
  if (authenticated === null) return null;

  return (
    <div className="home-page">
      <div className="home-hero-bg" />

      <TopBar title="Histórico" />

      <main className="home-shell">
        <header className="home-heading">
          <div>
            <h1>Os teus uploads recentes</h1>
          </div>
          <div className="filters-row">
            <div className="search-field">
              <input
                type="text"
                placeholder="Search by name"
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                aria-label="Pesquisar por nome"
              />
              <button
                className="search-icon-btn"
                type="button"
                aria-label="Pesquisar"
                onClick={() => {}}
              />
            </div>
            <button
              className="pill-btn"
              type="button"
              onClick={() => setSortOrder((prev) => (prev === 'asc' ? 'desc' : 'asc'))}
            >
              Date {sortOrder === 'asc' ? '↑' : '↓'}
            </button>
            <button
              className="pill-btn"
              type="button"
              onClick={() =>
                setLabelFilter((prev) => (prev === 'all' ? 'with' : prev === 'with' ? 'none' : 'all'))
              }
            >
              {labelFilter === 'all' && 'Rótulos'}
              {labelFilter === 'with' && 'Com rótulos'}
              {labelFilter === 'none' && 'Sem rótulos'}
            </button>
          </div>
        </header>

        <section className="cards-grid">
          {loading ? (
            <div className="placeholder-card">A carregar documentos...</div>
          ) : filteredDocs.length === 0 ? (
            <div className="placeholder-card">
              <p className="empty-headline">Ainda não tens uploads.</p>
              <p className="empty-body">Carrega um PDF para veres o histórico aqui.</p>
            </div>
          ) : (
            filteredDocs.map((doc) => {
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
      <button
        type="button"
        className="fab-upload"
        aria-label="Upload de PDF"
        onClick={() => setShowUpload(true)}
      >
        <span className="fab-plus">+</span>
        <span className="fab-label">Upload PDF</span>
      </button>

      {showUpload && (
        <div className="upload-backdrop" role="presentation" onClick={() => setShowUpload(false)}>
          <div
            className="upload-modal"
            role="dialog"
            aria-modal="true"
            onClick={(event) => event.stopPropagation()}
          >
            {uploadError && <div className="upload-error">{uploadError}</div>}
            <div
              className={`upload-dropzone${isDragging ? ' is-dragging' : ''}`}
              onClick={() => fileInputRef.current && fileInputRef.current.click()}
              onDrop={handleDrop}
              onDragOver={handleDragOver}
              onDragEnter={handleDragEnter}
              onDragLeave={handleDragLeave}
            >
              <div className="upload-icon" aria-hidden="true">
                <span>PDF</span>
                <div className="upload-arrow">↑</div>
              </div>
              {selectedFile ? (
                <>
                  <p className="upload-title">Ficheiro pronto para enviar</p>
                  <p className="upload-sub">Vamos analisar e classificar o documento.</p>
                  <p className="upload-file">{selectedFile.name}</p>
                  <div className="upload-actions">
                    <button
                      type="button"
                      className="upload-send"
                      onClick={(event) => event.stopPropagation()}
                    >
                      Enviar para classificação
                    </button>
                  </div>
                </>
              ) : (
                <>
                  <p className="upload-title">Arraste e solte o ficheiro aqui</p>
                  <p className="upload-sub">ou clique para selecionar o seu ficheiro</p>
                </>
              )}
              <input
                ref={fileInputRef}
                type="file"
                accept="application/pdf"
                onChange={handleFileChange}
                hidden
              />
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

export default HomePage;
