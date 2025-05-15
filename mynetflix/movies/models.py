from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone

# movies/models.py
class Movie(models.Model):
    title = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    video_file = models.FileField(upload_to='')  # 빈 문자열: media/ 바로 아래 저장
    uploaded_by = models.ForeignKey(User, on_delete=models.CASCADE)
    uploaded_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.title
