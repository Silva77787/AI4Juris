import { Link, useNavigate } from 'react-router-dom';
import '../styles/HomePage.css';

function TopBar({ title }) {
  const navigate = useNavigate();

  const handleLogout = () => {
    localStorage.removeItem('accessToken');
    localStorage.removeItem('refreshToken');
    navigate('/');
  };

  return (
    <header className="home-nav">
      <Link className="brand brand-link" to="/home" aria-label="Voltar ao inicio">
        <div className="logo-dot" />
        <div>
          <p className="brand-kicker">AI4Juris</p>
          <strong className="brand-title">Workspace</strong>
        </div>
      </Link>

      {title ? <div className="nav-title">{title}</div> : <div className="nav-spacer" />}

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
  );
}

export default TopBar;
