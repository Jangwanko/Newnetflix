import os
import re
import mimetypes
from django.shortcuts import render, redirect, get_object_or_404
from django.http import StreamingHttpResponse, Http404
from django.core.files.storage import FileSystemStorage
from django.http import JsonResponse
from django.contrib import messages
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth import login, authenticate
from django.contrib.auth.views import LoginView, LogoutView
from django.contrib.auth.decorators import login_required
from django.utils.http import http_date
from wsgiref.util import FileWrapper
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
            return redirect('movie_detail', movie.id)
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

CHUNK_SIZE = 8192  # 8 KB

@login_required
def stream_video(request, movie_id):
    movie = get_object_or_404(Movie, id=movie_id, uploaded_by=request.user)
    file_path = movie.video_file.path

    if not os.path.exists(file_path):
        raise Http404("비디오 파일이 존재하지 않습니다.")

    file_size = os.path.getsize(file_path)
    content_type, _ = mimetypes.guess_type(file_path)
    content_type = content_type or 'application/octet-stream'

    range_header = request.headers.get('Range', '').strip()
    if range_header:
        # "Range: bytes=start-end" 형식 처리
        match = re.match(r'bytes=(\d+)-(\d*)', range_header)
        if match:
            start = int(match.group(1))
            end = int(match.group(2)) if match.group(2) else file_size - 1
            length = end - start + 1

            def stream_generator():
                with open(file_path, 'rb') as f:
                    f.seek(start)
                    remaining = length
                    while remaining > 0:
                        chunk_size = min(CHUNK_SIZE, remaining)
                        data = f.read(chunk_size)
                        if not data:
                            break
                        yield data
                        remaining -= len(data)

            response = StreamingHttpResponse(stream_generator(), status=206, content_type=content_type)
            response['Content-Length'] = str(length)
            response['Content-Range'] = f'bytes {start}-{end}/{file_size}'
            response['Accept-Ranges'] = 'bytes'
            response['Cache-Control'] = 'no-cache'
            response['Last-Modified'] = http_date(os.path.getmtime(file_path))
            return response

    # Range 요청이 없으면 전체 스트림 전송
    response = StreamingHttpResponse(FileWrapper(open(file_path, 'rb')), content_type=content_type)
    response['Content-Length'] = str(file_size)
    response['Accept-Ranges'] = 'bytes'
    return response    
