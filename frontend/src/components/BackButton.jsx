import { useNavigate } from 'react-router-dom';

function BackButton({ fallback = '/home', label = 'Voltar' }) {
  const navigate = useNavigate();

  const handleClick = () => {
    if (window.history.length > 1) {
      navigate(-1);
    } else {
      navigate(fallback);
    }
  };

  return (
    <button className="nav-btn ghost back-btn" onClick={handleClick}>
      {label}
    </button>
  );
}

export default BackButton;
