from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status


# --- AUTH ---

@api_view(['POST'])
def register(request):
    """
    Registo fake: recebe email, password, name, etc.
    Por agora não grava nada em BD, só devolve um utilizador de teste.
    """
    data = request.data
    user = {
        "id": 1,
        "name": data.get("name", "User Demo"),
        "email": data.get("email", "demo@example.com"),
    }
    return Response(user, status=status.HTTP_201_CREATED)


@api_view(['POST'])
def login(request):
    """
    Login fake: aceita qualquer credencial e devolve um token de teste.
    Mais tarde ligas isto ao sistema de autenticação a sério.
    """
    data = request.data
    response_data = {
        "token": "fake-token-123",
        "user": {
            "id": 1,
            "name": "Demo User",
            "email": data.get("email", "demo@example.com"),
        },
    }
    return Response(response_data, status=status.HTTP_200_OK)


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
