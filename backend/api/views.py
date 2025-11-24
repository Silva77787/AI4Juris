from django.contrib.auth import authenticate, get_user_model
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from rest_framework_simplejwt.tokens import RefreshToken

from .models import Group, GroupMembership
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
def register(request):
    data = request.data
    email = data.get("email")
    password = data.get("password")
    name = data.get("name", "")

    # Validação
    if not email or not password:
        return Response(
            {"error": "Email e password obrigatórios"},
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



# --- DOCUMENTOS / HISTÓRICO ---

@api_view(['GET'])
def list_documents(request):
    """
    Lista de documentos para a tua Home / Histórico.
    Neste momento dados estáticos só para testar o frontend.
    """
    documents = [
        {
            "id": 1,
            "title": "Acórdão 1",
            "filename": "acordao_1.pdf",
            "uploaded_at": "2025-11-10T12:00:00Z",
            "status": "processed",
            "labels": ["Direito Penal", "Recurso"],
        },
        {
            "id": 2,
            "title": "Acórdão 2",
            "filename": "acordao_2.pdf",
            "uploaded_at": "2025-11-11T09:30:00Z",
            "status": "processing",
            "labels": [],
        },
    ]
    return Response(documents)


@api_view(['POST'])
def upload_document(request):
    """
    Endpoint de upload simplificado.
    Por agora assume que recebes JSON (title, description, etc.)
    Mais tarde mudamos para multipart com ficheiro real.
    """
    data = request.data
    created = {
        "id": 3,
        "title": data.get("title", "Documento sem título"),
        "filename": data.get("filename", "ficheiro.pdf"),
        "uploaded_at": "2025-11-15T10:00:00Z",
        "status": "processing",
        "labels": [],
    }
    return Response(created, status=status.HTTP_201_CREATED)


# --- GRUPOS ---
# -----------------------------
# Criar grupo
# -----------------------------
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def create_group(request):
    name = request.data.get("name")

    if not name:
        return Response({"error": "Nome do grupo é obrigatório"}, status=400)

    # Criar grupo
    group = Group.objects.create(
        name=name,
        owner=request.user
    )

    # Adicionar criador como único owner
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


# -----------------------------
# Listar grupos do utilizador
# -----------------------------
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def my_groups(request):
    memberships = GroupMembership.objects.filter(user=request.user)

    groups = [
        {
            "id": m.group.id,
            "name": m.group.name,
            "role": m.role,
            "members_count": GroupMembership.objects.filter(group=m.group).count(),
            "invite_code": str(m.group.invite_code) if m.role == "owner" else None,
        }
        for m in memberships
    ]

    return Response(groups)


# -----------------------------
# Listar membros de um grupo
# -----------------------------
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def group_members(request, group_id):
    group = get_object_or_404(Group, id=group_id)

    # Verificar se o utilizador pertence ao grupo
    if not GroupMembership.objects.filter(group=group, user=request.user).exists():
        return Response({"error": "Não pertence a este grupo"}, status=403)

    members = GroupMembership.objects.filter(group=group)

    return Response([
        {
            "id": m.user.id,
            "email": m.user.email,
            "role": m.role,
        }
        for m in members
    ])


# -----------------------------
# Convidar membro por email
# -----------------------------
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def invite_member(request, group_id):
    email = request.data.get("email")
    if not email:
        return Response({"error": "Email é obrigatório"}, status=400)

    group = get_object_or_404(Group, id=group_id)

    # Só owner ou admin podem convidar
    acting = GroupMembership.objects.get(user=request.user, group=group)
    if acting.role not in ("owner", "admin"):
        return Response({"error": "Sem permissões"}, status=403)

    try:
        invited_user = User.objects.get(email=email)
    except User.DoesNotExist:
        return Response({"error": "Utilizador não encontrado"}, status=404)

    GroupMembership.objects.get_or_create(
        user=invited_user,
        group=group,
        defaults={"role": "member"}
    )

    return Response({"message": f"{email} foi adicionado ao grupo."})


# -----------------------------
# Entrar num grupo via código de convite (QR CODE)
# -----------------------------
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def join_group(request, invite_code):
    group = get_object_or_404(Group, invite_code=invite_code)

    GroupMembership.objects.get_or_create(
        user=request.user,
        group=group,
        defaults={"role": "member"}
    )

    return Response({"message": f"Entrou no grupo {group.name}", "id": group.id})


# -----------------------------
# Promover admin (apenas owner)
# -----------------------------
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def promote_to_admin(request, group_id, user_id):

    group = get_object_or_404(Group, id=group_id)

    acting = GroupMembership.objects.get(group=group, user=request.user)
    if acting.role != "owner":
        return Response({"error": "Apenas o owner pode promover admins"}, status=403)

    member = GroupMembership.objects.get(group=group, user_id=user_id)

    if member.role == "owner":
        return Response({"error": "O owner não pode ser modificado."}, status=400)

    member.role = "admin"
    member.save()

    return Response({"message": "Utilizador promovido a admin."})


# -----------------------------
# Rebaixar admin para member (apenas owner)
# -----------------------------
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def demote_to_member(request, group_id, user_id):
    group = get_object_or_404(Group, id=group_id)

    acting = GroupMembership.objects.get(group=group, user=request.user)
    if acting.role != "owner":
        return Response({"error": "Apenas o owner pode alterar permissões"}, status=403)

    member = GroupMembership.objects.get(group=group, user_id=user_id)

    if member.role == "owner":
        return Response({"error": "O owner não pode ser despromovido."}, status=400)

    member.role = "member"
    member.save()

    return Response({"message": "Permissões removidas: utilizador agora é membro."})
