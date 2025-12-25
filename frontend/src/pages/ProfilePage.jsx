// src/pages/ProfilePage.jsx
import { useEffect, useMemo, useState } from 'react';
import { Link } from 'react-router-dom';
import TopBar from '../components/TopBar.jsx';
import DynamicToast from './DynamicToast.jsx';
import '../styles/HomePage.css';
import '../styles/ProfilePage.css';
import { config } from '../utils/config';

function ProfilePage() {
  const [profile, setProfile] = useState({
    name: '',
    email: '',
  });
  const [form, setForm] = useState({
    name: '',
    email: '',
    currentPassword: '',
    newPassword: '',
    confirmPassword: '',
  });
  const [showEdit, setShowEdit] = useState(false);
  const [error, setError] = useState('');
  const [stats, setStats] = useState(null);
  const [trend, setTrend] = useState([]);
  const [descriptors, setDescriptors] = useState([]);
  const [recentDocs, setRecentDocs] = useState([]);
  const [toasts, setToasts] = useState([]);

  const pushToast = (message, type = 'success') => {
    const id = `${Date.now()}-${Math.random()}`;
    setToasts((prev) => [...prev.slice(-4), { id, message, type }]);
    setTimeout(() => {
      setToasts((prev) => prev.filter((toast) => toast.id !== id));
    }, 5000);
  };

  const dismissToast = (id) => {
    setToasts((prev) => prev.filter((toast) => toast.id !== id));
  };

  const polylinePoints = useMemo(() => {
    if (trend.length < 2) return '';
    const maxValue = Math.max(...trend.map((p) => p.value || 0), 1);
    return trend
      .map((point, idx) => {
        const x = (idx / (trend.length - 1)) * 360 + 20;
        const y = 140 - (point.value / maxValue) * 110 + 20;
        return `${x},${y}`;
      })
      .join(' ');
  }, [trend]);

  const descriptorTotal = descriptors.reduce((acc, item) => acc + item.value, 0);
  const donutStops = useMemo(() => {
    if (!descriptorTotal) return [];
    let acc = 0;
    return descriptors.map((item) => {
      const start = acc;
      const size = (item.value / descriptorTotal) * 360;
      acc += size;
      return { start, end: acc, label: item.label };
    });
  }, [descriptorTotal, descriptors]);

  const donutGradient = donutStops
    .map((stop, idx) => {
      const color = ['#3b82f6', '#22c1dc', '#f59e0b', '#8b5cf6'][idx % 4];
      return `${color} ${stop.start}deg ${stop.end}deg`;
    })
    .join(', ');

  useEffect(() => {
    const token = localStorage.getItem('accessToken');
    if (!token) return;

    fetch(`${config.apiUrl}/profile/`, {
      headers: {
        'Content-Type': 'application/json',
        Authorization: `Bearer ${token}`,
      },
    })
      .then((res) => res.json())
      .then((data) => {
        if (data && data.email) {
          setProfile({
            name: data.name || '',
            email: data.email || '',
          });
          setForm((prev) => ({
            ...prev,
            name: data.name || '',
            email: data.email || '',
          }));
        }
      })
      .catch((err) => {
        console.error('Erro ao carregar perfil:', err);
      });
  }, []);

  useEffect(() => {
    if (!showEdit) return;

    const handleKeyDown = (event) => {
      if (event.key === 'Escape') {
        setShowEdit(false);
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [showEdit]);

  const handleChange = (evt) => {
    setForm({ ...form, [evt.target.name]: evt.target.value });
  };

  const handleOpenEdit = () => {
    setError('');
    setForm((prev) => ({
      ...prev,
      currentPassword: '',
      newPassword: '',
      confirmPassword: '',
    }));
    setShowEdit(true);
  };

  const handleSubmit = (evt) => {
    evt.preventDefault();
    setError('');

    const nameChanged = form.name !== profile.name;
    const emailChanged = form.email !== profile.email;
    const wantsPasswordChange = !!(form.newPassword || form.confirmPassword);

    if (!nameChanged && !emailChanged && !wantsPasswordChange) {
      setError('Nao fizeste nenhuma alteracao.');
      return;
    }

    if ((nameChanged || emailChanged || wantsPasswordChange) && !form.currentPassword) {
      setError('A password atual e obrigatoria.');
      return;
    }

    if (wantsPasswordChange && form.newPassword !== form.confirmPassword) {
      setError('As passwords nao coincidem.');
      return;
    }

    const token = localStorage.getItem('accessToken');
    if (!token) {
      setError('Sessao expirada. Faz login novamente.');
      return;
    }

    fetch(`${config.apiUrl}/profile/`, {
      method: 'PATCH',
      headers: {
        'Content-Type': 'application/json',
        Authorization: `Bearer ${token}`,
      },
      body: JSON.stringify({
        name: form.name,
        email: form.email,
        current_password: form.currentPassword || undefined,
        new_password: form.newPassword || undefined,
        confirm_password: form.confirmPassword || undefined,
      }),
    })
      .then((res) => res.json().then((data) => ({ ok: res.ok, data })))
      .then(({ ok, data }) => {
        if (!ok) {
          setError(data.error || 'Erro ao guardar perfil.');
          return;
        }

        setProfile((prev) => ({
          ...prev,
          name: data.name || prev.name,
          email: data.email || prev.email,
        }));
        setForm((prev) => ({
          ...prev,
          name: data.name || prev.name,
          email: data.email || prev.email,
          currentPassword: '',
          newPassword: '',
          confirmPassword: '',
        }));

        if (nameChanged) {
          pushToast('Nome alterado com sucesso.', 'success');
        }
        if (emailChanged) {
          pushToast('Email alterado com sucesso.', 'success');
        }
        if (wantsPasswordChange) {
          pushToast('Palavra-passe alterada com sucesso.', 'success');
        }

        setShowEdit(false);
      })
      .catch((err) => {
        console.error('Erro ao guardar perfil:', err);
        setError('Erro ao guardar perfil.');
      });
  };

  return (
    <div className="home-page">
      <div className="home-hero-bg" />
      <TopBar title="Perfil" />

      <main className="home-shell profile-shell">
        <header className="profile-hero">
          <h1>Bem-vindo de volta, {profile.name || 'utilizador'}</h1>
          <button type="button" className="chip-btn edit-btn" onClick={handleOpenEdit}>
            Editar perfil
          </button>
        </header>

        <section className="stats-grid">
          <article className="stat-card">
            <p className="stat-value">{stats ? stats.totalUploads : '--'}</p>
            <p className="stat-label">{stats ? 'Totais de uploads' : 'Sem dados'}</p>
          </article>
          <article className="stat-card">
            <p className="stat-value">{stats ? stats.processed : '--'}</p>
            <p className="stat-label">{stats ? 'Processados com sucesso' : 'Sem dados'}</p>
          </article>
          <article className="stat-card">
            <p className="stat-value">{stats ? stats.processing : '--'}</p>
            <p className="stat-label">{stats ? 'Em processamento' : 'Sem dados'}</p>
          </article>
        </section>

        <section className="profile-grid">
          <article className="profile-card chart-card">
            <div className="card-header">
              <h2>Evolucao temporal dos uploads</h2>
              <div className="chip-row">
                <button type="button" className="chip-btn active">7 dias</button>
                <button type="button" className="chip-btn">30 dias</button>
                <button type="button" className="chip-btn">1 ano</button>
              </div>
            </div>
            <div className="chart-wrap">
              {trend.length > 1 ? (
                <>
                  <svg viewBox="0 0 400 200" role="img" aria-label="Evolucao temporal dos uploads">
                    <polyline points={polylinePoints} />
                  </svg>
                  <div className="chart-axis">
                    {trend.map((point) => (
                      <span key={point.label}>{point.label}</span>
                    ))}
                  </div>
                </>
              ) : (
                <div className="chart-empty">Sem dados</div>
              )}
            </div>
          </article>

          <article className="profile-card donut-card">
            <h2>Top descritores</h2>
            {descriptors.length ? (
              <>
                <div className="donut-wrap" style={{ background: `conic-gradient(${donutGradient})` }} />
                <div className="legend">
                  {descriptors.map((item, idx) => (
                    <div key={item.label} className="legend-row">
                      <span className={`legend-dot legend-dot-${idx}`} />
                      <span>{item.label}</span>
                    </div>
                  ))}
                </div>
              </>
            ) : (
              <div className="chart-empty">Sem dados</div>
            )}
          </article>
        </section>

        <section className="profile-card profile-latest">
          <div className="card-header">
            <h2>Ultimos documentos processados</h2>
            <Link to="/home" className="chip-btn">Ver historico</Link>
          </div>
          <div className="table">
            <div className="table-row table-head">
              <span>Nome</span>
              <span>Data</span>
              <span>Rotulos</span>
              <span>Estado</span>
            </div>
            {recentDocs.length ? (
              recentDocs.map((doc) => (
                <div key={doc.name} className="table-row">
                  <span>{doc.name}</span>
                  <span>{doc.date}</span>
                  <span>{doc.labels}</span>
                  <span>{doc.status}</span>
                </div>
              ))
            ) : (
              <div className="table-row">
                <span>Sem dados</span>
                <span>-</span>
                <span>-</span>
                <span>-</span>
              </div>
            )}
          </div>
        </section>
      </main>

      {showEdit && (
        <div className="modal-backdrop" role="presentation" onClick={() => setShowEdit(false)}>
          <div className="modal-card" role="dialog" aria-modal="true" onClick={(e) => e.stopPropagation()}>
            <div className="modal-header">
              <div>
                <h2>Editar perfil</h2>
              </div>
              <button type="button" className="modal-close" onClick={() => setShowEdit(false)} aria-label="Fechar">
                x
              </button>
            </div>
            {error && <div className="form-message form-error">{error}</div>}
            <form onSubmit={handleSubmit} className="modal-form" autoComplete="off">
              <label>
                Nome
                <input
                  type="text"
                  name="name"
                  autoComplete="off"
                  value={form.name}
                  onChange={handleChange}
                />
              </label>
              <label>
                Email
                <input
                  type="email"
                  name="email"
                  autoComplete="off"
                  value={form.email}
                  onChange={handleChange}
                />
              </label>
              <label className="full-row">
                Password atual
                <input
                  type="password"
                  name="currentPassword"
                  autoComplete="new-password"
                  value={form.currentPassword}
                  onChange={handleChange}
                />
              </label>
              <label>
                Nova password
                <input
                  type="password"
                  name="newPassword"
                  autoComplete="new-password"
                  value={form.newPassword}
                  onChange={handleChange}
                />
              </label>
              <label>
                Repetir password
                <input
                  type="password"
                  name="confirmPassword"
                  autoComplete="new-password"
                  value={form.confirmPassword}
                  onChange={handleChange}
                />
              </label>
              <div className="modal-actions">
                <button type="submit" className="save-btn">Guardar alteracoes</button>
              </div>
            </form>
          </div>
        </div>
      )}

      <DynamicToast toasts={toasts} onDismiss={dismissToast} />
    </div>
  );
}

export default ProfilePage;
