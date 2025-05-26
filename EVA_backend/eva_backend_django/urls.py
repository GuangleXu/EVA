# EVA_backend/eva_backend_django/urls.py

"""
URL configuration for eva_backend_django project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.1/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""

from django.contrib import admin
from eva_backend_django import settings
from django.conf.urls.static import static
from django.urls import include, path, re_path
from django.views.generic import TemplateView
from api_service.views import health_check
from django.http import JsonResponse

admin.site.site_title = "EVA Admin"
admin.site.site_header = "EVA Admin"

urlpatterns = [
    path("admin/", admin.site.urls),
    path("eva/", include("eva_service.urls")),  # EVA 服务模块的路由
    path("api/", include("api_service.urls")),  # API 服务模块的路由
    path('speech/', include('speech.urls')),  # 语音服务的路由
]

# 配置静态和媒体文件路由
urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

if settings.DEBUG:  # 仅在 DEBUG 模式下启用 Debug Toolbar
    import debug_toolbar
    urlpatterns += [
        path('__debug__/', include(debug_toolbar.urls, namespace='djdt')),
    ]
