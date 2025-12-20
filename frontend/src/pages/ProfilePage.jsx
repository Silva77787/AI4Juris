// src/pages/ProfilePage.jsx
import { useEffect, useMemo, useState } from 'react';
import { Link } from 'react-router-dom';
import TopBar from '../components/TopBar.jsx';
import '../styles/HomePage.css';
import '../styles/ProfilePage.css';

const mockStats = {
  totalUploads: 151,
  processed: 114,
  processing: 28,
};

const mockTrend = [
  { label: '01/01', value: 8 },
  { label: '01/02', value: 12 },
  { label: '01/03', value: 16 },
  { label: '01/04', value: 19 },
  { label: '01/05', value: 24 },
  { label: '01/06', value: 27 },
  { label: '01/07', value: 31 },
  { label: '01/08', value: 38 },
  { label: '01/09', value: 44 },
  { label: '01/10', value: 52 },
  { label: '01/11', value: 61 },
];

const mockDescriptors = [
  { label: 'Direito Penal', value: 38 },
  { label: 'Direito Civil', value: 27 },
  { label: 'Recurso', value: 21 },
  { label: 'Responsabilidade', value: 14 },
];

const mockRecentDocs = [
  { name: 'acordao_1', date: '10/11/2025', labels: 'Penal / Recurso', status: 'Processado' },
  { name: 'acordao_2', date: '11/11/2025', labels: 'Civil', status: 'Em processamento' },
  { name: 'acordao_3', date: '14/11/2025', labels: 'Responsabilidade', status: 'Processado' },
];

function ProfilePage() {
  const [profile, setProfile] = useState({
    name: 'Joao',
    email: 'joao@email.com',
  });
  const [form, setForm] = useState({
    name: 'Joao',
    email: 'joao@email.com',
    currentPassword: '',
    newPassword: '',
    confirmPassword: '',
  });
  const [saved, setSaved] = useState(false);
  const [showEdit, setShowEdit] = useState(false);
  const [error, setError] = useState('');

  const polylinePoints = useMemo(() => {
    const maxValue = Math.max(...mockTrend.map((p) => p.value));
    return mockTrend
      .map((point, idx) => {
        const x = (idx / (mockTrend.length - 1)) * 360 + 20;
        const y = 140 - (point.value / maxValue) * 110 + 20;
        return `${x},${y}`;
      })
      .join(' ');
  }, []);

  const descriptorTotal = mockDescriptors.reduce((acc, item) => acc + item.value, 0);
  const donutStops = useMemo(() => {
    let acc = 0;
    return mockDescriptors.map((item) => {
      const start = acc;
      const size = (item.value / descriptorTotal) * 360;
      acc += size;
      return { start, end: acc, label: item.label };
    });
  }, [descriptorTotal]);

  const donutGradient = donutStops
    .map((stop, idx) => {
      const color = ['#3b82f6', '#22c1dc', '#f59e0b', '#8b5cf6'][idx % 4];
      return `${color} ${stop.start}deg ${stop.end}deg`;
    })
    .join(', ');

  useEffect(() => {
    const token = localStorage.getItem('accessToken');
    if (!token) return;

    fetch('http://localhost:7777/profile/', {
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
      setError('Não fizeste nenhuma alteração.');
      return;
    }

    if ((nameChanged || emailChanged || wantsPasswordChange) && !form.currentPassword) {
      setError('A password atual é obrigatória.');
      return;
    }

    if (wantsPasswordChange && form.newPassword !== form.confirmPassword) {
      setError('As passwords não coincidem.');
      return;
    }

    const token = localStorage.getItem('accessToken');
    if (!token) {
      setError('Sessão expirada. Faz login novamente.');
      return;
    }

    fetch('http://localhost:7777/profile/', {
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
        setSaved(true);
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
          <h1>Bem-vindo de volta, {profile.name}</h1>
          <button type="button" className="chip-btn edit-btn" onClick={handleOpenEdit}>
            Editar perfil
          </button>
        </header>

        <section className="stats-grid">
          <article className="stat-card">
            <p className="stat-value">{mockStats.totalUploads}</p>
            <p className="stat-label">Totais de uploads</p>
          </article>
          <article className="stat-card">
            <p className="stat-value">{mockStats.processed}</p>
            <p className="stat-label">Processados com sucesso</p>
          </article>
          <article className="stat-card">
            <p className="stat-value">{mockStats.processing}</p>
            <p className="stat-label">Em processamento</p>
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
              <svg viewBox="0 0 400 200" role="img" aria-label="Evolucao temporal dos uploads">
                <polyline points={polylinePoints} />
              </svg>
              <div className="chart-axis">
                {mockTrend.map((point) => (
                  <span key={point.label}>{point.label}</span>
                ))}
              </div>
            </div>
          </article>

          <article className="profile-card donut-card">
            <h2>Top descritores</h2>
            <div className="donut-wrap" style={{ background: `conic-gradient(${donutGradient})` }} />
            <div className="legend">
              {mockDescriptors.map((item, idx) => (
                <div key={item.label} className="legend-row">
                  <span className={`legend-dot legend-dot-${idx}`} />
                  <span>{item.label}</span>
                </div>
              ))}
            </div>
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
            {mockRecentDocs.map((doc) => (
              <div key={doc.name} className="table-row">
                <span>{doc.name}</span>
                <span>{doc.date}</span>
                <span>{doc.labels}</span>
                <span>{doc.status}</span>
              </div>
            ))}
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
                ×
              </button>
            </div>
            {saved && <div className="form-message saved-pill">Guardado</div>}
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
    </div>
  );
}

export default ProfilePage;
