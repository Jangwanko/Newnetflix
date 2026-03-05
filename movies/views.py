from django.core.paginator import Paginator
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
import time

from myflix.metrics import record_upload
from posts.forms import CommentForm

from .forms import MovieForm
from .models import Movie


def home(request):
    return render(request, "movies/home.html")


def movie_list(request):
    queryset = (
        Movie.objects.select_related("uploaded_by")
        .only("id", "title", "uploaded_at", "processing_status", "uploaded_by__username")
        .order_by("-uploaded_at")
    )
    paginator = Paginator(queryset, 20)
    page_obj = paginator.get_page(request.GET.get("page"))
    return render(request, "movies/movie_list.html", {"page_obj": page_obj, "movies": page_obj.object_list})


def movie_detail(request, movie_id):
    movie = get_object_or_404(Movie.objects.select_related("uploaded_by"), id=movie_id)
    comment_form = CommentForm()
    comments = movie.comments.select_related("user").all().order_by("-created_at")
    return render(
        request,
        "movies/movie_detail.html",
        {
            "movie": movie,
            "comment_form": comment_form,
            "comments": comments,
        },
    )


@login_required
def movie_form(request, movie_id=None):
    movie = get_object_or_404(Movie, id=movie_id, uploaded_by=request.user) if movie_id else None

    if request.method == "POST":
        started = time.monotonic()
        form = MovieForm(request.POST, request.FILES, instance=movie)
        if form.is_valid():
            new_movie = form.save(commit=False)
            if not movie:
                new_movie.uploaded_by = request.user
                new_movie.processing_status = Movie.ProcessingStatus.QUEUED
                new_movie.processing_error = ""
                new_movie.duration_seconds = None
            elif "video_file" in form.changed_data:
                new_movie.processing_status = Movie.ProcessingStatus.QUEUED
                new_movie.processing_error = ""
                new_movie.duration_seconds = None
            new_movie.save()
            record_upload(time.monotonic() - started, success=True)
            return redirect("movie_detail", new_movie.id)

        record_upload(time.monotonic() - started, success=False)
    else:
        form = MovieForm(instance=movie)

    return render(request, "movies/movie_form.html", {"form": form, "movie": movie})


@login_required
def delete_movie(request, movie_id):
    movie = get_object_or_404(Movie, id=movie_id, uploaded_by=request.user)
    if request.method == "POST":
        movie.delete()
        return redirect("movie_list")
    return render(request, "movies/confirm_delete.html", {"movie": movie})


@login_required
def upload_worker_page(request):
    return render(request, "movies/upload_worker.html")
