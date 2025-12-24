from django.db import models

from django.contrib.auth.models import AbstractUser
import uuid
from django.conf import settings

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



UserModel = settings.AUTH_USER_MODEL


class Group(models.Model):
    name = models.CharField(max_length=255)

    # owner principal (criador)
    owner = models.ForeignKey(
        UserModel,
        on_delete=models.CASCADE,
        related_name="owned_groups"
    )

    invite_code = models.UUIDField(default=uuid.uuid4, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name

class GroupMembership(models.Model):
    """
    Roles:
    - owner  → máximo 2 por grupo
    - member → utilizador normal
    """
    ROLE_CHOICES = [
        ("owner", "Owner"),
        ("member", "Member"),
    ]

    user = models.ForeignKey(UserModel, on_delete=models.CASCADE)
    group = models.ForeignKey(Group, on_delete=models.CASCADE)

    role = models.CharField(
        max_length=20,
        choices=ROLE_CHOICES,
        default="member"
    )

    # usado para determinar o owner mais antigo
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("user", "group")

    def __str__(self):
        return f"{self.user} in {self.group} ({self.role})"



class GroupInvite(models.Model):
    """
    Convite por email: o utilizador convidado decide aceitar/recusar.
    Só cria GroupMembership quando for ACCEPTED.
    """
    STATUS_CHOICES = [
        ("PENDING", "Pending"),
        ("ACCEPTED", "Accepted"),
        ("DECLINED", "Declined"),
    ]

    group = models.ForeignKey(Group, on_delete=models.CASCADE, related_name="invites")
    invited_user = models.ForeignKey(UserModel, on_delete=models.CASCADE, related_name="group_invites")
    invited_by = models.ForeignKey(UserModel, on_delete=models.CASCADE, related_name="sent_group_invites")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="PENDING")
    created_at = models.DateTimeField(auto_now_add=True)
    responded_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        unique_together = ("group", "invited_user")

    def __str__(self):
        return f"Invite {self.invited_user} -> {self.group} ({self.status})"

class JoinRequest(models.Model):
    """
    Pedido via invite_code: um owner do grupo decide aceitar/recusar.
    Só cria GroupMembership quando for ACCEPTED.
    """
    STATUS_CHOICES = [
        ("PENDING", "Pending"),
        ("ACCEPTED", "Accepted"),
        ("DECLINED", "Declined"),
    ]

    group = models.ForeignKey(Group, on_delete=models.CASCADE, related_name="join_requests")
    user = models.ForeignKey(UserModel, on_delete=models.CASCADE, related_name="join_requests")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="PENDING")
    created_at = models.DateTimeField(auto_now_add=True)
    decided_by = models.ForeignKey(UserModel, on_delete=models.SET_NULL, null=True, blank=True, related_name="decided_join_requests")
    decided_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        unique_together = ("group", "user")

    def __str__(self):
        return f"JoinRequest {self.user} -> {self.group} ({self.status})"