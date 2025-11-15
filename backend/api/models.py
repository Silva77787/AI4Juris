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