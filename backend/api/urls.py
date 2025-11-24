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

    # Grupos
    path('groups/create/', views.create_group, name='create_group'),
    path('groups/my/', views.my_groups, name='my_groups'),
    path('groups/<int:group_id>/members/', views.group_members, name='group_members'),
    path('groups/<int:group_id>/invite/', views.invite_member, name='invite_member'),
    path('groups/join/<uuid:invite_code>/', views.join_group, name='join_group'),
    path('groups/<int:group_id>/promote/<int:user_id>/', views.promote_to_admin, name='promote_to_admin'),
    path('groups/<int:group_id>/demote/<int:user_id>/', views.demote_to_member, name='demote_to_member'),
]
