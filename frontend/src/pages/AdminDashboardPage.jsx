import { useEffect, useMemo, useState } from "react";
import TopBar from "../components/TopBar.jsx";
import { config } from "../utils/config";
import "../styles/HomePage.css";
import "../styles/ProfilePage.css";
import "../styles/AdminDashboardPage.css";

const donutColors = ["#3b82f6", "#22c1dc", "#f59e0b", "#8b5cf6"];

function AdminDashboardPage() {
  const [profile, setProfile] = useState({ name: "", email: "" });
  const [metrics, setMetrics] = useState(null);
  const [trend, setTrend] = useState([]);
  const [descriptors, setDescriptors] = useState([]);
  const [recentDocs, setRecentDocs] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const token = localStorage.getItem("accessToken");
    if (!token) return;

    fetch(`${config.apiUrl}/profile/`, {
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${token}`,
      },
    })
      .then((res) => res.json())
      .then((data) => {
        if (data && data.email) {
          setProfile({ name: data.name || "", email: data.email || "" });
        }
      })
      .catch(() => {
        setProfile((prev) => ({ ...prev, name: prev.name || "" }));
      });
  }, []);

  useEffect(() => {
    const mock = {
      metrics: {
        totalDocuments: 250,
        processed: 220,
        processing: 18,
        users: 46,
      },
      trend: [
        { label: "Seg", value: 38 },
        { label: "Ter", value: 41 },
        { label: "Qua", value: 36 },
        { label: "Qui", value: 52 },
        { label: "Sex", value: 48 },
        { label: "Sab", value: 30 },
        { label: "Dom", value: 20 },
      ],
      descriptors: [
        { label: "Contratos", value: 82 },
        { label: "Faturas", value: 64 },
        { label: "Relatórios", value: 38 },
        { label: "Acórdãos", value: 26 },
      ],
      recentDocs: [
        { id: 1, name: "contrato1.pdf", user: "Joana", date: "2025-12-20", labels: 5, status: "Processado" },
        { id: 2, name: "fatura2.pdf", user: "Ricardo", date: "2025-12-20", labels: 3, status: "Processado" },
        { id: 3, name: "relatorio3.pdf", user: "Maria", date: "2025-12-19", labels: 4, status: "Erro" },
        { id: 4, name: "acordao4.pdf", user: "Pedro", date: "2025-12-19", labels: 0, status: "Em processamento" },
      ],
    };

    const timer = setTimeout(() => {
      setMetrics(mock.metrics);
      setTrend(mock.trend);
      setDescriptors(mock.descriptors);
      setRecentDocs(mock.recentDocs);
      setLoading(false);
    }, 300);

    return () => clearTimeout(timer);
  }, []);

  const polylinePoints = useMemo(() => {
    if (trend.length < 2) return "";
    const maxValue = Math.max(...trend.map((p) => p.value || 0), 1);
    return trend
      .map((point, idx) => {
        const x = (idx / (trend.length - 1)) * 360 + 20;
        const y = 140 - (point.value / maxValue) * 110 + 20;
        return `${x},${y}`;
      })
      .join(" ");
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
    .map((stop, idx) => `${donutColors[idx % donutColors.length]} ${stop.start}deg ${stop.end}deg`)
    .join(", ");

  const statusTone = (status) => {
    if (!status) return "status-default";
    const normalized = status.toLowerCase();
    if (normalized.includes("process")) return "status-processing";
    if (normalized.includes("erro")) return "status-error";
    return "status-success";
  };

  if (loading) return <div className="loading">A carregar dashboard…</div>;

  return (
    <div className="home-page">
      <div className="home-hero-bg" />
      <TopBar title="Admin Dashboard" />

      <main className="home-shell profile-shell admin-dashboard">
        <header className="profile-hero">
          <div>
            <h1>Bem-vindo de volta, {profile.name || "administrador"}</h1>
            <p className="muted">Estatísticas globais de utilizadores e documentos</p>
          </div>
        </header>

        <section className="stats-grid">
          <article className="stat-card">
            <p className="stat-value">{metrics.totalDocuments}</p>
            <p className="stat-label">Documentos submetidos</p>
          </article>
          <article className="stat-card">
            <p className="stat-value">{metrics.processed}</p>
            <p className="stat-label">Processados com sucesso</p>
          </article>
          <article className="stat-card">
            <p className="stat-value">{metrics.processing}</p>
            <p className="stat-label">Em processamento</p>
          </article>
          <article className="stat-card">
            <p className="stat-value">{metrics.users}</p>
            <p className="stat-label">Utilizadores ativos</p>
          </article>
        </section>

        <section className="profile-grid">
          <article className="profile-card chart-card">
            <div className="card-header">
              <h2>Evolucao semanal dos uploads</h2>
              <div className="chip-row">
                <button type="button" className="chip-btn active">7 dias</button>
                <button type="button" className="chip-btn">30 dias</button>
                <button type="button" className="chip-btn">1 ano</button>
              </div>
            </div>
            <div className="chart-wrap">
              {trend.length > 1 ? (
                <>
                  <svg viewBox="0 0 400 200" role="img" aria-label="Evolucao semanal dos uploads">
                    <polyline points={polylinePoints} />
                  </svg>
                  <div
                    className="chart-axis"
                    style={{ gridTemplateColumns: `repeat(${trend.length || 1}, 1fr)` }}
                  >
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
            <h2>Descritores mais usados</h2>
            <br />
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

        <section className="profile-card profile-latest admin-table">
          <div className="card-header">
            <h2>Uploads recentes</h2>
            <span className="muted">Os ultimos 20 documentos processados</span>
          </div>
          <div className="table">
            <div className="table-row table-head">
              <span>Documento</span>
              <span>Utilizador</span>
              <span>Data</span>
              <span>Descritores</span>
              <span>Estado</span>
            </div>
            {recentDocs.length ? (
              recentDocs.map((doc) => (
                <div key={doc.id} className="table-row">
                  <span>{doc.name}</span>
                  <span>{doc.user}</span>
                  <span>{doc.date}</span>
                  <span>{doc.labels}</span>
                  <span className={`status-pill ${statusTone(doc.status)}`}>{doc.status}</span>
                </div>
              ))
            ) : (
              <div className="table-row">
                <span>Sem dados</span>
                <span>-</span>
                <span>-</span>
                <span>-</span>
                <span>-</span>
              </div>
            )}
          </div>
        </section>
      </main>
    </div>
  );
}

export default AdminDashboardPage;