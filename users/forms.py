from django import forms
from django.contrib.auth.forms import UserCreationForm
from .models import CustomUser


class CustomUserCreationForm(UserCreationForm):
    email = forms.EmailField(required=True)

    class Meta:
        model = CustomUser
        fields = ['username', 'nickname', 'email']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.fields['username'].label = '아이디'
        self.fields['username'].help_text = '150자 이하, 문자/숫자/@/./+/-/_만 사용할 수 있습니다.'
        self.fields['nickname'].label = '닉네임'
        self.fields['email'].label = '이메일'
        self.fields['password1'].label = '비밀번호'
        self.fields['password1'].help_text = (
            '8자 이상이며 너무 단순하거나 아이디와 유사한 비밀번호는 사용할 수 없습니다.'
        )
        self.fields['password2'].label = '비밀번호 확인'
        self.fields['password2'].help_text = '같은 비밀번호를 한 번 더 입력하세요.'
