from django.contrib.auth import get_user_model
from django.test import Client, TestCase
from django.urls import reverse


class SignupTests(TestCase):
    def test_signup_creates_user(self):
        response = self.client.post(
            reverse('signup'),
            {
                'username': 'newuser',
                'nickname': 'nick',
                'email': 'newuser@example.com',
                'password1': 'ComplexPass123!!',
                'password2': 'ComplexPass123!!',
            },
            follow=True,
        )

        self.assertEqual(response.status_code, 200)
        self.assertTrue(get_user_model().objects.filter(username='newuser').exists())

    def test_signup_invalid_password_shows_reason_on_signup_page(self):
        response = self.client.post(
            reverse('signup'),
            {
                'username': 'weakuser',
                'nickname': 'nick',
                'email': 'weak@example.com',
                'password1': '1234',
                'password2': '1234',
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, '입력값을 확인해 주세요.')
        self.assertContains(response, '비밀번호')
        self.assertFalse(get_user_model().objects.filter(username='weakuser').exists())

    def test_signup_csrf_failure_shows_message_on_signup_page(self):
        csrf_client = Client(enforce_csrf_checks=True)
        response = csrf_client.post(
            reverse('signup'),
            {
                'username': 'csrfuser',
                'nickname': 'nick',
                'email': 'csrf@example.com',
                'password1': 'ComplexPass123!!',
                'password2': 'ComplexPass123!!',
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, '보안 토큰(CSRF)')
