from django.shortcuts import render, redirect, get_object_or_404
from django.core.files.storage import FileSystemStorage
from django.http import JsonResponse
from django.contrib import messages
from django.contrib.auth.forms import UserCreationForm
from django.contrib import messages
from django.contrib.auth.views import LoginView, LogoutView
from django.contrib.auth.decorators import login_required
import os
from django.conf import settings
from .models import Movie
from .forms import MovieForm

def home(request):
    return render(request, 'movies/home.html')

@login_required
def movie_list(request):
    movies = Movie.objects.filter(uploaded_by=request.user).order_by('-uploaded_at')
    return render(request, 'movies/movie_list.html', {'movies': movies})

def movie_detail(request, movie_id):
    movie = get_object_or_404(Movie, id=movie_id)
    return render(request, 'movies/movie_detail.html', {'movie': movie})

@login_required
def upload_movie(request):
    if request.method == 'POST':
        form = MovieForm(request.POST, request.FILES)
        if form.is_valid():
            movie = form.save(commit=False)
            movie.uploaded_by = request.user
            movie.save()
            return redirect('movie_list')
    else:
        form = MovieForm()
    return render(request, 'movies/upload_movie.html', {'form': form})

def delete_movie(request, movie_id):
    movie = get_object_or_404(Movie, id=movie_id)
    file_path = movie.video_file.path
    try:
        if os.path.exists(file_path):
            os.remove(file_path)
    except PermissionError:
        pass
    movie.delete()
    return redirect('movie_list')

def edit_movie(request, movie_id):
    movie = get_object_or_404(Movie, id=movie_id)
    if request.method == 'POST':
        form = MovieForm(request.POST, instance=movie)
        if form.is_valid():
            form.save()
            return redirect('movie_detail', movie_id=movie.id)
    else:
        form = MovieForm(instance=movie)
    return render(request, 'movies/edit_movie.html', {'form': form})

def home(request):
    return render(request, 'movies/home.html')

def signup(request):
    if request.method == 'POST':
        form = UserCreationForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, '회원가입이 완료되었습니다. 로그인해주세요.')
            return redirect('login')  # 로그인 페이지 URL 이름
    else:
        form = UserCreationForm()
    return render(request, 'movies/signup.html', {'form': form})

class CustomLoginView(LoginView):
    template_name = 'movies/login.html'

    def form_valid(self, form):
        messages.success(self.request, "로그인 되었습니다.")
        return super().form_valid(form)

    def form_invalid(self, form):
        messages.error(self.request, "아이디 혹은 비밀번호가 틀립니다.")
        return super().form_invalid(form)

class CustomLogoutView(LogoutView):
    def dispatch(self, request, *args, **kwargs):
        messages.info(request, "로그아웃 되었습니다.")
        return super().dispatch(request, *args, **kwargs)