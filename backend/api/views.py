from django.contrib.auth import authenticate
from django.contrib.auth import get_user_model
from rest_framework.decorators import api_view
from rest_framework.response import Response
from django.contrib.auth import authenticate, get_user_model
from django.http import FileResponse
from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.decorators import api_view, permission_classes, parser_classes
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from .models import Document, Prediction, Explanation, Metric
from .serializers import DocumentDetailSerializer
from rest_framework_simplejwt.tokens import RefreshToken

from .models import Document
from .serializers import DocumentDetailSerializer, DocumentSerializer
from .tasks import process_document

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
@permission_classes([IsAuthenticated])
def list_documents(request):
    """
    Lista real de documentos do utilizador autenticado.
    """
    documents = Document.objects.filter(user=request.user).order_by("-created_at")
    serializer = DocumentSerializer(documents, many=True, context={"request": request})
    return Response(serializer.data)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
@parser_classes([MultiPartParser, FormParser])
def upload_document(request):
    """
    Upload de PDF. Guarda o ficheiro, cria o registo e envia para processamento assincrono.
    """
    uploaded_file = request.FILES.get("file")

    if uploaded_file is None:
        return Response({"error": "Campo 'file' e obrigatorio (multipart/form-data)."}, status=status.HTTP_400_BAD_REQUEST)

    filename = request.data.get("filename") or uploaded_file.name

    document = Document.objects.create(
        user=request.user,
        file=uploaded_file,
        filename=filename,
        state="QUEUED",
    )

    # Enfileirar processamento do PDF
    process_document.delay(document.id)

    serializer = DocumentSerializer(document, context={"request": request})
    return Response(serializer.data, status=status.HTTP_201_CREATED)


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
    document = get_object_or_404(Document, pk=pk, user=request.user)
    serializer = DocumentDetailSerializer(document, context={"request": request})
    return Response(serializer.data)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def download_document(request, pk):
    """
    Endpoint para recuperar o PDF armazenado.
    """
    document = get_object_or_404(Document, pk=pk, user=request.user)

    if not document.file:
        return Response({"detail": "Ficheiro nao encontrado."}, status=status.HTTP_404_NOT_FOUND)

    return FileResponse(document.file.open("rb"), as_attachment=True, filename=document.filename)


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
