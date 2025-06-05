from django.urls import path
from . import views

urlpatterns = [
    path('file', views.upload_file, name='memories_upload_file'),  # POST
    path('file/<str:filename>', views.delete_file, name='memories_delete_file'),  # DELETE
] 