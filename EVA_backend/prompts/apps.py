# EVA_backend/prompts/apps.py

from django.apps import AppConfig

class PromptsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'prompts'

    def ready(self):
        import prompts.signals  # 例如导入其他初始化代码
