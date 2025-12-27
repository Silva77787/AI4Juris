export const config = {
  apiUrl: import.meta.env.VITE_API_URL || 'http://localhost:7777',
  environment: import.meta.env.MODE, // 'development' ou 'production'
};