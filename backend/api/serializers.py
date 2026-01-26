from rest_framework import serializers
from .models import Document, Prediction, Explanation, Metric

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
    file_url = serializers.SerializerMethodField()

    class Meta:
        model = Document
        fields = [
            "id",
            "filename",
            "file_url",
            "storage_path",
            "state",
            "text",
            "classification",
            "justification",
            "page_count",
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

    def get_file_url(self, obj):
        if not obj.file:
            return None
        try:
            return obj.file.url
        except Exception:
            return None
