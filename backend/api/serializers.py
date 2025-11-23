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
            "predictions",
            "metrics",
        ]
