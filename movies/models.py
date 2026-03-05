from django.conf import settings
from django.db import models


class Movie(models.Model):
    class ProcessingStatus(models.TextChoices):
        QUEUED = "queued", "Queued"
        PROCESSING = "processing", "Processing"
        READY = "ready", "Ready"
        FAILED = "failed", "Failed"

    title = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    video_file = models.FileField(upload_to="videos/")
    processing_status = models.CharField(
        max_length=20,
        choices=ProcessingStatus.choices,
        default=ProcessingStatus.READY,
    )
    processing_error = models.TextField(blank=True)
    duration_seconds = models.FloatField(null=True, blank=True)
    uploaded_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    uploaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(fields=["-uploaded_at"], name="movie_uploaded_at_idx"),
            models.Index(fields=["processing_status", "-uploaded_at"], name="movie_status_uploaded_idx"),
        ]

    def __str__(self):
        return self.title

    @property
    def is_ready(self):
        return self.processing_status == self.ProcessingStatus.READY
