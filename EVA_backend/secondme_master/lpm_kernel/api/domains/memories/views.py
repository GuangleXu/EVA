from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse
from lpm_kernel.file_data.memory_service import StorageService
from lpm_kernel.configs.config import Config
from lpm_kernel.file_data.document_service import DocumentService
import traceback
import json

storage_service = StorageService(Config.from_env())

@csrf_exempt
def upload_file(request):
    """
    Django 版文件上传接口
    """
    if request.method != "POST":
        return JsonResponse({"message": "只支持 POST 方法"}, status=405)
    try:
        # 兼容 multipart/form-data
        file = request.FILES.get("file")
        if not file:
            return JsonResponse({"message": "未上传文件"}, status=400)
        metadata = request.POST.dict() if request.POST else None
        memory, document = storage_service.save_file(file, metadata)
        result = memory.to_dict()
        if document:
            result["document"] = {
                "id": document.id,
                "name": document.name,
                "title": document.title,
                "mime_type": document.mime_type,
                "document_size": document.document_size,
                "extract_status": getattr(document.extract_status, "value", None),
                "embedding_status": getattr(document.embedding_status, "value", None),
                "create_time": getattr(document.create_time, "isoformat", lambda: None)(),
            }
        return JsonResponse({"message": "上传成功", "data": result}, status=200)
    except Exception as e:
        return JsonResponse({"message": f"内部错误: {str(e)}", "trace": traceback.format_exc()}, status=500)

@csrf_exempt
def delete_file(request, filename):
    """
    Django 版文件删除接口
    """
    if request.method != "DELETE":
        return JsonResponse({"message": "只支持 DELETE 方法"}, status=405)
    try:
        document_service = DocumentService()
        result = document_service.delete_file_by_name(filename)
        if result:
            return JsonResponse({"message": f"文件 '{filename}' 删除成功"}, status=200)
        else:
            return JsonResponse({"message": f"文件 '{filename}' 不存在或删除失败"}, status=404)
    except Exception as e:
        return JsonResponse({"message": f"内部错误: {str(e)}", "trace": traceback.format_exc()}, status=500) 