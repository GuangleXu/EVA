from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from .speech_manager import SpeechManager

@csrf_exempt
def tts_generation(request):
    if request.method == "POST":
        text = request.POST.get("text", "")
        if not text:
            return JsonResponse({"error": "缺少文本参数"}, status=400)
        
        speech_manager = SpeechManager()
        audio_url = speech_manager.generate_speech(text)

        return JsonResponse({"audio_url": audio_url})
    
    return JsonResponse({"error": "只支持 POST 请求"}, status=405)
