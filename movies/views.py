from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from .models import Movie
from .forms import MovieForm
from django.http import FileResponse
from posts.forms import CommentForm

def home(request):
    return render(request, 'movies/home.html')

def movie_list(request):
    movies = Movie.objects.all().order_by('-uploaded_at')
    return render(request, 'movies/movie_list.html', {'movies': movies})

def movie_detail(request, movie_id):
    movie = get_object_or_404(Movie, id=movie_id)
    comment_form = CommentForm()
    return render(request, 'movies/movie_detail.html', {
        'movie': movie,
        'comment_form': comment_form
    })

@login_required
def movie_form(request, movie_id=None):
    if movie_id:
        movie = get_object_or_404(Movie, id=movie_id, uploaded_by=request.user)
    else:
        movie = None

    if request.method == 'POST':
        form = MovieForm(request.POST, request.FILES, instance=movie)
        if form.is_valid():
            new_movie = form.save(commit=False)
            if not movie:
                new_movie.uploaded_by = request.user
            new_movie.save()
            return redirect('movie_detail', new_movie.id)
    else:
        form = MovieForm(instance=movie)

    return render(request, 'movies/movie_form.html', {'form': form})

@login_required
def delete_movie(request, movie_id):
    movie = get_object_or_404(Movie, id=movie_id, uploaded_by=request.user)
    if request.method == 'POST':
        movie.delete()
        return redirect('movie_list')
    return render(request, 'movies/confirm_delete.html', {'movie': movie})

@login_required
def stream_video(request, movie_id):
    movie = get_object_or_404(Movie, id=movie_id)
    return FileResponse(movie.video_file.open(), content_type='video/mp4')