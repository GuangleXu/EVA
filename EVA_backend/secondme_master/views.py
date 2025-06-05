import os
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.conf import settings

# 中文注释：定义 docs 目录路径（相对 secondme_master 目录）
DOCS_DIR = os.path.join(os.path.dirname(__file__), "docs")

# 中文注释：确保 docs 目录存在
os.makedirs(DOCS_DIR, exist_ok=True)

@csrf_exempt  # 允许 POST/DELETE 测试时免除 CSRF 校验
def secondme_memories(request, filename=None):
    """
    中文注释：支持文件上传（POST）和删除（DELETE），文件存储在 docs 目录。
    - POST: 上传 markdown 文件
    - DELETE: 删除指定 markdown 文件
    """
    if request.method == "POST":
        # 中文注释：处理文件上传
        upload_file = request.FILES.get("file")
        if not upload_file:
            return JsonResponse({"message": "未检测到上传文件", "status": "fail"}, status=400)
        # 只允许上传 markdown 文件
        if not upload_file.name.endswith(".md"):
            return JsonResponse({"message": "只允许上传 markdown 文件", "status": "fail"}, status=400)
        save_path = os.path.join(DOCS_DIR, upload_file.name)
        with open(save_path, "wb") as f:
            for chunk in upload_file.chunks():
                f.write(chunk)
        return JsonResponse({"message": f"文件 {upload_file.name} 上传成功！", "status": "success"})

    elif request.method == "DELETE":
        # 中文注释：处理文件删除
        if not filename:
            return JsonResponse({"message": "未指定要删除的文件名", "status": "fail"}, status=400)
        file_path = os.path.join(DOCS_DIR, filename)
        if not os.path.exists(file_path):
            return JsonResponse({"message": f"文件 {filename} 不存在", "status": "fail"}, status=404)
        os.remove(file_path)
        return JsonResponse({"message": f"文件 {filename} 删除成功！", "status": "success"})

    else:
        # 中文注释：仅支持 POST 和 DELETE
        return JsonResponse({"message": "仅支持 POST（上传）和 DELETE（删除）请求", "status": "fail"}, status=405)
