// src/components/PrivateRoute.jsx
import { Navigate } from 'react-router-dom';

function PrivateRoute({ children }) {
  const token = localStorage.getItem('accessToken');
  if (!token) return <Navigate to="/" replace />; // redireciona se não tiver token
  return children;
}

export default PrivateRoute;
