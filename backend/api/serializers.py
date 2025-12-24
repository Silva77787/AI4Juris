from rest_framework import serializers
from .models import Document, Prediction, Explanation, Metric, Notification

class ExplanationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Explanation
        fields = ["id", "text_span", "start_offset", "end_offset", "score"]

class PredictionSerializer(serializers.ModelSerializer):
    explanations = ExplanationSerializer(many=True, read_only=True, source="explanation_set")

    class Meta:
        model = Prediction
        fields = ["id", "descriptor", "score", "explanations"]

class MetricSerializer(serializers.ModelSerializer):
    class Meta:
        model = Metric
        fields = ["id", "stage", "duration_ms", "created_at"]

class DocumentDetailSerializer(serializers.ModelSerializer):
    uploaded_by = serializers.EmailField(source="user.email", read_only=True)
    group_id = serializers.IntegerField(source="group.id", read_only=True, allow_null=True)
    predictions = PredictionSerializer(many=True, read_only=True, source="prediction_set")
    metrics = MetricSerializer(many=True, read_only=True, source="metric_set")

    class Meta:
        model = Document
        fields = [
            "id",
            "filename",
            "state",
            "text",
            "duration_ms",
            "n_descriptors",
            "error_msg",
            "created_at",
            "updated_at",
            "uploaded_by",
            "group_id",
            "predictions",
            "metrics",
        ]


class NotificationSerializer(serializers.ModelSerializer):
    notification_type_display = serializers.CharField(source='get_notification_type_display', read_only=True)
    recipient_email = serializers.CharField(source='recipient.email', read_only=True)
    related_user_email = serializers.CharField(source='related_user.email', read_only=True, allow_null=True)
    document_filename = serializers.CharField(source='document.filename', read_only=True, allow_null=True)
    
    class Meta:
        model = Notification
        fields = [
            "id",
            "notification_type",
            "notification_type_display",
            "title",
            "message",
            "recipient_email",
            "document_filename",
            "related_user_email",
            "is_read",
            "created_at",
            "read_at",
        ]
        read_only_fields = ['id', 'created_at', 'read_at']


class NotificationCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Notification
        fields = [
            "notification_type",
            "title",
            "message",
            "document",
            "related_user",
        ]
    
    def validate_notification_type(self, value):
        valid_types = [choice[0] for choice in Notification.NOTIFICATION_TYPES]
        if value not in valid_types:
            raise serializers.ValidationError(f"Tipo de notificação inválido. Tipos válidos: {valid_types}")
        return value