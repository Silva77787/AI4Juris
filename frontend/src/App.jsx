// src/App.jsx
import './App.css';
import { Routes, Route } from 'react-router-dom';
import Layout from './components/Layout.jsx';

import HomePage from './pages/HomePage.jsx';
import LoginPage from './pages/LoginPage.jsx';
import RegisterPage from './pages/RegisterPage.jsx';
import UploadPage from './pages/UploadPage.jsx';
import AdminDashboardPage from './pages/AdminDashboardPage.jsx';
import GroupsPage from './pages/GroupsPage.jsx';

function App() {
  return (
    <Layout>
      <Routes>
        <Route path="/" element={<HomePage />} />
        <Route path="/login" element={<LoginPage />} />
        <Route path="/register" element={<RegisterPage />} />
        <Route path="/upload" element={<UploadPage />} />
        <Route path="/admin" element={<AdminDashboardPage />} />
        <Route path="/groups" element={<GroupsPage />} />
      </Routes>
    </Layout>
  );
}

export default App;
