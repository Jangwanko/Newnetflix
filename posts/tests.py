import tempfile

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse

from movies.models import Movie

from .models import Comment, Like, Notification


@override_settings(MEDIA_ROOT=tempfile.gettempdir())
class InteractionTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.owner = User.objects.create_user(username='owner', password='pass1234')
        self.viewer = User.objects.create_user(username='viewer', password='pass1234')
        video = SimpleUploadedFile('video.mp4', b'fake-video-content', content_type='video/mp4')
        self.movie = Movie.objects.create(
            title='Movie',
            description='desc',
            video_file=video,
            uploaded_by=self.owner,
        )

    def test_like_toggle(self):
        self.client.login(username='viewer', password='pass1234')

        self.client.post(reverse('toggle_like', args=[self.movie.id]))
        self.assertTrue(Like.objects.filter(movie=self.movie, user=self.viewer).exists())

        self.client.post(reverse('toggle_like', args=[self.movie.id]))
        self.assertFalse(Like.objects.filter(movie=self.movie, user=self.viewer).exists())

    def test_comment_and_notification_created(self):
        self.client.login(username='viewer', password='pass1234')

        self.client.post(reverse('add_comment', args=[self.movie.id]), {'content': 'great movie'})

        self.assertTrue(Comment.objects.filter(movie=self.movie, user=self.viewer, content='great movie').exists())
        self.assertTrue(
            Notification.objects.filter(
                recipient=self.owner,
                sender=self.viewer,
                movie=self.movie,
                type='comment',
            ).exists()
        )
