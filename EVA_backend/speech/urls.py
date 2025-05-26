# speech/urls.py
from django.urls import path
from .views import tts_generation

urlpatterns = [
    path("tts/", tts_generation, name="tts-generation"),
]
