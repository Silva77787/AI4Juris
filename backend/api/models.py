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
    """
    Grupos de trabalho / equipas do AI4Juris.
    """
    name = models.CharField(max_length=255)
    owner = models.ForeignKey(
        UserModel,
        on_delete=models.CASCADE,
        related_name="owned_groups"
    )

    # usado para convite e QR code
    invite_code = models.UUIDField(default=uuid.uuid4, unique=True)

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name


class GroupMembership(models.Model):
    """
    Relação entre users e grupos, com roles:
    - owner: criador (apenas 1)
    - admin: escolhido pelo owner
    - member: utilizador normal
    """
    ROLE_CHOICES = [
        ("owner", "Owner"),
        ("admin", "Admin"),
        ("member", "Member"),
    ]

    user = models.ForeignKey(UserModel, on_delete=models.CASCADE)
    group = models.ForeignKey(Group, on_delete=models.CASCADE)

    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default="member")
    joined_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("user", "group")

    def save(self, *args, **kwargs):
        # Impedir mais do que 1 owner por grupo
        if self.role == "owner":
            already_owner = GroupMembership.objects.filter(
                group=self.group,
                role="owner"
            ).exclude(pk=self.pk)

            if already_owner.exists():
                raise ValueError("Este grupo já tem um owner (só pode existir um).")

        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.user} in {self.group} ({self.role})"

