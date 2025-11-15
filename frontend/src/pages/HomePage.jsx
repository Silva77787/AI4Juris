// src/pages/HomePage.jsx
import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';

function HomePage() {
  const [documents, setDocuments] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetch('http://localhost:8000/api/documents/')
      .then((res) => res.json())
      .then((data) => {
        setDocuments(data);
        setLoading(false);
      })
      .catch((err) => {
        console.error('Erro ao carregar documentos:', err);
        setLoading(false);
      });
  }, []);

  return (
    <section>
      <h2>Histórico de Documentos</h2>

      {/* Pesquisa / Filtros (placeholder para futuro) */}
      <p style={{ color: '#666' }}>Aqui vais listar os PDFs enviados, com pesquisa, filtros e paginação.</p>

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
