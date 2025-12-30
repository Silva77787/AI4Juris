// src/pages/HomePage.jsx
import { useEffect, useMemo, useRef, useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import '../styles/HomePage.css';
import TopBar from '../components/TopBar.jsx';
import DynamicToast from '../components/DynamicToast.jsx';
import { config } from '../utils/config';

function HomePage() {
  const [documents, setDocuments] = useState([]);
  const [loading, setLoading] = useState(true);
  const [authenticated, setAuthenticated] = useState(null);
  const [searchTerm, setSearchTerm] = useState('');
  const [sortOrder, setSortOrder] = useState('desc');
  const [stateFilter, setStateFilter] = useState('');
  const [classificationFilter, setClassificationFilter] = useState('');
  const [page, setPage] = useState(1);
  const [showUpload, setShowUpload] = useState(false);
  const [selectedFile, setSelectedFile] = useState(null);
  const [isDragging, setIsDragging] = useState(false);
  const [uploadError, setUploadError] = useState('');
  const [uploading, setUploading] = useState(false);
  const [toasts, setToasts] = useState([]);
  const fileInputRef = useRef(null);
  const navigate = useNavigate();

  const pushToast = (message, type = 'error') => {
    const id = `${Date.now()}-${Math.random()}`;
    setToasts((prev) => [...prev.slice(-4), { id, message, type }]);
    setTimeout(() => {
      setToasts((prev) => prev.filter((toast) => toast.id !== id));
    }, 5000);
  };

  const dismissToast = (id) => {
    setToasts((prev) => prev.filter((toast) => toast.id !== id));
  };

  useEffect(() => {
    const token = localStorage.getItem('accessToken');

    if (!token) {
      navigate('/');
      return;
    }

    setAuthenticated(true);

    fetch(`${config.apiUrl}/documents/`, {
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

  useEffect(() => {
    const pendingToast = localStorage.getItem('pendingToast');
    if (!pendingToast) return;

    try {
      const parsed = JSON.parse(pendingToast);
      if (parsed && parsed.message) {
        pushToast(parsed.message, parsed.type || 'success');
      }
    } catch (err) {
      console.error('Erro ao ler pendingToast:', err);
    } finally {
      localStorage.removeItem('pendingToast');
    }
  }, []);

  useEffect(() => {
    if (!showUpload) return;

    const handleKeyDown = (event) => {
      if (event.key === 'Escape') {
        setShowUpload(false);
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [showUpload]);

  const classificationOptions = useMemo(() => {
    const labels = new Set();
    documents.forEach((doc) => {
      if (Array.isArray(doc.labels)) {
        doc.labels.forEach((label) => {
          if (label) labels.add(label);
        });
      }
    });
    return Array.from(labels).sort((a, b) => a.localeCompare(b));
  }, [documents]);

  const stateFilterOptions = [
    { value: 'done', label: 'Done' },
    { value: 'error', label: 'Error' },
    { value: 'processing', label: 'Processing' },
    { value: 'queued', label: 'In queue' },
  ];

  const filteredDocs = useMemo(() => {
    const bySearch = documents.filter((doc) => {
      if (!searchTerm.trim()) return true;
      const query = searchTerm.toLowerCase();
      return (
        (doc.title && doc.title.toLowerCase().includes(query)) ||
        (doc.filename && doc.filename.toLowerCase().includes(query))
      );
    });

    const byState = bySearch.filter((doc) => {
      if (!stateFilter || stateFilter === 'all') return true;
      const statusText = (doc.state || doc.status || '').toLowerCase();
      return statusText === stateFilter;
    });

    const byClassification = byState.filter((doc) => {
      if (!classificationFilter || classificationFilter === 'all') return true;
      const hasLabels = doc.labels && doc.labels.length;
      return hasLabels && doc.labels.includes(classificationFilter);
    });

    const sorted = [...byClassification].sort((a, b) => {
      const da = a.created_at || a.uploaded_at ? new Date(a.created_at || a.uploaded_at).getTime() : 0;
      const db = b.created_at || b.uploaded_at ? new Date(b.created_at || b.uploaded_at).getTime() : 0;
      return sortOrder === 'asc' ? da - db : db - da;
    });

    return sorted;
  }, [documents, classificationFilter, searchTerm, sortOrder, stateFilter]);

  useEffect(() => {
    setPage(1);
  }, [searchTerm, sortOrder, stateFilter, classificationFilter]);

  const totalPages = Math.max(1, Math.ceil(filteredDocs.length / 6));
  const clampedPage = Math.min(page, totalPages);
  const pagedDocs = filteredDocs.slice((clampedPage - 1) * 6, clampedPage * 6);

  const handleFileSelect = (file) => {
    if (!file) return;
    if (file.type !== 'application/pdf') {
      setUploadError('Formato invalido. O ficheiro tem de ser PDF.');
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

  const handleUpload = async () => {
    if (!selectedFile || uploading) return;

    const token = localStorage.getItem('accessToken');
    if (!token) {
      pushToast('Sessao expirada. Faz login novamente.', 'error');
      return;
    }

    setUploading(true);

    try {
      const formData = new FormData();
      formData.append('file', selectedFile);
      formData.append('filename', selectedFile.name);

      const res = await fetch(`${config.apiUrl}/documents/upload/`, {
        method: 'POST',
        headers: {
          Authorization: `Bearer ${token}`,
        },
        body: formData,
      });

      const data = await res.json().catch(() => ({}));
      if (!res.ok) {
        const errorMessage = data.error || data.detail || 'Erro ao enviar documento.';
        pushToast(errorMessage, 'error');
        setUploading(false);
        return;
      }

      setDocuments((prev) => [data, ...prev]);
      setSelectedFile(null);
      setShowUpload(false);
      pushToast('Documento enviado com sucesso.', 'success');
    } catch (err) {
      console.error('Erro ao enviar documento:', err);
      pushToast('Erro ao enviar documento.', 'error');
    } finally {
      setUploading(false);
    }
  };

  if (authenticated === null) return null;

  return (
    <div className="home-page">
      <div className="home-hero-bg" />

      <TopBar title="Historico" />

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
              Date {sortOrder === 'asc' ? '▲' : '▼'}
            </button>
            <select
              className="filter-select"
              value={stateFilter}
              onChange={(event) => setStateFilter(event.target.value)}
              aria-label="Filtrar por estado"
            >
              <option value="" disabled>
                Estado
              </option>
              {stateFilterOptions.map((option) => (
                <option key={option.value} value={option.value}>
                  {option.label}
                </option>
              ))}
              <option value="all">Todos</option>
            </select>
            <select
              className="filter-select"
              value={classificationFilter}
              onChange={(event) => setClassificationFilter(event.target.value)}
              aria-label="Filtrar por classificacao"
            >
              <option value="" disabled>
                Classificacoes
              </option>
              {classificationOptions.map((label) => (
                <option key={label} value={label}>
                  {label}
                </option>
              ))}
              <option value="all">Todos</option>
            </select>
          </div>
        </header>

        <section className="cards-grid">
          {loading ? (
            <div className="placeholder-card">A carregar documentos...</div>
          ) : filteredDocs.length === 0 ? (
            <div className="placeholder-card">
              <p className="empty-headline">Ainda nao tens uploads.</p>
              <p className="empty-body">Carrega um PDF para veres o historico aqui.</p>
            </div>
          ) : (
            pagedDocs.map((doc) => {
              const uploadedAt = doc.created_at || doc.uploaded_at;
              const uploaded = uploadedAt ? new Date(uploadedAt).toLocaleString() : 'Data nao disponivel';
              const labels = doc.labels && doc.labels.length ? doc.labels : doc.classification ? [doc.classification] : [];
              const justification = doc.justification || doc.explanation || 'Sem justificacao disponivel.';
              const statusText = doc.state || doc.status || 'Pendente';
              const statusKey = statusText.toLowerCase().replace(/\s+/g, '-');

              return (
                <Link
                  key={doc.id}
                  to={`/documents/${doc.id}`}
                  className="doc-card-link"
                  style={{ textDecoration: 'none', color: 'inherit' }}
                >
                  <article className="doc-card">
                    <div className="doc-card__top">
                      <div>
                        <p className="doc-date">{uploaded}</p>
                        <h3 className="doc-title">{doc.title || doc.filename}</h3>
                        <p className="doc-file">{doc.filename}</p>
                      </div>
                      <span className={`status-pill status-${statusKey}`}>
                        {statusText}
                      </span>
                    </div>

                    <div className="doc-body">
                      <div className="doc-tags">
                        {(labels.length ? labels : ['Sem rotulos']).map((label, idx) => (
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
        {filteredDocs.length > 6 && (
          <div className="home-doc-pagination">
            <button
              type="button"
              className="ghost-btn"
              onClick={() => setPage((prev) => Math.max(1, prev - 1))}
              disabled={clampedPage === 1}
            >
              Anterior
            </button>
            <span className="meta-text">
              Pagina {clampedPage} de {totalPages}
            </span>
            <button
              type="button"
              className="ghost-btn"
              onClick={() => setPage((prev) => Math.min(totalPages, prev + 1))}
              disabled={clampedPage === totalPages}
            >
              Seguinte
            </button>
          </div>
        )}
      </main>

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
                <div className="upload-arrow">-&gt;</div>
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
                      onClick={(event) => {
                        event.stopPropagation();
                        handleUpload();
                      }}
                      disabled={uploading}
                    >
                      {uploading ? 'A enviar...' : 'Enviar para classificacao'}
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

      <DynamicToast toasts={toasts} onDismiss={dismissToast} />
    </div>
  );
}

export default HomePage;
