from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path

from myflix.metrics import livez, metrics_view, readyz

urlpatterns = [
    path("admin/", admin.site.urls),
    path("", include("movies.urls")),
    path("users/", include("users.urls")),
    path("posts/", include("posts.urls")),
    path("metrics", metrics_view, name="metrics"),
    path("livez", livez, name="livez"),
    path("readyz", readyz, name="readyz"),
]

if settings.DEBUG and hasattr(settings, "MEDIA_ROOT"):
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
