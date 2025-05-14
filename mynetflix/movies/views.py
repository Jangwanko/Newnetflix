from django.shortcuts import render, redirect
from django.core.files.storage import FileSystemStorage
from django.http import JsonResponse
from django.contrib import messages
import os
from django.conf import settings
from .models import Movie

def home(request):
    return render(request, 'movies/home.html')

def movie_list(request):
    movies = Movie.objects.all()
    return render(request, 'movies/movie_list.html', {'movies': movies})

def movie_detail(request, movie_id):
    movie = Movie.objects.get(id=movie_id)
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
    movie = Movie.objects.get(id=movie_id)
    file_path = movie.video_file.path

    try:
        if os.path.exists(file_path):
            os.remove(file_path)  # 실제 파일 삭제
    except PermissionError:
        messages.error(request, "파일이 사용 중입니다. 브라우저나 프로그램에서 영상을 닫고 다시 시도하세요.")
        return redirect('movie_detail', movie_id=movie.id)

    movie.delete()  # DB 레코드 삭제
    messages.success(request, "영상이 삭제되었습니다.")
    return redirect('movie_list')

def edit_movie(request, movie_id):
    movie = Movie.objects.get(id=movie_id)

    if request.method == 'POST':
        title = request.POST.get('title')
        description = request.POST.get('description')

        movie.title = title
        movie.description = description
        movie.save()

        return redirect('movie_detail', movie_id=movie.id)

    return render(request, 'movies/edit_movie.html', {'movie': movie})
