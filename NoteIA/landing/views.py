import random
from django.shortcuts import render, redirect
from django.contrib import messages
from .models import CustomUser, Contact, Cours,Note,Collaborateur,TextNote
import jwt
import os
import datetime
from django.conf import settings

from django.shortcuts import get_object_or_404

JWT_SECRET = os.environ.get('JWT_SECRET', 'lumiere_du_monde')
JWT_ALGORITHM = 'HS256'
JWT_EXP_DELTA_SECONDS = 3600  # 1 heure

def index(request):
    return render(request, 'landing/index.html')

def login(request):
    if request.method == "POST":
        identifiant = request.POST.get('identifiant')
        password = request.POST.get('password')
        user = None

        # Essayer de récupérer par username
        try:
            user = CustomUser.objects.get(username=identifiant)
        except CustomUser.DoesNotExist:
            # Sinon, essayer par numéro de téléphone
            try:
                contact = Contact.objects.get(tel=identifiant)
                user = CustomUser.objects.get(contact=contact)
            except (Contact.DoesNotExist, CustomUser.DoesNotExist):
                user = None

        if not user or not user.check_password(password):
            messages.error(request, "Identifiants invalides.")
            return render(request, 'landing/login.html')

        # Génération du JWT
        payload = {
            'user_id': user.id,
            'exp': datetime.datetime.utcnow() + datetime.timedelta(seconds=JWT_EXP_DELTA_SECONDS)
        }
        token = jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)

        response = redirect('dashboard')
        response.set_cookie('jwt', token)
        messages.success(request, "Connexion réussie !")
        return response

    return render(request, 'landing/login.html')


def logout(request):
    response = redirect('login')
    response.delete_cookie('jwt')
    messages.success(request, "Vous êtes déconnecté.")
    return response

def account_success(request):
    username = request.session.get('new_username')
    raw_password = request.session.get('new_password')
    if not username or not raw_password:
        return redirect('signup')
    # Optionnel : on peut supprimer ces informations de la session ensuite
    # request.session.pop('new_username')
    # request.session.pop('new_password')
    context = {
        'username': username,
        'password': raw_password,
    }
    return render(request, 'landing/success-compte.html', context)


def generate_username(prenom, nom):
    base_username = f"{prenom.capitalize()}{nom.capitalize()}"
    # On ajoute un nombre aléatoire à 4 chiffres
    random_number = random.randint(1000, 9999)
    return f"{base_username}{random_number}"

def signup(request):
    if request.method == "POST":
        nom = request.POST.get('nom')
        postnom = request.POST.get('postnom')
        prenom = request.POST.get('prenom')
        sexe = request.POST.get('sexe')
        tel = request.POST.get('tel')
        adresse = request.POST.get('adresse')
        password = request.POST.get('password')

        # Vérification de l'unicité du téléphone
        if Contact.objects.filter(tel=tel).exists():
            messages.error(request, "Téléphone déjà utilisé.")
            return render(request, 'landing/signup.html')

        # Création du contact
        contact = Contact.objects.create(
            nom=nom,
            postnom=postnom,
            prenom=prenom,
            sexe=sexe,
            adresse=adresse,
            tel=tel
        )

        # Génération et vérification de l'unicité du username
        username = generate_username(prenom, nom)
        while CustomUser.objects.filter(username=username).exists():
            username = generate_username(prenom, nom)

        # Création de l'utilisateur avec le mot de passe chiffré
        user = CustomUser(contact=contact, username=username)
        user.set_password(password)
        user.save()

        messages.success(request, f"Compte créé avec succès !")
        
        # Stocker le username et le mot de passe dans la session pour affichage
        request.session['new_username'] = username
        request.session['new_password'] = password
        
        return redirect('account_success')
    return render(request, 'landing/signup.html')


def dashboard(request):
    token = request.COOKIES.get('jwt')
    if not token:
        messages.error(request, "Vous devez être connecté pour accéder au dashboard.")
        return redirect('login')

    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        user = CustomUser.objects.get(id=payload['user_id'])
        context = {'user_contact': user.contact}
    except jwt.ExpiredSignatureError:
        # Le token a expiré, on supprime le cookie et on redirige avec le message
        messages.error(request, "Votre session a expiré. Veuillez vous reconnecter.")
        response = redirect('login')
        response.delete_cookie('jwt')
        return response
    except (jwt.InvalidTokenError, CustomUser.DoesNotExist):
        messages.error(request, "Session invalide. Veuillez vous reconnecter.")
        response = redirect('login')
        response.delete_cookie('jwt')
        return response

    return render(request, 'landing/dashboard.html', context)

def get_current_user(request):
    token = request.COOKIES.get('jwt')
    if not token:
        return None
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        return CustomUser.objects.get(id=payload['user_id'])
    except (jwt.ExpiredSignatureError, jwt.InvalidTokenError, CustomUser.DoesNotExist):
        return None

def edit_course(request, course_id):
    user = get_current_user(request)
    if not user:
        messages.error(request, "Vous devez être connecté pour modifier un cours.")
        return redirect('login')
    course = get_object_or_404(Cours, id=course_id, user=user)
    if request.method == "POST":
        course.nom = request.POST.get('nom')
        course.description = request.POST.get('description')
        course.save()
        messages.success(request, "Cours modifié avec succès !")
        return redirect('list_courses')
    return render(request, 'landing/edit_course.html', {'course': course})


def delete_course(request, course_id):
    user = get_current_user(request)
    if not user:
        messages.error(request, "Vous devez être connecté pour supprimer un cours.")
        return redirect('login')
    
    course = get_object_or_404(Cours, id=course_id, user=user)
    
    if request.method == "POST":
        course.delete()
        messages.success(request, "Cours supprimé avec succès !")
        return redirect('list_courses')
    
    # En GET, on affiche la page de confirmation
    return render(request, 'landing/confirm_delete_course.html', {'course': course})

def list_courses(request):
    user = get_current_user(request)
    if not user:
        messages.error(request, "Vous devez être connecté pour voir vos cours.")
        return redirect('login')
    courses = Cours.objects.filter(user=user)
    context = {
        'courses': courses,
        'user_contact': user.contact  # Ajout de la variable pour le template
    }
    return render(request, 'landing/list_courses.html', context)



def create_course(request):
    user = get_current_user(request)
    if not user:
        messages.error(request, "Vous devez être connecté pour créer un cours.")
        return redirect('login')
    
    if request.method == "POST":
        nom = request.POST.get('nom', '').strip()
        description = request.POST.get('description', '').strip()
        
        # Vérifier que le nom a été fourni
        if not nom:
            messages.error(request, "Veuillez insérer le nom du cours.")
            return render(request, 'landing/create_course.html', {'user_contact': user.contact})
        
        # Vérifier qu'un cours avec ce nom n'existe pas déjà pour cet utilisateur
        if Cours.objects.filter(nom__iexact=nom, user=user).exists():
            messages.error(request, "Vous avez déjà créé ce cours.")
            return render(request, 'landing/create_course.html', {'user_contact': user.contact})
        
        # Créer le cours si toutes les validations sont passées
        Cours.objects.create(nom=nom, description=description, user=user)
        messages.success(request, "Cours créé avec succès !")
        return redirect('list_courses')
    
    context = {
        'user_contact': user.contact  # Ajout de la variable pour le template
    }
    return render(request, 'landing/create_course.html', context)



def select_course_for_note(request):
    """
    Affiche la liste des cours sous forme de cartes pour que l'utilisateur
    choisisse dans lequel créer une note.
    """
    user = get_current_user(request)
    if not user:
        messages.error(request, "Vous devez être connecté pour créer une note.")
        return redirect('login')
    courses = Cours.objects.filter(user=user)
    context = {
        'courses': courses,
        'user_contact': user.contact
    }
    return render(request, 'landing/select_course_for_note.html', context)


def list_notes(request, course_id):
    user = get_current_user(request)
    if not user:
        messages.error(request, "Vous devez être connecté pour voir les notes.")
        return redirect('login')
    course = get_object_or_404(Cours, id=course_id, user=user)
    notes = Note.objects.filter(cours=course, userOwner=user)
    context = {
        'course': course,
        'notes': notes,
        'user_contact': user.contact
    }
    return render(request, 'landing/list_notes.html', context)


def create_note(request, course_id):
    user = get_current_user(request)
    if not user:
        messages.error(request, "Vous devez être connecté pour créer une note.")
        return redirect('login')
    course = get_object_or_404(Cours, id=course_id, user=user)
    
    if request.method == "POST":
        titre = request.POST.get('titre', '').strip()
        if not titre:
            messages.error(request, "Veuillez insérer un titre pour la note.")
            return render(request, 'landing/create_note.html', {'course': course, 'user_contact': user.contact})
        # Vérifier l'unicité du titre pour cet utilisateur et ce cours
        if Note.objects.filter(titre__iexact=titre, cours=course, userOwner=user).exists():
            messages.error(request, "Vous avez déjà créé une note avec ce titre dans ce cours.")
            return render(request, 'landing/create_note.html', {'course': course, 'user_contact': user.contact})
        # Créer la note
        Note.objects.create(titre=titre, cours=course, userOwner=user)
        messages.success(request, "Note créée avec succès !")
        return redirect('list_notes', course_id=course.id)
    
    return render(request, 'landing/create_note.html', {'course': course, 'user_contact': user.contact})


def note_detail(request, note_id):
    user = get_current_user(request)
    if not user:
        messages.error(request, "Vous devez être connecté pour voir cette note.")
        return redirect('login')
    note = get_object_or_404(Note, id=note_id)
    # Autoriser la consultation si l'utilisateur est owner ou collaborateur
    is_collaborator = Collaborateur.objects.filter(note=note, userCollab=user).exists()
    if note.userOwner != user and not is_collaborator:
        messages.error(request, "Vous n'avez pas accès à cette note.")
        return redirect('dashboard')
    textnotes = TextNote.objects.filter(note=note)
    # Récupérer les collaborateurs pour l'affichage (pour le owner)
    collaborators = Collaborateur.objects.filter(note=note)
    context = {
        'note': note,
        'textnotes': textnotes,
        'collaborators': collaborators,
        'user_contact': note.userOwner.contact if note.userOwner == user else user.contact,
        'is_owner': note.userOwner == user
    }
    return render(request, 'landing/note_detail.html', context)


def create_textnote(request, note_id):
    user = get_current_user(request)
    if not user:
        messages.error(request, "Vous devez être connecté pour créer un texte.")
        return redirect('login')
    note = get_object_or_404(Note, id=note_id)
    # Autoriser la création si l'utilisateur est owner ou collaborateur
    is_collaborator = Collaborateur.objects.filter(note=note, userCollab=user).exists()
    if note.userOwner != user and not is_collaborator:
        messages.error(request, "Vous n'avez pas le droit d'éditer cette note.")
        return redirect('dashboard')
    
    if request.method == "POST":
        texte = request.POST.get('texte', '').strip()
        if not texte:
            messages.error(request, "Le texte ne peut pas être vide.")
            return render(request, 'landing/create_textnote.html', {'note': note, 'user_contact': user.contact})
        TextNote.objects.create(note=note, texte=texte, userEditeur=user)
        messages.success(request, "Texte ajouté avec succès !")
        return redirect('note_detail', note_id=note.id)
    
    return render(request, 'landing/create_textnote.html', {'note': note, 'user_contact': user.contact})


def invite_collaborators(request, note_id):
    user = get_current_user(request)
    if not user:
        messages.error(request, "Vous devez être connecté pour inviter des collaborateurs.")
        return redirect('login')
    note = get_object_or_404(Note, id=note_id, userOwner=user)
    
    if request.method == "POST":
        # On attend une liste d'identifiants d'utilisateurs (par exemple via POST, séparés par une virgule)
        collaborators_input = request.POST.get('collaborators', '')
        # Par exemple, on suppose que l'entrée est de la forme "@user1,@user2" ou des numéros
        collaborator_identifiers = [item.strip() for item in collaborators_input.split(',') if item.strip()]
        added = []
        for ident in collaborator_identifiers:
            # Rechercher par username ou tel (si ident commence par @, on cherche par username)
            try:
                if ident.startswith('@'):
                    # Enlever le '@'
                    target_user = CustomUser.objects.get(username__iexact=ident[1:])
                else:
                    target_user = CustomUser.objects.get(contact__tel=ident)
                # Ne pas inviter le créateur lui-même
                if target_user == user:
                    continue
                # Vérifier que ce collaborateur n'est pas déjà invité
                if not Collaborateur.objects.filter(note=note, userCollab=target_user).exists():
                    Collaborateur.objects.create(note=note, userCollab=target_user)
                    added.append(target_user.username)
            except CustomUser.DoesNotExist:
                continue
        if added:
            messages.success(request, f"Collaborateur(s) {', '.join(added)} invité(s) avec succès.")
        else:
            messages.error(request, "Aucun collaborateur n'a été ajouté.")
        return redirect('note_detail', note_id=note.id)
    
    return render(request, 'landing/invite_collaborators.html', {'note': note, 'user_contact': user.contact})


def custom_404(request, exception):
    return render(request, 'landing/404.html', status=404)

def custom_500(request):
    return render(request, 'landing/500.html', status=500)

