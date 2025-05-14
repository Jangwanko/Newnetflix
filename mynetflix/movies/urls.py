from django.urls import path
from . import views

urlpatterns = [
    path('', views.movie_list, name='movie_list'),
    path('movie/<int:movie_id>/', views.movie_detail, name='movie_detail'),
    path('movie/<int:movie_id>/edit/', views.edit_movie, name='edit_movie'),
    path('movie/<int:movie_id>/delete/', views.delete_movie, name='delete_movie'),
    path('upload/', views.upload_movie, name='upload_movie'),
]
