from django.urls import path
from . import views

from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
)

urlpatterns = [
    path('register/', views.register, name='register'),
    path('login/', views.login, name='login'),
    # outros endpoints...
    path('token/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    # Documentos
    path('documents/', views.list_documents, name='list_documents'),
    path('documents/upload/', views.upload_document, name='upload_document'),

 # Grupos (base)
    path('groups/create/', views.create_group, name='create_group'),
    path('groups/my/', views.my_groups, name='my_groups'),
    path('groups/<int:group_id>/members/', views.group_members, name='group_members'),

    # Convites por email (utilizador decide)
    path('groups/<int:group_id>/invite/', views.invite_member, name='invite_member'),
    path('groups/invites/my/', views.my_invites, name='my_invites'),
    path('groups/invites/<int:invite_id>/accept/', views.accept_invite, name='accept_invite'),
    path('groups/invites/<int:invite_id>/decline/', views.decline_invite, name='decline_invite'),

    # Join via QR (owner decide)
    path('groups/join/<uuid:invite_code>/', views.join_group, name='join_group'),
    path('groups/<int:group_id>/join-requests/', views.list_join_requests, name='list_join_requests'),
    path('groups/join-requests/<int:request_id>/approve/', views.approve_join_request, name='approve_join_request'),
    path('groups/join-requests/<int:request_id>/reject/', views.reject_join_request, name='reject_join_request'),

    # Owners (roles)
    path('groups/<int:group_id>/promote/<int:user_id>/', views.promote_to_owner, name='promote_to_owner'),
    path('groups/<int:group_id>/demote/<int:user_id>/', views.demote_owner, name='demote_owner'),
]