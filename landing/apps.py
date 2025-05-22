from django.apps import AppConfig


class LandingConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'landing'


    def ready(self):
        """
        Méthode appelée au démarrage de l'application.
        Crée la base de données si nécessaire et l'utilisateur administrateur.
        """
        # Import ici pour éviter l'import circulaire
        from landing.db_setup import create_database, create_admin_user
        
        # On n'exécute ceci que si c'est le processus principal
        # pour éviter de l'exécuter deux fois lors de l'utilisation de runserver
        import sys
        if 'runserver' in sys.argv:
            try:
                # Créer la base de données si nécessaire
                create_database()
                
                # Créer l'utilisateur admin
                create_admin_user()
            except Exception as e:
                print(f"Erreur lors de l'initialisation: {e}")
