// src/components/Layout.jsx
import { Link } from 'react-router-dom';

function Layout({ children }) {
  return (
    <div className="layout">
      <header className="layout-header">
        <h1>AI4Juris</h1>
        <nav className="layout-nav">
          <Link to="/">Home</Link>
          <Link to="/groups">Grupos</Link>
          <Link to="/admin">Admin</Link>
          <Link to="/login">Login</Link>
        </nav>
      </header>

      <main className="layout-main">{children}</main>

      <footer className="layout-footer">
        <small>AI4Juris &copy; {new Date().getFullYear()}</small>
      </footer>
    </div>
  );
}

export default Layout;
