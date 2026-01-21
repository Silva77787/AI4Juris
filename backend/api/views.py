from django.utils import timezone
from django.contrib.auth import authenticate, get_user_model
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from django.views.decorators.csrf import csrf_exempt
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from .models import Document, Prediction, Explanation, Metric
from .serializers import DocumentDetailSerializer
from rest_framework_simplejwt.tokens import RefreshToken

from .models import Group, GroupInvite, GroupMembership, JoinRequest
from django.shortcuts import get_object_or_404

User = get_user_model()


# Função para gerar tokens JWT para um utilizador
def get_tokens_for_user(user):
    refresh = RefreshToken.for_user(user)
    return {
        'refresh': str(refresh),
        'access': str(refresh.access_token),
    }


@api_view(['POST'])
@csrf_exempt
def register(request):
    data = request.data
    email = data.get("email")
    password = data.get("password")
    confirm_password = data.get("confirm_password")
    name = data.get("name", "")

    # Validação
    if not email or not password:
        return Response(
            {"error": "Email e password obrigatórios"},
            status=status.HTTP_400_BAD_REQUEST
        )

    if confirm_password is None or password != confirm_password:
        return Response(
            {"error": "As passwords não coincidem"},
            status=status.HTTP_400_BAD_REQUEST
        )

    if User.objects.filter(email=email).exists():
        return Response(
            {"error": "Email já registado"},
            status=status.HTTP_400_BAD_REQUEST
        )

    # Criar utilizador
    user = User.objects.create_user(
        username=email, 
        email=email, 
        password=password, 
        first_name=name
    )

    # Gerar tokens
    tokens = get_tokens_for_user(user)

    return Response({
        "id": user.id,
        "name": user.first_name,
        "email": user.email,
        "tokens": tokens
    }, status=status.HTTP_201_CREATED)


@api_view(['POST'])
@csrf_exempt
def login(request):
    data = request.data
    email = data.get("email")
    password = data.get("password")

    # Validação
    if not email or not password:
        return Response(
            {"error": "Email e password obrigatórios"},
            status=status.HTTP_400_BAD_REQUEST
        )

    # Autenticação
    user = authenticate(username=email, password=password)

    if user is None:
        return Response(
            {"error": "Credenciais inválidas"},
            status=status.HTTP_401_UNAUTHORIZED
        )

    # Gerar tokens
    tokens = get_tokens_for_user(user)

    return Response({
        "id": user.id,
        "name": user.first_name,
        "email": user.email,
        "tokens": tokens
    }, status=status.HTTP_200_OK)


# --- PERFIL ---

@api_view(['GET', 'PATCH'])
@permission_classes([IsAuthenticated])

def profile(request):
    user = request.user

    if request.method == 'GET':
        return Response({
            "id": user.id,
            "name": user.first_name,
            "email": user.email,
        }, status=status.HTTP_200_OK)

    data = request.data
    name = data.get("name")
    email = data.get("email")
    current_password = data.get("current_password")
    new_password = data.get("new_password")
    confirm_password = data.get("confirm_password")

    name_changed = name is not None and name != user.first_name
    email_changed = email is not None and email != user.email

    if name_changed or email_changed:
        if not current_password:
            return Response({"error": "Password atual obrigatória"}, status=status.HTTP_400_BAD_REQUEST)
        if not user.check_password(current_password):
            return Response({"error": "Password atual incorreta"}, status=status.HTTP_400_BAD_REQUEST)

    if email and email != user.email:
        if User.objects.filter(email=email).exclude(pk=user.pk).exists():
            return Response({"error": "Email já registado"}, status=status.HTTP_400_BAD_REQUEST)
        user.email = email
        user.username = email

    if name is not None:
        user.first_name = name

    if new_password or confirm_password:
        if not current_password:
            return Response({"error": "Password atual obrigatória"}, status=status.HTTP_400_BAD_REQUEST)
        if not user.check_password(current_password):
            return Response({"error": "Password atual incorreta"}, status=status.HTTP_400_BAD_REQUEST)
        if new_password != confirm_password:
            return Response({"error": "As passwords não coincidem"}, status=status.HTTP_400_BAD_REQUEST)
        user.set_password(new_password)

    user.save()

    return Response({
        "id": user.id,
        "name": user.first_name,
        "email": user.email,
    }, status=status.HTTP_200_OK)


# --- DOCUMENTOS / HISTORICO ---

def _serialize_document_summary(document):
    return {
        "id": document.id,
        "title": document.filename,
        "filename": document.filename,
        "created_at": document.created_at,
        "state": document.state,
        "n_descriptors": document.n_descriptors,
        "error_msg": document.error_msg,
        "uploaded_by": document.user.email,
        "group_id": document.group_id,
    }


def _is_group_member(user, group):
    return GroupMembership.objects.filter(group=group, user=user).exists()


def _can_access_document(user, document):
    if document.group_id:
        return _is_group_member(user, document.group)
    return document.user_id == user.id


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def list_documents(request):
    documents = (
        Document.objects.filter(user=request.user, group__isnull=True)
        .order_by('-created_at')
    )
    return Response([_serialize_document_summary(doc) for doc in documents])


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def upload_document(request):
    uploaded_file = request.FILES.get("file")
    if not uploaded_file:
        return Response({"error": "Ficheiro em falta."}, status=status.HTTP_400_BAD_REQUEST)

    document = Document.objects.create(
        user=request.user,
        file=uploaded_file,
        filename=uploaded_file.name,
        state="QUEUED",
    )

    print("Storage class:", document.file.storage.__class__)
    print("File name:", document.file.name)
    print("File URL:", document.file.url)

    return Response({
        "id": document.id,
        "url": document.file.url,
        "filename": document.filename,
        "state": document.state,
    })


# --- DETALHES ---

#Possivel codigo correto

#@api_view(["GET"])
#@permission_classes([IsAuthenticated])
#def document_detail(request, pk):
#    try:
#        doc = Document.objects.get(pk=pk, user=request.user)
#    except Document.DoesNotExist:
#        return Response({"error": "Documento não encontrado"}, status=404)
#    serializer = DocumentDetailSerializer(doc)
#    return Response(serializer.data)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def document_detail(request, pk):
    document = get_object_or_404(Document, pk=pk)
    if not _can_access_document(request.user, document):
        return Response({"detail": "Documento nao encontrado."}, status=404)
    serializer = DocumentDetailSerializer(document)
    return Response(serializer.data)

# --- GRUPOS ---

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def create_group(request):
    name = request.data.get("name")
    if not name:
        return Response({"error": "Nome do grupo é obrigatório"}, status=400)

    name = name.strip()
    if Group.objects.filter(name__iexact=name).exists():
        return Response({"error": "Já existe um grupo com esse nome"}, status=400)

    group = Group.objects.create(name=name, owner=request.user)

    GroupMembership.objects.create(
        user=request.user,
        group=group,
        role="owner"
    )

    return Response({
        "id": group.id,
        "name": group.name,
        "invite_code": str(group.invite_code),
        "owner": request.user.email
    }, status=201)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def my_groups(request):
    memberships = GroupMembership.objects.filter(user=request.user).select_related("group")
    groups = []
    for m in memberships:
        groups.append({
            "id": m.group.id,
            "name": m.group.name,
            "role": m.role,
            "members_count": GroupMembership.objects.filter(group=m.group).count(),
            "invite_code": str(m.group.invite_code) if m.role == "owner" else None,
        })
    return Response(groups)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def group_members(request, group_id):
    group = get_object_or_404(Group, id=group_id)

    if not GroupMembership.objects.filter(group=group, user=request.user).exists():
        return Response({"error": "Não pertence a este grupo"}, status=403)

    members = GroupMembership.objects.filter(group=group).select_related("user").order_by("created_at")

    return Response([
        {"id": m.user.id, "email": m.user.email, "role": m.role}
        for m in members
    ])


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def list_group_documents(request, group_id):
    group = get_object_or_404(Group, id=group_id)
    if not _is_group_member(request.user, group):
        return Response({"error": "Nao pertence a este grupo"}, status=403)

    documents = Document.objects.filter(group=group).order_by('-created_at')
    return Response([_serialize_document_summary(doc) for doc in documents])


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def upload_group_document(request, group_id):
    group = get_object_or_404(Group, id=group_id)
    if not _is_group_member(request.user, group):
        return Response({"error": "Nao pertence a este grupo"}, status=403)

    uploaded_file = request.FILES.get("file")
    if not uploaded_file:
        return Response({"error": "Ficheiro em falta."}, status=status.HTTP_400_BAD_REQUEST)

    filename = request.data.get("filename") or uploaded_file.name
    document = Document.objects.create(
        user=request.user,
        group=group,
        file=uploaded_file,
        filename=filename,
        state="QUEUED",
    )
    return Response(_serialize_document_summary(document), status=status.HTTP_201_CREATED)


def _require_owner(user, group):
    membership = get_object_or_404(GroupMembership, user=user, group=group)
    if membership.role != "owner":
        return None
    return membership


# -----------------------------
# Convidar membro por email
# NOVA REGRA: cria convite PENDING; convidado aceita/recusa.
# -----------------------------
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def invite_member(request, group_id):
    email = request.data.get("email")
    if not email:
        return Response({"error": "Email é obrigatório"}, status=400)

    group = get_object_or_404(Group, id=group_id)

    if _require_owner(request.user, group) is None:
        return Response({"error": "Apenas owners podem convidar membros"}, status=403)

    invited_user = User.objects.filter(email=email).first()
    if not invited_user:
        return Response({"error": "Utilizador não encontrado"}, status=404)

    if GroupMembership.objects.filter(group=group, user=invited_user).exists():
        return Response({"error": "Este utilizador já pertence ao grupo"}, status=400)

    invite, created = GroupInvite.objects.get_or_create(
        group=group,
        invited_user=invited_user,
        defaults={"invited_by": request.user, "status": "PENDING"}
    )

    if not created:
        if invite.status == "PENDING":
            return Response({"error": "Já existe um convite pendente para este utilizador"}, status=400)
        # Reabrir convite se estava recusado (ou aceite mas sem membership por algum bug)
        invite.status = "PENDING"
        invite.invited_by = request.user
        invite.responded_at = None
        invite.save()

    return Response({"message": "Convite enviado", "invite_id": invite.id}, status=201)


# -----------------------------
# Listar convites pendentes do utilizador (inbox)
# -----------------------------
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def my_invites(request):
    invites = GroupInvite.objects.filter(invited_user=request.user, status="PENDING").select_related("group", "invited_by")
    return Response([
        {
            "id": i.id,
            "group_id": i.group.id,
            "group_name": i.group.name,
            "invited_by_email": i.invited_by.email,
            "created_at": i.created_at,
            "status": i.status,
        }
        for i in invites
    ])


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def accept_invite(request, invite_id):
    invite = get_object_or_404(GroupInvite, id=invite_id, invited_user=request.user, status="PENDING")

    if GroupMembership.objects.filter(group=invite.group, user=request.user).exists():
        invite.status = "ACCEPTED"
        invite.responded_at = timezone.now()
        invite.save()
        return Response({"message": "Já pertences ao grupo"}, status=200)

    GroupMembership.objects.create(
        user=request.user,
        group=invite.group,
        role="member"
    )

    invite.status = "ACCEPTED"
    invite.responded_at = timezone.now()
    invite.save()

    return Response({"message": f"Convite aceite. Entraste no grupo {invite.group.name}", "group_id": invite.group.id})


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def decline_invite(request, invite_id):
    invite = get_object_or_404(GroupInvite, id=invite_id, invited_user=request.user, status="PENDING")
    invite.status = "DECLINED"
    invite.responded_at = timezone.now()
    invite.save()
    return Response({"message": "Convite recusado"})


# -----------------------------
# Entrar via invite_code (QR)
# NOVA REGRA: cria JoinRequest PENDING; um owner aprova/recusa.
# -----------------------------
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def join_group(request, invite_code):
    group = get_object_or_404(Group, invite_code=invite_code)

    if GroupMembership.objects.filter(group=group, user=request.user).exists():
        return Response({"error": "Já pertence ao grupo"}, status=400)

    jr, created = JoinRequest.objects.get_or_create(
        group=group,
        user=request.user,
        defaults={"status": "PENDING"}
    )

    if not created:
        if jr.status == "PENDING":
            return Response({"message": "Já tens um pedido pendente", "request_id": jr.id}, status=200)
        jr.status = "PENDING"
        jr.decided_by = None
        jr.decided_at = None
        jr.save()

    return Response({"message": "Pedido de entrada enviado para aprovação de um owner", "request_id": jr.id}, status=201)


# -----------------------------
# Owners: listar pedidos pendentes do grupo
# -----------------------------
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def list_join_requests(request, group_id):
    group = get_object_or_404(Group, id=group_id)

    if _require_owner(request.user, group) is None:
        return Response({"error": "Apenas owners podem ver pedidos"}, status=403)

    reqs = JoinRequest.objects.filter(group=group, status="PENDING").select_related("user").order_by("created_at")

    return Response([
        {
            "id": r.id,
            "user_id": r.user.id,
            "user_email": r.user.email,
            "created_at": r.created_at,
            "status": r.status,
        }
        for r in reqs
    ])


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def approve_join_request(request, request_id):
    jr = get_object_or_404(JoinRequest, id=request_id, status="PENDING")
    group = jr.group

    if _require_owner(request.user, group) is None:
        return Response({"error": "Apenas owners podem aprovar pedidos"}, status=403)

    if not GroupMembership.objects.filter(group=group, user=jr.user).exists():
        GroupMembership.objects.create(user=jr.user, group=group, role="member")

    jr.status = "ACCEPTED"
    jr.decided_by = request.user
    jr.decided_at = timezone.now()
    jr.save()

    return Response({"message": "Pedido aprovado. Utilizador adicionado ao grupo.", "group_id": group.id})


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def reject_join_request(request, request_id):
    jr = get_object_or_404(JoinRequest, id=request_id, status="PENDING")
    group = jr.group

    if _require_owner(request.user, group) is None:
        return Response({"error": "Apenas owners podem recusar pedidos"}, status=403)

    jr.status = "DECLINED"
    jr.decided_by = request.user
    jr.decided_at = timezone.now()
    jr.save()

    return Response({"message": "Pedido recusado"})


# -----------------------------
# Promover a owner (apenas owner)
# (mantém as regras antigas: max 2 owners)
# -----------------------------
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def promote_to_owner(request, group_id, user_id):
    group = get_object_or_404(Group, id=group_id)

    requester = get_object_or_404(GroupMembership, group=group, user=request.user)
    if requester.role != "owner":
        return Response({"error": "Apenas owners podem promover outros membros"}, status=403)

    owners_count = GroupMembership.objects.filter(group=group, role="owner").count()
    if owners_count >= 2:
        return Response({"error": "O grupo já tem o número máximo de owners (2)"}, status=400)

    target = get_object_or_404(GroupMembership, group=group, user_id=user_id)
    if target.role == "owner":
        return Response({"error": "O utilizador já é owner"}, status=400)

    target.role = "owner"
    target.save()

    return Response({"message": "Utilizador promovido a owner com sucesso"})


# -----------------------------
# Rebaixar owner para member (apenas owner mais antigo)
# -----------------------------
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def demote_owner(request, group_id, user_id):
    group = get_object_or_404(Group, id=group_id)

    requester = get_object_or_404(GroupMembership, group=group, user=request.user)
    if requester.role != "owner":
        return Response({"error": "Apenas owners podem executar esta ação"}, status=403)

    owners = GroupMembership.objects.filter(group=group, role="owner").order_by("created_at")
    if owners.count() <= 1:
        return Response({"error": "O grupo tem de ter pelo menos um owner"}, status=400)

    oldest_owner = owners.first()
    if requester != oldest_owner:
        return Response({"error": "Apenas o owner mais antigo pode rebaixar outro owner"}, status=403)

    target = get_object_or_404(GroupMembership, group=group, user_id=user_id)
    if target.role != "owner":
        return Response({"error": "O utilizador não é owner"}, status=400)

    target.role = "member"
    target.save()

    return Response({"message": "Owner rebaixado para member com sucesso"})


# -----------------------------
# Remover membro do grupo (expulsar)
# -----------------------------
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def remove_member(request, group_id, user_id):
    group = get_object_or_404(Group, id=group_id)

    requester = get_object_or_404(GroupMembership, group=group, user=request.user)
    if requester.role != "owner":
        return Response({"error": "Apenas owners podem remover membros"}, status=403)

    if request.user.id == user_id:
        return Response({"error": "Não podes remover-te do grupo"}, status=400)

    target = get_object_or_404(GroupMembership, group=group, user_id=user_id)

    if target.role == "owner":
        owners = GroupMembership.objects.filter(group=group, role="owner").order_by("created_at")
        if owners.count() <= 1:
            return Response({"error": "O grupo tem de ter pelo menos um owner"}, status=400)
        oldest_owner = owners.first()
        if requester != oldest_owner:
            return Response({"error": "Apenas o owner mais antigo pode remover outro owner"}, status=403)

    target.delete()
    return Response({"message": "Membro removido do grupo com sucesso"})


# -----------------------------
# Sair do grupo
# - member: remove membership
# - owner: elimina o grupo (e todos os membros)
# -----------------------------
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def leave_group(request, group_id):
    group = get_object_or_404(Group, id=group_id)
    membership = get_object_or_404(GroupMembership, group=group, user=request.user)

    if membership.role == "owner":
        group.delete()
        return Response({"message": "Grupo eliminado com sucesso"})

    membership.delete()
    return Response({"message": "Saíste do grupo com sucesso"})
