from django.http import JsonResponse
from django.views.decorators.http import require_http_methods


@require_http_methods(["GET"])
def index(request):
    """EVA 服务的默认视图"""
    return JsonResponse({"status": "ok", "message": "Welcome to EVA Service API"})
