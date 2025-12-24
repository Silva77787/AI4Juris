from django.db import models

from django.contrib.auth.models import AbstractUser

class User(AbstractUser):
    role = models.CharField(max_length=20, default="user")

class Document(models.Model):
    STATE_CHOICES = [
        ("QUEUED", "Queued"),
        ("PROCESSING", "Processing"),
        ("DONE", "Done"),
        ("ERROR", "Error"),
        ("TIMEOUT", "Timeout"),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE)
    file = models.FileField(upload_to="documents/")
    filename = models.CharField(max_length=255)

    state = models.CharField(max_length=20, choices=STATE_CHOICES)
    text = models.TextField(null=True, blank=True)

    duration_ms = models.IntegerField(null=True, blank=True)
    n_descriptors = models.IntegerField(default=0)
    error_msg = models.TextField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)


class Prediction(models.Model):
    document = models.ForeignKey(Document, on_delete=models.CASCADE)
    descriptor = models.CharField(max_length=255)
    score = models.FloatField()


class Explanation(models.Model):
    prediction = models.ForeignKey(Prediction, on_delete=models.CASCADE)
    
    text_span = models.TextField()
    start_offset = models.IntegerField()
    end_offset = models.IntegerField()
    score = models.FloatField()


class Metric(models.Model):
    document = models.ForeignKey(Document, on_delete=models.CASCADE)
    stage = models.CharField(max_length=50)
    duration_ms = models.IntegerField()
    created_at = models.DateTimeField(auto_now_add=True)


class Notification(models.Model):
    """
    Modelo para armazenar notificações de:
    - Convites para grupos
    - Status de uploads (QUEUED, PROCESSING, DONE, ERROR)
    - Mensagens do sistema
    """
    
    NOTIFICATION_TYPES = [
        ("GROUP_INVITE", "Convite de Grupo"),
        ("UPLOAD_QUEUED", "Upload Enfileirado"),
        ("UPLOAD_PROCESSING", "Upload em Processamento"),
        ("UPLOAD_DONE", "Upload Concluído"),
        ("UPLOAD_ERROR", "Erro no Upload"),
        ("SYSTEM", "Mensagem do Sistema"),
    ]
    
    recipient = models.ForeignKey(User, on_delete=models.CASCADE, related_name="notifications")
    notification_type = models.CharField(max_length=30, choices=NOTIFICATION_TYPES)
    
    # Dados da notificação (flexível)
    title = models.CharField(max_length=255)
    message = models.TextField()
    
    # Relações opcionais
    document = models.ForeignKey(Document, on_delete=models.CASCADE, null=True, blank=True)
    related_user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name="sent_invites")
    
    # Estado
    is_read = models.BooleanField(default=False)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    read_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['recipient', '-created_at']),
            models.Index(fields=['recipient', 'is_read']),
        ]
    
    def __str__(self):
        return f"{self.get_notification_type_display()} - {self.recipient.email}"