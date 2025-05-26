from . import views  # 导入task_manager_app应用中的views模块

# 定义task_manager_app的命名空间
app_name = 'task_manager_app'

# 定义task_manager_app的URL路由
urlpatterns = [
    # 暂时注释掉 task 路由
    # path('task/', include('task_manager_app.urls')),
]
