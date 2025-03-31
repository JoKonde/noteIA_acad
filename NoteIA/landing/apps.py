from django.apps import AppConfig


class LandingConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'landing'


    def ready(self):
        from . import db_setup  # Assurez-vous que le fichier db_setup.py est dans landing/ ou adaptez le chemin
        db_setup.create_database()
