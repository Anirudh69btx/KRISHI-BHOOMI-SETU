import React from 'react';
import ReactDOM from 'react-dom/client';
import App from './App';
import './index.css';

// Register service worker
if ('serviceWorker' in navigator && import.meta.env.PROD) {
  window.addEventListener('load', () => {
    navigator.serviceWorker.register('/sw.js', { scope: '/' }).then(
      (reg) => console.info('[SW] Registered:', reg.scope),
      (err) => console.error('[SW] Registration failed:', err),
    );
  });
}

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>,
);
