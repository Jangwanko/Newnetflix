from django.contrib import messages
from django.shortcuts import redirect, render
from django.views.decorators.csrf import ensure_csrf_cookie

from .forms import CustomUserCreationForm


@ensure_csrf_cookie
def signup(request):
    if request.method == 'POST':
        form = CustomUserCreationForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, '회원가입이 완료되었습니다. 로그인해 주세요.')
            return redirect('login')
    else:
        form = CustomUserCreationForm()

    return render(request, 'users/signup.html', {'form': form})


def csrf_failure(request, reason=''):
    message = '요청이 만료되었거나 보안 토큰(CSRF)이 유효하지 않습니다. 페이지를 새로고침 후 다시 시도해 주세요.'
    if request.path.startswith('/users/signup'):
        form = CustomUserCreationForm(request.POST or None)
        return render(
            request,
            'users/signup.html',
            {
                'form': form,
                'csrf_error': message,
                'csrf_reason': reason,
            },
            status=200,
        )

    return render(request, 'errors/403.html', {'csrf_error': message, 'reason': reason}, status=403)
