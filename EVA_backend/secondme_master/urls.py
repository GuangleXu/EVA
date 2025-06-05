# secondme_master/urls.py
from django.urls import path
from .views import secondme_memories

urlpatterns = [
    path("secondme_memories/", secondme_memories, name="secondme_memories"),
]
