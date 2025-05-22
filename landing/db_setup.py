import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
from django.conf import settings
from landing.models import Contact, CustomUser

def create_database():
    db_settings = settings.DATABASES['default']
    dbname = db_settings['NAME']
    
    try:
        # Connexion à la base postgres par défaut
        conn = psycopg2.connect(
            dbname='postgres',
            user=db_settings['USER'],
            password=db_settings['PASSWORD'],
            host=db_settings['HOST'],
            port=db_settings['PORT']
        )
        conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
        cursor = conn.cursor()
        
        # Vérifie si la DB existe déjà
        cursor.execute("SELECT 1 FROM pg_database WHERE datname = %s", (dbname,))
        exists = cursor.fetchone()
        if not exists:
            cursor.execute(f"CREATE DATABASE {dbname};")
            print(f"Base de données '{dbname}' créée.")
        else:
            print(f"Base de données '{dbname}' existe déjà.")
        cursor.close()
        conn.close()
    except Exception as e:
        print(f"Erreur lors de la création de la base de données: {e}")

def create_admin_user():
    """
    Crée un compte administrateur par défaut si aucun n'existe.
    Identifiants: root45 / soleillevant
    """
    try:
        # Vérifie si l'administrateur existe déjà
        admin_exists = CustomUser.objects.filter(username='root45').exists()
        
        if not admin_exists:
            # Création du contact pour l'administrateur
            admin_contact = Contact.objects.create(
                nom="Administrateur",
                postnom="Système",
                prenom="Admin",
                sexe="M",
                adresse="NoteIA - Système",
                tel="admin-system-123"
            )
            
            # Création du compte administrateur
            admin_user = CustomUser(
                username='root45',
                contact=admin_contact
            )
            admin_user.set_password('soleillevant')
            admin_user.save()
            
            print("Compte administrateur créé avec succès (username: root45, password: soleillevant)")
        else:
            print("Le compte administrateur existe déjà")
            
    except Exception as e:
        print(f"Erreur lors de la création du compte administrateur: {e}")
