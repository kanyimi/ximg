from django.apps import AppConfig


class PhotohostappConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "photohostapp"


    def ready(self):
        import photohostapp.signals