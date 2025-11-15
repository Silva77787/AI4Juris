import './styles/App.css';
import './styles/auth.css';

import { Routes, Route, Navigate } from 'react-router-dom';

import HomePage from './pages/HomePage.jsx';
import AuthPage from './pages/AuthPage.jsx';
import UploadPage from './pages/UploadPage.jsx';
import AdminDashboardPage from './pages/AdminDashboardPage.jsx';
import GroupsPage from './pages/GroupsPage.jsx';

function App() {
  
  const handleLogin = (token) => {
          localStorage.setItem("token", token);
          setAuth(token);
      };

  return (
    <Routes>
      {/* LOGIN / REGISTER COM O MESMO COMPONENTE */}
      <Route path="/" element={<AuthPage onLogin={handleLogin} />} />

    </Routes>
  );
}

export default App;
