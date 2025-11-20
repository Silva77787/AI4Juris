// src/pages/HomePage.jsx
import { useEffect, useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';

function HomePage() {
  const [documents, setDocuments] = useState([]);
  const [loading, setLoading] = useState(true);
  const [authenticated, setAuthenticated] = useState(null); // null = ainda a verificar
  const navigate = useNavigate();

  useEffect(() => {
    const token = localStorage.getItem('accessToken');

    if (!token) {
      // Se não tiver token, redireciona para login
      navigate('/');
      return;
    }

    // Token existe, considera autenticado (até prova em contrário)
    setAuthenticated(true);

    fetch('http://localhost:7777/documents/', {
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${token}`, // JWT header
      },
    })
      .then((res) => {
        if (!res.ok) {
          if (res.status === 401) {
            // Token expirado ou inválido
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

  // Enquanto não sabemos se o usuário está autenticado, não renderizamos nada
  if (authenticated === null) return null;

  return (
    <section>
      <h2>Histórico de Documentos</h2>

      <button onClick={handleLogout} style={{ marginBottom: '1rem' }}>
        Logout
      </button>

      {/* Botão de upload */}
      <div style={{ marginTop: '1.5rem' }}>
        <Link to="/upload" className="btn-primary">
          Upload de novo PDF
        </Link>
      </div>

      {/* Conteúdo */}
      <div style={{ marginTop: '2rem' }}>
        {loading ? (
          <p>A carregar documentos...</p>
        ) : documents.length === 0 ? (
          <p>Sem documentos enviados ainda.</p>
        ) : (
          <ul>
            {documents.map((doc) => (
              <li key={doc.id} style={{ marginBottom: '1rem' }}>
                <strong>{doc.title}</strong>
                <br />
                <small>
                  Ficheiro: {doc.filename} <br />
                  Estado: {doc.status} <br />
                  Enviado em: {new Date(doc.uploaded_at).toLocaleString()}
                </small>
              </li>
            ))}
          </ul>
        )}
      </div>
    </section>
  );
}

export default HomePage;
