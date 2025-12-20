import './styles/App.css';

import { Routes, Route } from 'react-router-dom';

import AuthPage from './pages/AuthPage.jsx';
import HomePage from './pages/HomePage.jsx';
import UploadPage from './pages/UploadPage.jsx';
import AdminDashboardPage from './pages/AdminDashboardPage.jsx';
import GroupsPage from './pages/GroupsPage.jsx';
import DocumentDetailPage from './pages/DocumentDetailPage.jsx';
import ProfilePage from './pages/ProfilePage.jsx';

import PrivateRoute from './components/PrivateRoute.jsx'; // novo componente para proteção de rotas

function App() {
  return (
    <Routes>
      {/* Página inicial: login/register */}
      <Route path="/" element={<AuthPage />} />

      {/* Páginas protegidas: só acessíveis com token */}
      <Route 
        path="/home" 
        element={
          <PrivateRoute>
            <HomePage />
          </PrivateRoute>
        } 
      />
      <Route 
        path="/upload" 
        element={
          <PrivateRoute>
            <UploadPage />
          </PrivateRoute>
        } 
      />
      <Route 
        path="/admin" 
        element={
          <PrivateRoute>
            <AdminDashboardPage />
          </PrivateRoute>
        } 
      />
      <Route 
        path="/groups" 
        element={
          <PrivateRoute>
            <GroupsPage />
          </PrivateRoute>
        } 
      />
      <Route 
        path="/documents/:id" 
        element={
          <PrivateRoute>
            <DocumentDetailPage />
          </PrivateRoute>
        } 
      />
      <Route 
        path="/profile" 
        element={
          <PrivateRoute>
            <ProfilePage />
          </PrivateRoute>
        } 
      />
    </Routes>
  );
}

export default App;
