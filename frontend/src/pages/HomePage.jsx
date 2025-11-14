// src/pages/HomePage.jsx
import { Link } from 'react-router-dom';

function HomePage() {
  return (
    <section>
      <h2>Histórico de Documentos</h2>

      {/* Aqui mais tarde: pesquisa, filtros, paginação */}
      <p>Aqui vais listar os PDFs enviados, com pesquisa, filtros e paginação.</p>

      <div style={{ marginTop: '1.5rem' }}>
        <Link to="/upload" className="btn-primary">
          Upload de novo PDF
        </Link>
      </div>
    </section>
  );
}

export default HomePage;
