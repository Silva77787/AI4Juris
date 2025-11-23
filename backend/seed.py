from django.contrib.auth import get_user_model
from api.models import Document, Prediction, Explanation, Metric

def run():
    User = get_user_model()

    # Criar user
    user, _ = User.objects.get_or_create(username="demo_user", role="user")
    user.set_password("123456")
    user.save()

    # Criar documento
    doc = Document.objects.create(
        user=user,
        file="documents/exemplo.pdf",
        filename="exemplo.pdf",
        state="DONE",
        text="Texto extraído do PDF…",
        duration_ms=1520,
        n_descriptors=3,
        error_msg=None,
    )

    # Previsões
    p1 = Prediction.objects.create(
        document=doc,
        descriptor="Tipo de contrato",
        score=0.92
    )

    p2 = Prediction.objects.create(
        document=doc,
        descriptor="Partes envolvidas",
        score=0.88
    )

    # Explicações
    Explanation.objects.create(
        prediction=p1,
        text_span="Contrato de prestação de serviços",
        start_offset=54,
        end_offset=89,
        score=0.87
    )

    Explanation.objects.create(
        prediction=p2,
        text_span="Empresa XPTO e Cliente João",
        start_offset=120,
        end_offset=150,
        score=0.91
    )

    # Métricas
    Metric.objects.create(document=doc, stage="OCR", duration_ms=450)
    Metric.objects.create(document=doc, stage="LLM Processing", duration_ms=980)
    Metric.objects.create(document=doc, stage="Post-processing", duration_ms=90)

    print("Database seeded successfully! Document ID:", doc.id)
