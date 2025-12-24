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
    path("documents/<int:pk>/", views.document_detail),

    # Grupos
    path('groups/', views.list_groups, name='list_groups'),

    # Notificações
    path('notifications/', views.list_notifications, name='list-notifications'),
    path('notifications/count/', views.get_notification_count, name='notification-count'),
    path('notifications/<int:pk>/', views.notification_detail, name='notification-detail'),
    path('notifications/mark-all-as-read/', views.mark_all_notifications_as_read, name='mark-all-as-read'),
    path('notifications/<int:pk>/delete/', views.delete_notification, name='delete-notification'),
    path('notifications/delete-all/', views.delete_all_notifications, name='delete-all-notifications'),

    # Perfil
    path('profile/', views.profile, name='profile'),
]
