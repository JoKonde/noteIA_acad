# NoteIA - Application de Notes Intelligentes

NoteIA est une application de prise de notes collaborative avec des fonctionnalités d'intelligence artificielle intégrées. Elle permet aux utilisateurs de créer des cours, des notes, et de générer automatiquement des résumés et des quiz grâce à l'IA.

## Fonctionnalités principales

- **Gestion de cours et notes**
  - Création et organisation de cours
  - Différents types de notes : texte, image, PDF, audio, vidéo, OCR
  - Collaboration en temps réel

- **Fonctionnalités IA**
  - Génération de résumés intelligents
  - Création de quiz interactifs basés sur le contenu
  - Assistant IA "Eden" intégré
  - Support de multiples modèles d'IA (OpenRouter, DeepSeek, OpenAI)

- **Autres caractéristiques**
  - Système d'authentification sécurisé
  - Interface utilisateur moderne et intuitive
  - Gestion des clés API et configuration des modèles d'IA

## Prérequis

- Python 3.8+
- Django 3.2+
- PostgreSQL
- Pip (gestionnaire de paquets Python)
- Accès aux API d'IA (OpenRouter, DeepSeek ou OpenAI)

## Installation

### Installation locale

1. **Cloner le dépôt**
   ```bash
   git clone https://github.com/JoKonde/noteIA_acad
   cd noteia
   ```

2. **Créer un environnement virtuel**
   ```bash
   # Windows
   python -m venv venv
   venv\Scripts\activate

   # Linux/MacOS
   python -m venv venv
   source venv/bin/activate
   ```

3. **Installer les dépendances**
   ```bash
   pip install -r requirements.txt
   ```

4. **Configuration de la base de données**

   Créez un fichier `.env` à la racine du projet avec les variables suivantes :
   ```
   # Configuration de la base de données
   DB_NAME=noteia_db
   DB_USER=postgres
   DB_PASSWORD=votre_mot_de_passe
   DB_HOST=localhost
   DB_PORT=5432

   # Clé secrète Django
   SECRET_KEY=votre_cle_secrete_django

   # Configuration des API d'IA
   OPENROUTER_API_KEY=votre_cle_openrouter
   ```

5. **Appliquer les migrations**
   ```bash
   python manage.py makemigrations
   python manage.py migrate
   ```

6. **Lancer le serveur de développement**
   ```bash
   python manage.py runserver
   ```

7. **Accéder à l'application**
   Ouvrez un navigateur et accédez à `http://127.0.0.1:8000`

### Déploiement sur le cloud

#### Heroku

1. **Installer l'outil CLI Heroku**
   Suivez les instructions sur [le site officiel de Heroku](https://devcenter.heroku.com/articles/heroku-cli)

2. **Se connecter à Heroku**
   ```bash
   heroku login
   ```

3. **Créer une application Heroku**
   ```bash
   heroku create noteia-app
   ```

4. **Ajouter une base de données PostgreSQL**
   ```bash
   heroku addons:create heroku-postgresql:hobby-dev
   ```

5. **Configurer les variables d'environnement**
   ```bash
   heroku config:set SECRET_KEY=votre_cle_secrete_django
   heroku config:set OPENROUTER_API_KEY=votre_cle_openrouter
   ```

6. **Déployer l'application**
   ```bash
   git push heroku master
   ```

7. **Appliquer les migrations**
   ```bash
   heroku run python manage.py migrate
   ```

8. **Ouvrir l'application**
   ```bash
   heroku open
   ```

## Configuration des API d'IA

NoteIA utilise plusieurs fournisseurs d'API d'IA pour générer des résumés, des quiz et alimenter l'assistant Eden. Voici comment configurer ces API :

### Compte administrateur

Un compte administrateur est automatiquement créé lors du premier démarrage de l'application avec les identifiants suivants :
- **Nom d'utilisateur** : root45
- **Mot de passe** : soleillevant

Connectez-vous avec ces identifiants pour accéder à la page de configuration des API.

### Configuration des clés API

1. **Connectez-vous** avec le compte administrateur
2. Cliquez sur l'**icône de profil** en haut à droite
3. Sélectionnez "**Configuration des API**"
4. Pour chaque fournisseur d'API, entrez votre clé API dans le champ correspondant

### Obtention des clés API

#### OpenRouter

1. Créez un compte sur [OpenRouter](https://openrouter.ai/)
2. Accédez à la page "API Keys" dans votre tableau de bord
3. Créez une nouvelle clé API
4. Copiez la clé et insérez-la dans NoteIA

#### DeepSeek

1. Inscrivez-vous sur [DeepSeek](https://platform.deepseek.com/)
2. Accédez aux paramètres de votre compte et à la section API
3. Générez une nouvelle clé API
4. Copiez la clé et insérez-la dans NoteIA

#### OpenAI

1. Créez un compte sur [OpenAI](https://platform.openai.com/)
2. Accédez à la section "API Keys"
3. Cliquez sur "Create new secret key"
4. Copiez la clé et insérez-la dans NoteIA

### Gestion des modèles

Dans la page de configuration des API, vous pouvez :
- **Activer/désactiver** des modèles spécifiques
- **Définir un modèle par défaut** pour chaque fournisseur
- **Ajouter de nouveaux modèles** personnalisés
- **Rafraîchir** la liste des modèles disponibles

Par défaut, NoteIA utilise le modèle gratuit "DeepSeek R1" via OpenRouter si aucun autre modèle n'est activé.

## Utilisation de l'application

### Création d'un compte

1. Accédez à la page d'inscription
2. Remplissez vos informations personnelles
3. Notez le nom d'utilisateur généré et votre mot de passe
4. Connectez-vous avec ces identifiants

### Création de cours et notes

1. Depuis le tableau de bord, créez un nouveau cours
2. Dans le cours, créez une nouvelle note
3. Ajoutez du contenu à la note (texte, images, PDF, etc.)

### Utilisation des fonctionnalités IA

1. **Génération de résumé** : Dans une note contenant du texte, cliquez sur "Générer un résumé"
2. **Création de quiz** : Dans une note, cliquez sur "Générer un quiz"
3. **Assistant Eden** : Utilisez le bouton flottant ou accédez au tableau de bord Eden

## Structure du projet

```
noteia/
├── landing/                # Application principale
│   ├── models.py           # Modèles de données
│   ├── views.py            # Vues et logique
│   ├── urls.py             # Définition des URLs
│   └── templates/          # Templates HTML
├── noteIA/                 # Configuration du projet Django
│   ├── settings.py         # Paramètres du projet
│   ├── urls.py             # URLs du projet
│   └── wsgi.py             # Configuration WSGI
├── static/                 # Fichiers statiques
│   ├── css/                # Styles CSS
│   ├── js/                 # Scripts JavaScript
│   └── img/                # Images
├── media/                  # Fichiers uploadés par les utilisateurs
├── requirements.txt        # Dépendances du projet
└── manage.py               # Script de gestion Django
```

## Contribution

Les contributions sont les bienvenues ! Veuillez suivre ces étapes :
1. Forkez le projet
2. Créez une branche pour votre fonctionnalité (`git checkout -b feature/amazing-feature`)
3. Committez vos changements (`git commit -m 'Add some amazing feature'`)
4. Poussez vers la branche (`git push origin feature/amazing-feature`)
5. Ouvrez une Pull Request

## Licence

Ce projet est sous licence [MIT](LICENSE).

## Contact

Pour toute question ou assistance, veuillez ouvrir une issue sur GitHub ou contacter l'équipe de développement à l'adresse jonathankonde430@gmail.com. 