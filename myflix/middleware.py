import time

from .metrics import record_request


def _normalized_metric_path(request) -> str:
    resolver_match = getattr(request, "resolver_match", None)
    if resolver_match and resolver_match.route:
        route = resolver_match.route
        return route if route.startswith("/") else f"/{route}"
    return request.path


class MetricsMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        start = time.monotonic()
        response = self.get_response(request)
        duration = time.monotonic() - start
        metric_path = _normalized_metric_path(request)
        record_request(request.method, metric_path, response.status_code, duration)
        return response
