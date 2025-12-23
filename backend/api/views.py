from django.contrib.auth import authenticate
from django.contrib.auth import get_user_model
from rest_framework.decorators import api_view
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



@api_view(['GET'])
def healthcheck(request):
    """Endpoint simples para testar se a API está a funcionar"""
    return Response({
        "status": "ok",
        "debug": settings.DEBUG,
        "database": "connected" if connection.ensure_connection() is None else "error"
    })