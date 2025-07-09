from django.urls import path
from . import views

urlpatterns = [
    path('comment/<int:movie_id>/', views.add_comment, name='add_comment'),
    path('like/<int:movie_id>/', views.toggle_like, name='toggle_like'),
    path('notification/<int:noti_id>/', views.read_notification, name='read_notification'),  # ✅ 추가
    path('notification/<int:noti_id>/delete/', views.delete_notification, name='delete_notification'),
]