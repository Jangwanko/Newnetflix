from django.urls import path
from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('movies/', views.movie_list, name='movie_list'),
    path('movie/upload/', views.movie_form, name='upload_movie'),
    path('movie/upload/worker/', views.upload_worker_page, name='upload_worker'),
    path('movie/<int:movie_id>/', views.movie_detail, name='movie_detail'),
    path('movie/<int:movie_id>/edit/', views.movie_form, name='edit_movie'),
    path('movie/<int:movie_id>/delete/', views.delete_movie, name='delete_movie'),
]
