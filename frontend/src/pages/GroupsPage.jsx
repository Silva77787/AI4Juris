// src/pages/GroupsPage.jsx
import { useEffect, useMemo, useRef, useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import TopBar from '../components/TopBar.jsx';
import DynamicToast from '../components/DynamicToast.jsx';
import '../styles/HomePage.css';
import '../styles/GroupsPage.css';
import { config } from '../utils/config';

const API_BASE = config.apiUrl;
const GROUP_PAGE_SIZE = 5;

const normalizeRole = (role) => (role === 'owner' ? 'owner' : 'member');

function GroupsPage() {
  const navigate = useNavigate();
  const [groups, setGroups] = useState([]);
  const [groupsLoading, setGroupsLoading] = useState(true);
  const [groupsError, setGroupsError] = useState('');

  const [selectedGroupId, setSelectedGroupId] = useState(null);
  const [members, setMembers] = useState([]);
  const [membersLoading, setMembersLoading] = useState(false);
  const [membersError, setMembersError] = useState('');

  const [joinRequests, setJoinRequests] = useState([]);
  const [requestsLoading, setRequestsLoading] = useState(false);
  const [requestsError, setRequestsError] = useState('');

  const [invites, setInvites] = useState([]);
  const [invitesLoading, setInvitesLoading] = useState(false);
  const [invitesError, setInvitesError] = useState('');

  const [groupDocuments, setGroupDocuments] = useState([]);
  const [groupDocsLoading, setGroupDocsLoading] = useState(false);
  const [groupDocsError, setGroupDocsError] = useState('');
  const [groupUploadFile, setGroupUploadFile] = useState(null);
  const [groupUploading, setGroupUploading] = useState(false);
  const groupFileInputRef = useRef(null);
  const [showGroupUpload, setShowGroupUpload] = useState(false);
  const [groupIsDragging, setGroupIsDragging] = useState(false);
  const [groupUploadError, setGroupUploadError] = useState('');
  const [groupSearchTerm, setGroupSearchTerm] = useState('');
  const [groupSortOrder, setGroupSortOrder] = useState('desc');
  const [groupStateFilter, setGroupStateFilter] = useState('');
  const [groupClassificationFilter, setGroupClassificationFilter] = useState('');
  const [groupPage, setGroupPage] = useState(1);

  const [createName, setCreateName] = useState('');
  const [inviteEmail, setInviteEmail] = useState('');
  const [joinCode, setJoinCode] = useState('');
  const [toasts, setToasts] = useState([]);
  const [confirmDialog, setConfirmDialog] = useState(null);
  const [groupActionsOpen, setGroupActionsOpen] = useState(false);

  const selectedGroup = useMemo(
    () => groups.find((group) => group.id === selectedGroupId) || null,
    [groups, selectedGroupId]
  );

  const userIsOwner = selectedGroup && normalizeRole(selectedGroup.role) === 'owner';
  const ownerCount = members.filter((member) => normalizeRole(member.role) === 'owner').length;

  const authFetch = (path, options = {}) => {
    const token = localStorage.getItem('accessToken');
    if (!token) {
      navigate('/');
      return Promise.reject(new Error('Missing token'));
    }

    const isFormData = options.body instanceof FormData;
    const headers = {
      Authorization: `Bearer ${token}`,
      ...(options.headers || {}),
    };
    if (!isFormData && !headers['Content-Type']) {
      headers['Content-Type'] = 'application/json';
    }

    return fetch(`${API_BASE}${path}`, {
      headers,
      ...options,
    }).then((res) => {
      if (res.status === 401) {
        localStorage.removeItem('accessToken');
        localStorage.removeItem('refreshToken');
        navigate('/');
      }
      return res;
    });
  };

  const pushToast = (message, type = 'success') => {
    const id = `${Date.now()}-${Math.random().toString(16).slice(2)}`;
    setToasts((prev) => {
      const next = [...prev, { id, message, type }];
      return next.slice(-5);
    });
    setTimeout(() => {
      setToasts((prev) => prev.filter((toast) => toast.id !== id));
    }, 5000);
  };

  const dismissToast = (id) => {
    setToasts((prev) => prev.filter((toast) => toast.id !== id));
  };

  const loadGroups = () => {
    setGroupsLoading(true);
    setGroupsError('');

    authFetch('/groups/my/')
      .then((res) => {
        if (!res.ok) throw new Error('Failed');
        return res.json();
      })
      .then((data) => {
        const normalized = Array.isArray(data) ? data : [];
        setGroups(normalized);
        if (normalized.length && !selectedGroupId) {
          setSelectedGroupId(normalized[0].id);
        }
      })
      .catch(() => {
        setGroupsError('Nao foi possivel carregar os grupos.');
      })
      .finally(() => {
        setGroupsLoading(false);
      });
  };

  const loadMembers = (groupId) => {
    if (!groupId) return;
    setMembersLoading(true);
    setMembersError('');

    authFetch(`/groups/${groupId}/members/`)
      .then((res) => {
        if (!res.ok) throw new Error('Failed');
        return res.json();
      })
      .then((data) => {
        const normalized = Array.isArray(data)
          ? data.map((member) => ({ ...member, role: normalizeRole(member.role) }))
          : [];
        setMembers(normalized);
      })
      .catch(() => {
        setMembersError('Nao foi possivel carregar os membros.');
      })
      .finally(() => {
        setMembersLoading(false);
      });
  };

  const loadGroupDocuments = (groupId) => {
    if (!groupId) return;
    setGroupDocsLoading(true);
    setGroupDocsError('');

    authFetch(`/groups/${groupId}/documents/`)
      .then((res) => {
        if (!res.ok) throw new Error('Failed');
        return res.json();
      })
      .then((data) => {
        const normalized = Array.isArray(data) ? data : [];
        setGroupDocuments(normalized);
      })
      .catch(() => {
        setGroupDocsError('Nao foi possivel carregar o historico do grupo.');
        setGroupDocuments([]);
      })
      .finally(() => {
        setGroupDocsLoading(false);
      });
  };

  const loadJoinRequests = (groupId) => {
    if (!groupId) return;
    setRequestsLoading(true);
    setRequestsError('');

    authFetch(`/groups/${groupId}/join-requests/`)
      .then((res) => {
        if (!res.ok) throw new Error('Failed');
        return res.json();
      })
      .then((data) => {
        const normalized = Array.isArray(data) ? data : [];
        setJoinRequests(normalized);
      })
      .catch(() => {
        setRequestsError('Nao foi possivel carregar pedidos.');
      })
      .finally(() => {
        setRequestsLoading(false);
      });
  };

  const loadInvites = () => {
    setInvitesLoading(true);
    setInvitesError('');

    authFetch('/groups/invites/my/')
      .then((res) => {
        if (!res.ok) throw new Error('Failed');
        return res.json();
      })
      .then((data) => {
        const normalized = Array.isArray(data) ? data : [];
        setInvites(normalized);
      })
      .catch(() => {
        setInvitesError('Nao foi possivel carregar convites.');
      })
      .finally(() => {
        setInvitesLoading(false);
      });
  };

  useEffect(() => {
    loadGroups();
    loadInvites();
  }, []);

  useEffect(() => {
    if (selectedGroupId) {
      loadMembers(selectedGroupId);
      loadGroupDocuments(selectedGroupId);
    } else {
      setMembers([]);
      setGroupDocuments([]);
      setGroupUploadFile(null);
    }
  }, [selectedGroupId]);


  const groupClassificationOptions = useMemo(() => {
    const labels = new Set();
    groupDocuments.forEach((doc) => {
      if (Array.isArray(doc.labels)) {
        doc.labels.forEach((label) => {
          if (label) labels.add(label);
        });
      }
    });
    return Array.from(labels).sort((a, b) => a.localeCompare(b));
  }, [groupDocuments]);
  const stateFilterOptions = [
    { value: 'done', label: 'Done' },
    { value: 'error', label: 'Error' },
    { value: 'processing', label: 'Processing' },
    { value: 'queued', label: 'In queue' },
  ];

  const filteredGroupDocs = useMemo(() => {
    const bySearch = groupDocuments.filter((doc) => {
      if (!groupSearchTerm.trim()) return true;
      const query = groupSearchTerm.toLowerCase();
      return (
        (doc.title && doc.title.toLowerCase().includes(query)) ||
        (doc.filename && doc.filename.toLowerCase().includes(query))
      );
    });

    const byState = bySearch.filter((doc) => {
      if (!groupStateFilter || groupStateFilter === 'all') return true;
      const statusText = (doc.state || doc.status || '').toLowerCase();
      return statusText === groupStateFilter;
    });

    const byClassification = byState.filter((doc) => {
      if (!groupClassificationFilter || groupClassificationFilter === 'all') return true;
      const hasLabels = doc.labels && doc.labels.length;
      return hasLabels && doc.labels.includes(groupClassificationFilter);
    });

    const sorted = [...byClassification].sort((a, b) => {
      const da = a.created_at || a.uploaded_at ? new Date(a.created_at || a.uploaded_at).getTime() : 0;
      const db = b.created_at || b.uploaded_at ? new Date(b.created_at || b.uploaded_at).getTime() : 0;
      return groupSortOrder === 'asc' ? da - db : db - da;
    });

    return sorted;
  }, [groupDocuments, groupClassificationFilter, groupSearchTerm, groupSortOrder, groupStateFilter]);

  useEffect(() => {
    setGroupPage(1);
  }, [groupSearchTerm, groupSortOrder, groupStateFilter, groupClassificationFilter, selectedGroupId]);

  const totalGroupPages = Math.max(1, Math.ceil(filteredGroupDocs.length / GROUP_PAGE_SIZE));
  const clampedGroupPage = Math.min(groupPage, totalGroupPages);
  const pagedGroupDocs = filteredGroupDocs.slice(
    (clampedGroupPage - 1) * GROUP_PAGE_SIZE,
    clampedGroupPage * GROUP_PAGE_SIZE
  );

  useEffect(() => {
    if (selectedGroupId && userIsOwner) {
      loadJoinRequests(selectedGroupId);
    } else {
      setJoinRequests([]);
    }
  }, [selectedGroupId, userIsOwner]);

  const handleCreateGroup = (event) => {
    event.preventDefault();

    if (!createName.trim()) {
      pushToast('O nome do grupo e obrigatorio.', 'error');
      return;
    }

    authFetch('/groups/create/', {
      method: 'POST',
      body: JSON.stringify({ name: createName.trim() }),
    })
      .then((res) => res.json().then((data) => ({ ok: res.ok, data })))
      .then(({ ok, data }) => {
        if (!ok) {
          pushToast(data.error || 'Erro ao criar grupo.', 'error');
          return;
        }
        setCreateName('');
        pushToast('Grupo criado.', 'success');
        loadGroups();
      })
      .catch(() => {
        pushToast('Erro ao criar grupo.', 'error');
      });
  };

  const handleInviteMember = (event) => {
    event.preventDefault();

    if (!inviteEmail.trim()) {
      pushToast('Indica um email valido.', 'error');
      return;
    }

    if (!selectedGroupId) {
      pushToast('Seleciona um grupo primeiro.', 'error');
      return;
    }

    authFetch(`/groups/${selectedGroupId}/invite/`, {
      method: 'POST',
      body: JSON.stringify({ email: inviteEmail.trim() }),
    })
      .then((res) => res.json().then((data) => ({ ok: res.ok, data })))
      .then(({ ok, data }) => {
        if (!ok) {
          pushToast(data.error || 'Erro ao convidar.', 'error');
          return;
        }
        setInviteEmail('');
        pushToast(data.message || 'Convite enviado.', 'success');
        loadJoinRequests(selectedGroupId);
      })
      .catch(() => {
        pushToast('Erro ao convidar.', 'error');
      });
  };

  const handleJoinGroup = (event) => {
    event.preventDefault();

    if (!joinCode.trim()) {
      pushToast('Insere o codigo de convite.', 'error');
      return;
    }

    authFetch(`/groups/join/${joinCode.trim()}/`, { method: 'POST' })
      .then((res) => res.json().then((data) => ({ ok: res.ok, data })))
      .then(({ ok, data }) => {
        if (!ok) {
          pushToast(data.error || 'Erro ao enviar pedido.', 'error');
          return;
        }
        setJoinCode('');
        pushToast(data.message || 'Pedido enviado.', 'success');
        loadGroups();
      })
      .catch(() => {
        pushToast('Erro ao enviar pedido.', 'error');
      });
  };

  const handleGroupFileChange = (event) => {
    const file = event.target.files && event.target.files[0];
    if (!file) return;
    handleGroupFileSelect(file);
  };

  const handleGroupFileSelect = (file) => {
    if (!file) return;
    if (file.type !== 'application/pdf') {
      setGroupUploadError('Formato invalido. O ficheiro tem de ser PDF.');
      setGroupUploadFile(null);
      return;
    }
    setGroupUploadError('');
    setGroupUploadFile(file);
  };

  const handleGroupUpload = () => {
    if (!selectedGroupId || !groupUploadFile || groupUploading) return;
    setGroupUploading(true);

    const formData = new FormData();
    formData.append('file', groupUploadFile);
    formData.append('filename', groupUploadFile.name);

    authFetch(`/groups/${selectedGroupId}/documents/upload/`, {
      method: 'POST',
      body: formData,
    })
      .then((res) => res.json().then((data) => ({ ok: res.ok, data })))
      .then(({ ok, data }) => {
        if (!ok) {
          pushToast(data.error || data.detail || 'Erro ao enviar documento.', 'error');
          return;
        }
        setGroupDocuments((prev) => [data, ...prev]);
        setGroupUploadFile(null);
        setShowGroupUpload(false);
        pushToast('Documento enviado para o grupo.', 'success');
      })
      .catch(() => {
        pushToast('Erro ao enviar documento.', 'error');
      })
      .finally(() => {
        setGroupUploading(false);
      });
  };

  const handleSelectGroupFile = () => {
    if (groupUploading) return;
    if (groupFileInputRef.current) {
      groupFileInputRef.current.click();
    }
  };

  const handleGroupDrop = (event) => {
    event.preventDefault();
    setGroupIsDragging(false);
    const file = event.dataTransfer.files && event.dataTransfer.files[0];
    handleGroupFileSelect(file);
  };

  const handleGroupDragOver = (event) => {
    event.preventDefault();
  };

  const handleGroupDragEnter = (event) => {
    event.preventDefault();
    setGroupIsDragging(true);
  };

  const handleGroupDragLeave = (event) => {
    event.preventDefault();
    if (event.currentTarget === event.target) {
      setGroupIsDragging(false);
    }
  };

  const handleCopyInviteCode = (code) => {
    if (!code || !navigator.clipboard) {
      pushToast('Nao foi possivel copiar o codigo.', 'error');
      return;
    }
    navigator.clipboard.writeText(code).then(
      () => {
        pushToast('Codigo copiado.', 'success');
      },
      () => {
        pushToast('Nao foi possivel copiar o codigo.', 'error');
      }
    );
  };

  const handleApproveRequest = (requestId) => {
    authFetch(`/groups/join-requests/${requestId}/approve/`, { method: 'POST' })
      .then((res) => res.json().then((data) => ({ ok: res.ok, data })))
      .then(({ ok, data }) => {
        if (!ok) {
          setRequestsError(data.error || 'Erro ao aprovar pedido.');
          pushToast(data.error || 'Erro ao aprovar pedido.', 'error');
          return;
        }
        pushToast(data.message || 'Pedido aprovado.', 'success');
        loadJoinRequests(selectedGroupId);
        loadMembers(selectedGroupId);
      })
      .catch(() => {
        setRequestsError('Erro ao aprovar pedido.');
        pushToast('Erro ao aprovar pedido.', 'error');
      });
  };

  const handleRejectRequest = (requestId) => {
    authFetch(`/groups/join-requests/${requestId}/reject/`, { method: 'POST' })
      .then((res) => res.json().then((data) => ({ ok: res.ok, data })))
      .then(({ ok, data }) => {
        if (!ok) {
          setRequestsError(data.error || 'Erro ao recusar pedido.');
          pushToast(data.error || 'Erro ao recusar pedido.', 'error');
          return;
        }
        pushToast(data.message || 'Pedido recusado.', 'success');
        loadJoinRequests(selectedGroupId);
      })
      .catch(() => {
        setRequestsError('Erro ao recusar pedido.');
        pushToast('Erro ao recusar pedido.', 'error');
      });
  };

  const handleAcceptInvite = (inviteId) => {
    authFetch(`/groups/invites/${inviteId}/accept/`, { method: 'POST' })
      .then((res) => res.json().then((data) => ({ ok: res.ok, data })))
      .then(({ ok, data }) => {
        if (!ok) {
          setInvitesError(data.error || 'Erro ao aceitar convite.');
          pushToast(data.error || 'Erro ao aceitar convite.', 'error');
          return;
        }
        pushToast(data.message || 'Convite aceite.', 'success');
        loadInvites();
        loadGroups();
      })
      .catch(() => {
        setInvitesError('Erro ao aceitar convite.');
        pushToast('Erro ao aceitar convite.', 'error');
      });
  };

  const handleDeclineInvite = (inviteId) => {
    authFetch(`/groups/invites/${inviteId}/decline/`, { method: 'POST' })
      .then((res) => res.json().then((data) => ({ ok: res.ok, data })))
      .then(({ ok, data }) => {
        if (!ok) {
          setInvitesError(data.error || 'Erro ao recusar convite.');
          pushToast(data.error || 'Erro ao recusar convite.', 'error');
          return;
        }
        pushToast(data.message || 'Convite recusado.', 'success');
        loadInvites();
      })
      .catch(() => {
        setInvitesError('Erro ao recusar convite.');
        pushToast('Erro ao recusar convite.', 'error');
      });
  };

  const handlePromoteOwner = (memberId) => {
    if (ownerCount >= 2) {
      pushToast('Limite de 2 owners atingido.', 'error');
      return;
    }

    authFetch(`/groups/${selectedGroupId}/promote/${memberId}/`, { method: 'POST' })
      .then((res) => res.json().then((data) => ({ ok: res.ok, data })))
      .then(({ ok, data }) => {
        if (!ok) {
          pushToast(data.error || 'Erro ao promover.', 'error');
          return;
        }
        pushToast(data.message || 'Owner atualizado.', 'success');
        loadMembers(selectedGroupId);
        loadGroups();
      })
      .catch(() => {
        pushToast('Erro ao promover.', 'error');
      });
  };

  const handleDemoteOwner = (memberId) => {
    authFetch(`/groups/${selectedGroupId}/demote/${memberId}/`, { method: 'POST' })
      .then((res) => res.json().then((data) => ({ ok: res.ok, data })))
      .then(({ ok, data }) => {
        if (!ok) {
          pushToast(data.error || 'Erro ao rebaixar.', 'error');
          return;
        }
        pushToast(data.message || 'Owner atualizado.', 'success');
        loadMembers(selectedGroupId);
        loadGroups();
      })
      .catch(() => {
        pushToast('Erro ao rebaixar.', 'error');
      });
  };

  const handleRemoveMember = (memberId) => {
    authFetch(`/groups/${selectedGroupId}/remove/${memberId}/`, { method: 'POST' })
      .then((res) => res.json().then((data) => ({ ok: res.ok, data })))
      .then(({ ok, data }) => {
        if (!ok) {
          pushToast(data.error || 'Erro ao expulsar.', 'error');
          return;
        }
        pushToast(data.message || 'Membro removido.', 'success');
        loadMembers(selectedGroupId);
        loadGroups();
      })
      .catch(() => {
        pushToast('Erro ao expulsar.', 'error');
      });
  };

  const handleLeaveGroupConfirmed = () => {
    if (!selectedGroupId) return;

    authFetch(`/groups/${selectedGroupId}/leave/`, { method: 'POST' })
      .then((res) => res.json().then((data) => ({ ok: res.ok, data })))
      .then(({ ok, data }) => {
        if (!ok) {
          pushToast(data.error || 'Erro ao sair do grupo.', 'error');
          return;
        }
        pushToast(data.message || 'Saiste do grupo.', 'success');
        setSelectedGroupId(null);
        loadGroups();
        loadInvites();
      })
      .catch(() => {
        pushToast('Erro ao sair do grupo.', 'error');
      });
  };

  const openLeaveGroupDialog = () => {
    if (!selectedGroupId) return;
    setConfirmDialog({ type: 'leave' });
  };

  const openRemoveMemberDialog = (member) => {
    setConfirmDialog({
      type: 'remove',
      memberId: member.id,
      memberEmail: member.email,
    });
  };

  const handleConfirmAction = () => {
    if (!confirmDialog) return;
    const { type, memberId } = confirmDialog;
    setConfirmDialog(null);
    if (type === 'remove') {
      handleRemoveMember(memberId);
    } else if (type === 'leave') {
      handleLeaveGroupConfirmed();
    }
  };

  return (
    <div className="home-page groups-page">
      <div className="home-hero-bg" />
      <TopBar title="Grupos" />

      <main className="home-shell groups-shell">
        <header className="groups-hero">
          <div>
            <p className="eyebrow">Workspace colaborativo</p>
            <h1>Gestao de grupos</h1>
            <p className="hero-sub">Cria grupos, gere membros e responde a convites e pedidos.</p>
          </div>
          <div className="hero-actions">
            <form className="panel-card compact-card" onSubmit={handleCreateGroup}>
              <div className="card-header">
                <h2>Criar grupo</h2>
              </div>
              <label className="form-field">
                Nome do grupo
                <input
                  type="text"
                  value={createName}
                  onChange={(event) => setCreateName(event.target.value)}
                  placeholder="Ex: Equipa Penal"
                />
              </label>
              <button type="submit" className="primary-btn">
                Criar grupo
              </button>
            </form>

            <form className="panel-card compact-card" onSubmit={handleJoinGroup}>
              <div className="card-header">
                <h2>Entrar com invite code</h2>
              </div>
              <label className="form-field">
                Codigo de convite
                <input
                  type="text"
                  value={joinCode}
                  onChange={(event) => setJoinCode(event.target.value)}
                  placeholder="XXXX-XXXX-XXXX"
                />
              </label>
              <button type="submit" className="primary-btn ghost">
                Enviar pedido
              </button>
            </form>
          </div>
        </header>

        <section className="groups-grid">
          <article className="panel-card groups-detail-card">
            <div className="card-header group-detail-header">
              <div>
                <h2>{selectedGroup ? selectedGroup.name : 'Detalhes do grupo'}</h2>
              </div>
              <div className="detail-header-meta">
                {selectedGroup && (
                  <button
                    type="button"
                    className="details-icon-btn"
                    aria-label="Detalhes do grupo"
                    onClick={() => setGroupActionsOpen(true)}
                  >
                    ...
                  </button>
                )}
              </div>
            </div>

            {!selectedGroup ? (
              <div className="empty-state">Seleciona um grupo para ver os detalhes.</div>
            ) : (
              <>
                <div className="group-summary">
                  {selectedGroup && (
                    <span className={`role-pill ${normalizeRole(selectedGroup.role)}`}>
                      {normalizeRole(selectedGroup.role) === 'owner' ? 'Owner' : 'Member'}
                    </span>
                  )}
                  <div className="group-meta-left">
                    <span className="meta-label">Membros</span>
                    <span className="summary-value">{selectedGroup.members_count ?? members.length}</span>
                  </div>
                  {selectedGroup.invite_code && userIsOwner && (
                    <div className="group-meta-right">
                      <span className="meta-label">Invite code</span>
                      <div className="summary-code">
                        <span className="summary-value code">{selectedGroup.invite_code}</span>
                        <button
                          type="button"
                          className="ghost-btn icon-btn"
                          onClick={() => handleCopyInviteCode(selectedGroup.invite_code)}
                          aria-label="Copiar codigo de convite"
                          title="Copiar codigo"
                        >
                          <span className="icon-copy" aria-hidden="true" />
                        </button>
                      </div>
                    </div>
                  )}
                </div>

                <div className="group-documents">
                  <div className="card-header compact">
                    <h3>Historico do grupo</h3>
                    <div className="detail-header-meta">
                      <span className="chip">{filteredGroupDocs.length}</span>
                      <button
                        type="button"
                        className="primary-btn ghost group-upload-btn"
                        onClick={() => setShowGroupUpload(true)}
                      >
                        Upload PDF
                      </button>
                    </div>
                  </div>
                <div className="group-doc-filters">
                  <div className="search-field">
                    <input
                      type="text"
                      placeholder="Search by name"
                      value={groupSearchTerm}
                      onChange={(e) => setGroupSearchTerm(e.target.value)}
                      aria-label="Pesquisar por nome"
                    />
                    <button
                      className="search-icon-btn"
                      type="button"
                      aria-label="Pesquisar"
                      onClick={() => {}}
                    />
                  </div>
                    <button
                      className="pill-btn"
                      type="button"
                      onClick={() => setGroupSortOrder((prev) => (prev === 'asc' ? 'desc' : 'asc'))}
                    >
                      Date {groupSortOrder === 'asc' ? '▲' : '▼'}
                    </button>
                  <select
                    className="filter-select"
                    value={groupStateFilter}
                    onChange={(event) => setGroupStateFilter(event.target.value)}
                    aria-label="Filtrar por estado"
                  >
                    <option value="" disabled>
                      Estado
                    </option>
                    {stateFilterOptions.map((option) => (
                      <option key={option.value} value={option.value}>
                        {option.label}
                      </option>
                    ))}
                    <option value="all">Todos</option>
                  </select>
                  <select
                    className="filter-select"
                    value={groupClassificationFilter}
                    onChange={(event) => setGroupClassificationFilter(event.target.value)}
                    aria-label="Filtrar por classificacao"
                  >
                    <option value="" disabled>
                      Classificacoes
                    </option>
                    {groupClassificationOptions.map((label) => (
                      <option key={label} value={label}>
                        {label}
                      </option>
                    ))}
                    <option value="all">Todos</option>
                  </select>
                </div>

                  {groupDocsLoading ? (
                    <div className="empty-state">A carregar documentos...</div>
                  ) : groupDocsError ? (
                    <div className="empty-state error">{groupDocsError}</div>
                  ) : filteredGroupDocs.length === 0 ? (
                    <div className="empty-state">Sem uploads neste grupo.</div>
                  ) : (
                    <div className="group-doc-list">
                      {pagedGroupDocs.map((doc) => {
                        const uploadedAt = doc.created_at || doc.uploaded_at;
                        const uploaded = uploadedAt
                          ? new Date(uploadedAt).toLocaleString()
                          : 'Data nao disponivel';
                        const statusText = doc.state || doc.status || 'Pendente';
                        const statusKey = statusText.toLowerCase().replace(/\s+/g, '-');

                        return (
                          <Link key={doc.id} to={`/documents/${doc.id}`} className="group-doc-row">
                            <div>
                              <p className="group-doc-name">{doc.title || doc.filename}</p>
                              <span className="meta-text">
                                {doc.uploaded_by ? `Enviado por ${doc.uploaded_by} • ` : ''}
                                {`Enviado em ${uploaded}`}
                              </span>
                            </div>
                            <span className={`status-pill status-${statusKey}`}>{statusText}</span>
                          </Link>
                        );
                      })}
                    </div>
                  )}
                  {filteredGroupDocs.length > GROUP_PAGE_SIZE && (
                    <div className="group-doc-pagination">
                      <button
                        type="button"
                        className="ghost-btn"
                        onClick={() => setGroupPage((prev) => Math.max(1, prev - 1))}
                        disabled={clampedGroupPage === 1}
                      >
                        Anterior
                      </button>
                      <span className="meta-text">
                        Pagina {clampedGroupPage} de {totalGroupPages}
                      </span>
                      <button
                        type="button"
                        className="ghost-btn"
                        onClick={() => setGroupPage((prev) => Math.min(totalGroupPages, prev + 1))}
                        disabled={clampedGroupPage === totalGroupPages}
                      >
                        Seguinte
                      </button>
                    </div>
                  )}

                  <input
                    ref={groupFileInputRef}
                    type="file"
                    accept="application/pdf"
                    onChange={handleGroupFileChange}
                    hidden
                  />
                </div>

              </>
            )}
          </article>

          <article className="panel-card groups-list-card">
            <div className="card-header">
              <h2>Os teus grupos</h2>
              <span className="chip">{groups.length} ativos</span>
            </div>

            {groupsLoading ? (
              <div className="empty-state">A carregar grupos...</div>
            ) : groupsError ? (
              <div className="empty-state error">{groupsError}</div>
            ) : groups.length === 0 ? (
              <div className="empty-state">
                Ainda nao estas em nenhum grupo. Cria um novo ou entra com convite.
              </div>
            ) : (
              <div className="groups-list groups-scroll">
                {groups.map((group) => {
                  const isActive = group.id === selectedGroupId;
                  const roleLabel = normalizeRole(group.role) === 'owner' ? 'Owner' : 'Member';
                  return (
                    <button
                      key={group.id}
                      type="button"
                      className={`group-card${isActive ? ' active' : ''}`}
                      onClick={() => setSelectedGroupId(group.id)}
                    >
                      <div>
                        <p className="group-name">{group.name}</p>
                        <div className="group-meta">
                          <span className={`role-pill ${roleLabel.toLowerCase()}`}>{roleLabel}</span>
                          <span className="count-pill">{group.members_count ?? 0} membros</span>
                        </div>
                      </div>
                      {normalizeRole(group.role) === 'owner' && group.invite_code && (
                        <div className="invite-code">
                          <span>{group.invite_code}</span>
                        </div>
                      )}
                    </button>
                  );
                })}
              </div>
            )}
          </article>
        </section>

        <section className="groups-secondary">
          <article className="panel-card">
            <div className="card-header">
              <h2>Convites pendentes</h2>
            </div>
            {invitesLoading ? (
              <div className="empty-state">A carregar convites...</div>
            ) : invitesError ? (
              <div className="empty-state error">{invitesError}</div>
            ) : invites.length === 0 ? (
              <div className="empty-state">Sem convites pendentes.</div>
            ) : (
              <div className="members-list">
                {invites.map((invite) => (
                  <div key={invite.id} className="member-row">
                    <div>
                      <p className="member-email">{invite.group_name}</p>
                      <span className="meta-text">Convidado por {invite.invited_by_email}</span>
                    </div>
                    <div className="member-actions">
                      <button
                        type="button"
                        className="ghost-btn success"
                        onClick={() => handleAcceptInvite(invite.id)}
                      >
                        Aceitar
                      </button>
                      <button
                        type="button"
                        className="ghost-btn danger"
                        onClick={() => handleDeclineInvite(invite.id)}
                      >
                        Recusar
                      </button>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </article>
        </section>
      </main>

      {confirmDialog && (
        <div className="modal-backdrop" role="presentation" onClick={() => setConfirmDialog(null)}>
          <div
            className="modal-card"
            role="dialog"
            aria-modal="true"
            onClick={(event) => event.stopPropagation()}
          >
            <div className="modal-header">
              <div>
                <h2>{confirmDialog.type === 'remove' ? 'Confirmar expulsao de membro' : 'Confirmar saida'}</h2>
                <p className="modal-sub">
                  {confirmDialog.type === 'remove'
                    ? `Vais expulsar ${confirmDialog.memberEmail || 'este membro'} do grupo.`
                    : userIsOwner
                      ? 'Ao sair, o grupo sera eliminado para sempre e todos os membros removidos.'
                      : 'Ao sair, deixas de ter acesso a este grupo.'}
                </p>
              </div>
              <button
                type="button"
                className="modal-close"
                onClick={() => setConfirmDialog(null)}
                aria-label="Fechar"
              >
                x
              </button>
            </div>
            <div className="modal-actions">
              <button type="button" className="ghost-btn" onClick={() => setConfirmDialog(null)}>
                Cancelar
              </button>
              <button type="button" className="danger-btn" onClick={handleConfirmAction}>
                Confirmar
              </button>
            </div>
          </div>
        </div>
      )}

      {groupActionsOpen && selectedGroup && (
        <div className="modal-backdrop" role="presentation" onClick={() => setGroupActionsOpen(false)}>
          <div
            className="modal-card group-actions-modal"
            role="dialog"
            aria-modal="true"
            onClick={(event) => event.stopPropagation()}
          >
            <div className="modal-header">
              <div>
                <h2>Detalhes do grupo</h2>
                <p className="modal-sub">Gere membros, convites e pedidos de entrada.</p>
              </div>
              <button
                type="button"
                className="modal-close"
                onClick={() => setGroupActionsOpen(false)}
                aria-label="Fechar"
              >
                x
              </button>
            </div>

            <div className="members-block">
              <div className="card-header compact">
                <h3>Lista de membros</h3>
                <button type="button" className="ghost-btn danger" onClick={openLeaveGroupDialog}>
                  Sair do grupo
                </button>
              </div>
              {membersLoading ? (
                <div className="empty-state">A carregar membros...</div>
              ) : membersError ? (
                <div className="empty-state error">{membersError}</div>
              ) : members.length === 0 ? (
                <div className="empty-state">Sem membros encontrados.</div>
              ) : (
                <div className="members-scroll">
                  <div className="members-list">
                    {members.map((member) => (
                      <div key={member.id} className="member-row">
                        <div>
                          <p className="member-email">{member.email}</p>
                          <span className="role-pill small">
                            {normalizeRole(member.role) === 'owner' ? 'Owner' : 'Member'}
                          </span>
                        </div>
                        {userIsOwner && (
                          <div className="member-actions">
                            {normalizeRole(member.role) === 'owner' ? (
                              <button
                                type="button"
                                className="ghost-btn"
                                onClick={() => handleDemoteOwner(member.id)}
                              >
                                Rebaixar owner
                              </button>
                            ) : (
                              <button
                                type="button"
                                className="ghost-btn"
                                onClick={() => handlePromoteOwner(member.id)}
                              >
                                Promover a owner
                              </button>
                            )}
                            <button
                              type="button"
                              className="ghost-btn danger"
                              onClick={() => openRemoveMemberDialog(member)}
                            >
                              Expulsar
                            </button>
                          </div>
                        )}
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>

            {userIsOwner && (
              <form className="invite-block" onSubmit={handleInviteMember}>
                <div className="card-header compact">
                  <h3>Convidar membro</h3>
                </div>
                <label className="form-field">
                  Email do convidado
                  <input
                    type="email"
                    value={inviteEmail}
                    onChange={(event) => setInviteEmail(event.target.value)}
                    placeholder="membro@empresa.com"
                  />
                </label>
                <button type="submit" className="primary-btn">
                  Enviar convite
                </button>
              </form>
            )}

            {userIsOwner && (
              <div className="requests-block">
                <div className="card-header compact">
                  <h3>Pedidos de entrada</h3>
                </div>
                {requestsLoading ? (
                  <div className="empty-state">A carregar pedidos...</div>
                ) : requestsError ? (
                  <div className="empty-state error">{requestsError}</div>
                ) : joinRequests.length === 0 ? (
                  <div className="empty-state">Sem pedidos pendentes.</div>
                ) : (
                  <div className="members-list">
                    {joinRequests.map((request) => (
                      <div key={request.id} className="member-row">
                        <div>
                          <p className="member-email">{request.user_email}</p>
                          <span className="meta-text">
                            Pedido em {new Date(request.created_at).toLocaleString()}
                          </span>
                        </div>
                        <div className="member-actions">
                          <button
                            type="button"
                            className="ghost-btn"
                            onClick={() => handleApproveRequest(request.id)}
                          >
                            Aprovar
                          </button>
                          <button
                            type="button"
                            className="ghost-btn"
                            onClick={() => handleRejectRequest(request.id)}
                          >
                            Recusar
                          </button>
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            )}
          </div>
        </div>
      )}

      {showGroupUpload && (
        <div className="upload-backdrop" role="presentation" onClick={() => setShowGroupUpload(false)}>
          <div
            className="upload-modal"
            role="dialog"
            aria-modal="true"
            onClick={(event) => event.stopPropagation()}
          >
            {groupUploadError && <div className="upload-error">{groupUploadError}</div>}
            <div
              className={`upload-dropzone${groupIsDragging ? ' is-dragging' : ''}`}
              onClick={handleSelectGroupFile}
              onDrop={handleGroupDrop}
              onDragOver={handleGroupDragOver}
              onDragEnter={handleGroupDragEnter}
              onDragLeave={handleGroupDragLeave}
            >
              <div className="upload-icon" aria-hidden="true">
                <span>PDF</span>
                <div className="upload-arrow">-&gt;</div>
              </div>
              {groupUploadFile ? (
                <>
                  <p className="upload-title">Ficheiro pronto para enviar</p>
                  <p className="upload-sub">Vamos analisar e classificar o documento.</p>
                  <p className="upload-file">{groupUploadFile.name}</p>
                  <div className="upload-actions">
                    <button
                      type="button"
                      className="upload-send"
                      onClick={(event) => {
                        event.stopPropagation();
                        handleGroupUpload();
                      }}
                      disabled={groupUploading}
                    >
                      {groupUploading ? 'A enviar...' : 'Enviar para classificacao'}
                    </button>
                  </div>
                </>
              ) : (
                <>
                  <p className="upload-title">Arraste e solte o ficheiro aqui</p>
                  <p className="upload-sub">ou clique para selecionar o seu ficheiro</p>
                </>
              )}
              <input
                ref={groupFileInputRef}
                type="file"
                accept="application/pdf"
                onChange={handleGroupFileChange}
                hidden
              />
            </div>
          </div>
        </div>
      )}

      <DynamicToast toasts={toasts} onDismiss={dismissToast} />
    </div>
  );
}

export default GroupsPage;
