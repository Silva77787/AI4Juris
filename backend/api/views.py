from django.contrib.auth import authenticate
from django.contrib.auth import get_user_model
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from .models import Document, Prediction, Explanation, Metric, Notification
from .serializers import DocumentDetailSerializer, NotificationSerializer, NotificationCreateSerializer
from rest_framework_simplejwt.tokens import RefreshToken
from django.utils import timezone

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

    data = [
        {
            "id": 1,
            "filename": "acordao_1.pdf",
            "state": "DONE",
            "text": "Texto extraído do Acórdão 1…",
            "duration_ms": 1800,
            "n_descriptors": 2,
            "error_msg": "",
            "created_at": "2025-11-10T12:00:00Z",
            "updated_at": "2025-11-10T12:05:00Z",
            "predictions": [
                {
                    "id": 1,
                    "descriptor": "Direito Penal",
                    "score": 0.93,
                    "explanations": [
                        {
                            "id": 1,
                            "text_span": "O arguido foi condenado…",
                            "start_offset": 210,
                            "end_offset": 260,
                            "score": 0.89
                        }
                    ]
                },
                {
                    "id": 2,
                    "descriptor": "Recurso",
                    "score": 0.88,
                    "explanations": [
                        {
                            "id": 2,
                            "text_span": "Foi interposto recurso…",
                            "start_offset": 400,
                            "end_offset": 440,
                            "score": 0.90
                        }
                    ]
                }
            ],
            "metrics": [
                { "id": 1, "stage": "OCR", "duration_ms": 500, "created_at": "2025-11-10T12:01:00Z" },
                { "id": 2, "stage": "LLM Processing", "duration_ms": 1100, "created_at": "2025-11-10T12:03:00Z" },
                { "id": 3, "stage": "Post-processing", "duration_ms": 200, "created_at": "2025-11-10T12:04:00Z" }
            ]
        },
        {
            "id": 2,
            "filename": "acordao_2.pdf",
            "state": "PROCESSING",
            "text": "",
            "duration_ms": "",
            "n_descriptors": 0,
            "error_msg": "",
            "created_at": "2025-11-11T09:30:00Z",
            "updated_at": "2025-11-11T09:30:00Z",
            "predictions": [],
            "metrics": []
        }
    ]

    # Procurar o documento com o id solicitado
    document = next((item for item in data if item["id"] == int(pk)), None)

    if not document:
        return Response({"detail": "Documento não encontrado."}, status=404)

    return Response(document)



# --- GRUPOS ---

@api_view(['GET'])
def list_groups(request):
    """
    Lista de grupos para a página /groups.
    """
    groups = [
        {
            "id": 1,
            "name": "Grupo de Trabalho A",
            "members_count": 3,
        },
        {
            "id": 2,
            "name": "Investigação Direito Penal",
            "members_count": 5,
        },
    ]
    return Response(groups)


# --- NOTIFICAÇÕES ---

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def list_notifications(request):
    user = request.user
    notifications = Notification.objects.filter(recipient=user)
    
    is_read_param = request.query_params.get('is_read')
    if is_read_param is not None:
        is_read = is_read_param.lower() == 'true'
        notifications = notifications.filter(is_read=is_read)
    
    serializer = NotificationSerializer(notifications, many=True)
    return Response(serializer.data)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_notification_count(request):
    user = request.user
    unread_count = Notification.objects.filter(recipient=user, is_read=False).count()
    
    return Response({
        "unread_count": unread_count,
        "total_count": Notification.objects.filter(recipient=user).count()
    })


@api_view(['GET', 'PUT'])
@permission_classes([IsAuthenticated])
def notification_detail(request, pk):
    user = request.user
    
    try:
        notification = Notification.objects.get(pk=pk, recipient=user)
    except Notification.DoesNotExist:
        return Response(
            {"error": "Notificação não encontrada"},
            status=status.HTTP_404_NOT_FOUND
        )
    
    if request.method == 'GET':
        serializer = NotificationSerializer(notification)
        return Response(serializer.data)
    
    elif request.method == 'PUT':
        # Marcar como lida
        if not notification.is_read:
            notification.is_read = True
            notification.read_at = timezone.now()
            notification.save()
        
        serializer = NotificationSerializer(notification)
        return Response(serializer.data)


@api_view(['PUT'])
@permission_classes([IsAuthenticated])
def mark_all_notifications_as_read(request):
    user = request.user
    now = timezone.now()
    
    notifications = Notification.objects.filter(recipient=user, is_read=False)
    updated_count = notifications.update(is_read=True, read_at=now)
    
    return Response({
        "message": f"{updated_count} notificações marcadas como lidas",
        "updated_count": updated_count
    })


@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
def delete_notification(request, pk):
    user = request.user
    
    try:
        notification = Notification.objects.get(pk=pk, recipient=user)
    except Notification.DoesNotExist:
        return Response(
            {"error": "Notificação não encontrada"},
            status=status.HTTP_404_NOT_FOUND
        )
    
    notification.delete()
    return Response(
        {"message": "Notificação deletada com sucesso"},
        status=status.HTTP_204_NO_CONTENT
    )


@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
def delete_all_notifications(request):
    user = request.user
    deleted_count, _ = Notification.objects.filter(recipient=user).delete()
    
    return Response({
        "message": f"{deleted_count} notificações deletadas",
        "deleted_count": deleted_count
    })


def create_notification(recipient, notification_type, title, message, document=None, related_user=None):
    notification = Notification.objects.create(
        recipient=recipient,
        notification_type=notification_type,
        title=title,
        message=message,
        document=document,
        related_user=related_user
    )
    return notification


def create_upload_notification(user, document, state):
    state_messages = {
        "QUEUED": {
            "title": "Upload Enfileirado",
            "message": f"O seu documento '{document.filename}' foi enfileirado para processamento.",
            "type": "UPLOAD_QUEUED"
        },
        "PROCESSING": {
            "title": "Processamento em Progresso",
            "message": f"O documento '{document.filename}' está sendo processado. Por favor, aguarde…",
            "type": "UPLOAD_PROCESSING"
        },
        "DONE": {
            "title": "Upload Concluído ✓",
            "message": f"O documento '{document.filename}' foi processado com sucesso! {document.n_descriptors} descritores encontrados.",
            "type": "UPLOAD_DONE"
        },
        "ERROR": {
            "title": "Erro no Processamento",
            "message": f"Erro ao processar '{document.filename}': {document.error_msg}",
            "type": "UPLOAD_ERROR"
        },
        "TIMEOUT": {
            "title": "Tempo Limite Excedido",
            "message": f"O processamento de '{document.filename}' excedeu o tempo limite.",
            "type": "UPLOAD_ERROR"
        }
    }
    
    state_info = state_messages.get(state)
    if state_info:
        create_notification(
            recipient=user,
            notification_type=state_info["type"],
            title=state_info["title"],
            message=state_info["message"],
            document=document
        )


def create_group_invite_notification(recipient, inviter, group_name):
    create_notification(
        recipient=recipient,
        notification_type="GROUP_INVITE",
        title=f"Convite para grupo: {group_name}",
        message=f"{inviter.first_name or inviter.email} convidou-o para se juntar ao grupo '{group_name}'.",
        related_user=inviter
    )
