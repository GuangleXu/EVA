from django.urls import path

from . import views

app_name = "eva_service"  # 添加应用命名空间

urlpatterns = [
    # 添加根路径的处理
    path("", views.index, name="index"),  # 添加默认视图
    # 其他现有的 URL 模式...
]
