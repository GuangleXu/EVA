from django.http import JsonResponse
from django.views.decorators.http import require_http_methods


@require_http_methods(["GET"])
def get_tasks(request):
    """获取任务列表"""
    return JsonResponse({"message": "Task list endpoint"})


@require_http_methods(["POST"])
def create_task(request):
    """创建新任务"""
    return JsonResponse({"message": "Create task endpoint"})
