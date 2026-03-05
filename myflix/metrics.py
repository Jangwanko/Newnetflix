
from django.db import connections
from django.db.utils import OperationalError
from django.http import HttpResponse, JsonResponse
from prometheus_client import CONTENT_TYPE_LATEST, CollectorRegistry, Counter, Histogram, generate_latest

REGISTRY = CollectorRegistry(auto_describe=True)

HTTP_REQUESTS_TOTAL = Counter(
    "myflix_http_requests_total",
    "Total HTTP requests",
    ["method", "path", "status"],
    registry=REGISTRY,
)

HTTP_REQUEST_DURATION_SECONDS = Histogram(
    "myflix_http_request_duration_seconds",
    "HTTP request latency",
    ["method", "path"],
    buckets=(0.05, 0.1, 0.25, 0.5, 1, 2, 5, 10),
    registry=REGISTRY,
)

MOVIE_UPLOAD_REQUESTS_TOTAL = Counter(
    "myflix_movie_upload_requests_total",
    "Movie upload request count",
    ["result"],
    registry=REGISTRY,
)

MOVIE_UPLOAD_DURATION_SECONDS = Histogram(
    "myflix_movie_upload_duration_seconds",
    "Movie upload request latency",
    buckets=(0.5, 1, 2, 5, 10, 30, 60, 120, 300, 600),
    registry=REGISTRY,
)

VIDEO_PROCESSING_TRANSITIONS_TOTAL = Counter(
    "myflix_video_processing_transitions_total",
    "Video processing status transitions",
    ["status"],
    registry=REGISTRY,
)


def record_request(method: str, path: str, status_code: int, duration_seconds: float) -> None:
    HTTP_REQUESTS_TOTAL.labels(method=method, path=path, status=str(status_code)).inc()
    HTTP_REQUEST_DURATION_SECONDS.labels(method=method, path=path).observe(duration_seconds)


def record_upload(duration_seconds: float, success: bool) -> None:
    MOVIE_UPLOAD_REQUESTS_TOTAL.labels(result="success" if success else "error").inc()
    MOVIE_UPLOAD_DURATION_SECONDS.observe(duration_seconds)


def record_video_processing_transition(status: str) -> None:
    VIDEO_PROCESSING_TRANSITIONS_TOTAL.labels(status=status).inc()


def metrics_view(request):
    return HttpResponse(generate_latest(REGISTRY), content_type=CONTENT_TYPE_LATEST)


def livez(_request):
    return JsonResponse({"status": "ok"})


def readyz(_request):
    try:
        with connections["default"].cursor() as cursor:
            cursor.execute("SELECT 1")
    except OperationalError:
        return JsonResponse({"status": "error", "dependency": "database"}, status=503)

    return JsonResponse({"status": "ready"})
