import logging
import time

from celery import shared_task

from .models import Document, Metric

logger = logging.getLogger(__name__)


@shared_task(bind=True, autoretry_for=(Exception,), retry_backoff=True, max_retries=3)
def process_document(self, document_id: int):
    """
    Background job that marks a document as processed.
    """
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
        duration_ms = int((time.perf_counter() - started) * 1000)

        document.text = ""
        document.state = "DONE"
        document.duration_ms = duration_ms
        document.n_descriptors = 0
        document.save(update_fields=["text", "state", "duration_ms", "n_descriptors", "updated_at"])

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
