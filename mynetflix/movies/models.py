# movies/models.py
from django.db import models

class Movie(models.Model):
    title = models.CharField(max_length=200)
    description = models.TextField()
    genre = models.CharField(max_length=100)
    year = models.PositiveIntegerField()
    video_file=models.FileField(upload_to='videos/')

    def __str__(self):
        return self.title
