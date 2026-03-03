from django.db import models
from django.conf import settings


class Movie(models.Model):
    class ProcessingStatus(models.TextChoices):
        QUEUED = 'queued', '대기 중'
        PROCESSING = 'processing', '처리 중'
        READY = 'ready', '재생 가능'
        FAILED = 'failed', '처리 실패'

    title = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    video_file = models.FileField(upload_to='videos/')
    processing_status = models.CharField(
        max_length=20,
        choices=ProcessingStatus.choices,
        default=ProcessingStatus.READY,
    )
    processing_error = models.TextField(blank=True)
    duration_seconds = models.FloatField(null=True, blank=True)
    uploaded_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    uploaded_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.title

    @property
    def is_ready(self):
        return self.processing_status == self.ProcessingStatus.READY
