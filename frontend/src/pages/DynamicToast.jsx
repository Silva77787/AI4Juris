// src/pages/DynamicToast.jsx
import '../styles/DynamicToast.css';

function DynamicToast({ toasts, onDismiss }) {
  if (!toasts || !toasts.length) return null;

  return (
    <div className="toast-stack" role="status" aria-live="polite">
      {toasts.map((toast) => (
        <div key={toast.id} className={`toast-card ${toast.type || 'success'}`}>
          <span className="toast-message">{toast.message}</span>
          <button
            type="button"
            className="toast-close"
            onClick={() => onDismiss && onDismiss(toast.id)}
            aria-label="Fechar notificacao"
          >
            x
          </button>
        </div>
      ))}
    </div>
  );
}

export default DynamicToast;
