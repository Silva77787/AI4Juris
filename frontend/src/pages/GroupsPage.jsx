// src/pages/GroupsPage.jsx
import { useEffect, useMemo, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import TopBar from '../components/TopBar.jsx';
import DynamicToast from './DynamicToast.jsx';
import '../styles/HomePage.css';
import '../styles/GroupsPage.css';

const API_BASE = 'http://localhost:7777';

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

  const [createName, setCreateName] = useState('');
  const [inviteEmail, setInviteEmail] = useState('');
  const [joinCode, setJoinCode] = useState('');
  const [toasts, setToasts] = useState([]);
  const [confirmDialog, setConfirmDialog] = useState(null);

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

    return fetch(`${API_BASE}${path}`, {
      headers: {
        'Content-Type': 'application/json',
        Authorization: `Bearer ${token}`,
        ...(options.headers || {}),
      },
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
    } else {
      setMembers([]);
    }
  }, [selectedGroupId]);

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
              <div className="groups-list">
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

          <article className="panel-card groups-detail-card">
            <div className="card-header">
              <h2>{selectedGroup ? selectedGroup.name : 'Detalhes do grupo'}</h2>
              {selectedGroup && (
                <span className="chip">
                  {normalizeRole(selectedGroup.role) === 'owner' ? 'Owner' : 'Member'}
                </span>
              )}
            </div>

            {!selectedGroup ? (
              <div className="empty-state">Seleciona um grupo para ver os detalhes.</div>
            ) : (
              <>
                <div className="group-summary">
                  <div>
                    <p className="summary-label">Membros</p>
                    <p className="summary-value">{selectedGroup.members_count ?? members.length}</p>
                  </div>
                  {selectedGroup.invite_code && userIsOwner && (
                    <div>
                      <p className="summary-label">Invite code</p>
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
              </>
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
                        className="ghost-btn"
                        onClick={() => handleAcceptInvite(invite.id)}
                      >
                        Aceitar
                      </button>
                      <button
                        type="button"
                        className="ghost-btn"
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

      <DynamicToast toasts={toasts} onDismiss={dismissToast} />
    </div>
  );
}

export default GroupsPage;
