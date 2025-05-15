from django.shortcuts import render, redirect, get_object_or_404
from django.core.files.storage import FileSystemStorage
from django.http import JsonResponse
from django.contrib import messages
from django.contrib.auth.forms import UserCreationForm
from django.contrib import messages
import os
from django.conf import settings
from .models import Movie
from .forms import MovieForm

def home(request):
    return render(request, 'movies/home.html')

def movie_list(request):
    movies = Movie.objects.all()
    return render(request, 'movies/movie_list.html', {'movies': movies})

def movie_detail(request, movie_id):
    movie = get_object_or_404(Movie, id=movie_id)
    return render(request, 'movies/movie_detail.html', {'movie': movie})

def upload_movie(request):
    if request.method == 'POST' and request.FILES.get('video_file'):
        title = request.POST.get('title', 'Untitled')
        description = request.POST.get('description', '')
        video_file = request.FILES['video_file']

        fs = FileSystemStorage()
        filename = fs.save(video_file.name, video_file)

        Movie.objects.create(
            title=title,
            description=description,
            video_file=filename
        )

        # 업로드 후 목록 페이지로 리다이렉트
        return redirect('movie_list')

    return render(request, 'movies/upload.html')

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