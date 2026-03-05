import tempfile

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse

from .models import Movie


@override_settings(MEDIA_ROOT=tempfile.gettempdir())
class MovieFlowTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(username="u1", password="pass1234")

    def test_upload_requires_login(self):
        response = self.client.get(reverse("upload_movie"))
        self.assertEqual(response.status_code, 302)

    def test_authenticated_user_can_upload_movie(self):
        self.client.login(username="u1", password="pass1234")
        video = SimpleUploadedFile("video.mp4", b"fake-video-content", content_type="video/mp4")

        response = self.client.post(
            reverse("upload_movie"),
            {"title": "Test Movie", "description": "desc", "video_file": video},
            follow=True,
        )

        self.assertEqual(response.status_code, 200)
        movie = Movie.objects.get(title="Test Movie", uploaded_by=self.user)
        self.assertEqual(movie.processing_status, Movie.ProcessingStatus.QUEUED)

    def test_rejects_non_video_extension(self):
        self.client.login(username="u1", password="pass1234")
        bad_file = SimpleUploadedFile("malware.exe", b"binary", content_type="application/octet-stream")

        response = self.client.post(
            reverse("upload_movie"),
            {"title": "Bad", "description": "bad", "video_file": bad_file},
            follow=True,
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "지원하지 않는 파일 형식입니다.")
        self.assertFalse(Movie.objects.filter(title="Bad").exists())
