from django.apps import AppConfig


class ChatConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "chat"
    verbose_name = "Chat"

    def ready(self):
        from chat.signals import connect_signals

        connect_signals()
