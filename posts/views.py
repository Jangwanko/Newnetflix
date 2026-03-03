from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect
from django.views.decorators.http import require_POST

from movies.models import Movie

from .forms import CommentForm
from .models import Like, Notification


@login_required
@require_POST
def toggle_like(request, movie_id):
    movie = get_object_or_404(Movie, id=movie_id)
    like, created = Like.objects.get_or_create(movie=movie, user=request.user)

    if not created:
        like.delete()
    elif movie.uploaded_by != request.user:
        Notification.objects.create(
            recipient=movie.uploaded_by,
            sender=request.user,
            movie=movie,
            type='like',
            message=f"{request.user.username}님이 '{movie.title}' 영상을 좋아합니다.",
        )

    return redirect('movie_detail', movie_id=movie.id)


@login_required
@require_POST
def add_comment(request, movie_id):
    movie = get_object_or_404(Movie, id=movie_id)
    form = CommentForm(request.POST)

    if form.is_valid():
        comment = form.save(commit=False)
        comment.movie = movie
        comment.user = request.user
        comment.save()

        if movie.uploaded_by != request.user:
            Notification.objects.create(
                recipient=movie.uploaded_by,
                sender=request.user,
                movie=movie,
                type='comment',
                message=f"{request.user.username}님이 '{movie.title}' 영상에 댓글을 남겼습니다: {comment.content}",
            )

    return redirect('movie_detail', movie_id=movie.id)


@login_required
def read_notification(request, noti_id):
    noti = get_object_or_404(Notification, id=noti_id, recipient=request.user)
    noti.is_read = True
    noti.save(update_fields=['is_read'])
    return redirect('movie_detail', movie_id=noti.movie.id)


@login_required
@require_POST
def delete_notification(request, noti_id):
    noti = get_object_or_404(Notification, id=noti_id, recipient=request.user)
    noti.delete()
    return redirect(request.META.get('HTTP_REFERER', 'home'))
