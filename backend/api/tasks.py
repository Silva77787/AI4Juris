import logging
import os
import time

import requests
from celery import shared_task
from pypdf import PdfReader

from .models import Document, Explanation, Metric, Prediction

logger = logging.getLogger(__name__)


def _extract_pdf_text_from_storage(document):
    if not document.file:
        return ""
    try:
        document.file.open("rb")
        reader = PdfReader(document.file)
        chunks = []
        for page in reader.pages:
            try:
                page_text = page.extract_text() or ""
            except Exception:
                page_text = ""
            if page_text:
                chunks.append(page_text)
        return "\n".join(chunks).strip()
    except Exception:
        return ""
    finally:
        try:
            document.file.close()
        except Exception:
            pass


def _call_identify_text(text):
    base_url = os.environ.get("IA_API_URL", "http://host.docker.internal:8000")
    url = f"{base_url.rstrip('/')}/identify_text"
    timeout = float(os.environ.get("IA_API_TIMEOUT_SEC", "60"))
    resp = requests.post(url, json={"text": text}, timeout=timeout)
    resp.raise_for_status()
    data = resp.json()
    return data.get("decision"), data.get("response")


@shared_task(bind=True, autoretry_for=(Exception,), retry_backoff=True, max_retries=3)
def process_document(self, document_id: int):
    started = time.perf_counter()

    try:
        document = Document.objects.get(pk=document_id)
    except Document.DoesNotExist:
        logger.warning("Document %s not found for processing", document_id)
        return

    document.state = "PROCESSING"
    document.error_msg = ""
    document.save(update_fields=["state", "error_msg", "updated_at"])

    try:
        text = _extract_pdf_text_from_storage(document)
        document.text = text

        if not text:
            raise RuntimeError("Failed to extract text from PDF.")

        decision, response_text = _call_identify_text(text)

        document.classification = decision or ""
        document.justification = response_text or ""
        document.state = "DONE"
        document.n_descriptors = 1 if decision else 0
        duration_ms = int((time.perf_counter() - started) * 1000)
        document.duration_ms = duration_ms
        document.error_msg = ""
        document.save(update_fields=[
            "text",
            "classification",
            "justification",
            "state",
            "n_descriptors",
            "duration_ms",
            "error_msg",
            "updated_at",
        ])

        if decision:
            prediction = Prediction.objects.create(
                document=document,
                descriptor=decision,
                score=1.0,
            )
            if response_text:
                Explanation.objects.create(
                    prediction=prediction,
                    text_span=response_text,
                    start_offset=0,
                    end_offset=len(response_text),
                    score=1.0,
                )

        Metric.objects.create(document=document, stage="PROCESS_DOCUMENT", duration_ms=duration_ms)
        return {"document_id": document_id, "duration_ms": duration_ms}
    except Exception as exc:
        duration_ms = int((time.perf_counter() - started) * 1000)
        document.state = "ERROR"
        document.error_msg = str(exc)
        document.duration_ms = duration_ms
        document.save(update_fields=["state", "error_msg", "duration_ms", "updated_at"])

        Metric.objects.create(document=document, stage="PROCESS_DOCUMENT_ERROR", duration_ms=duration_ms)
        logger.exception("Failed to process document %s", document_id)
        raise
