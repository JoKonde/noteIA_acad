import random
from django.shortcuts import render, redirect
from django.contrib import messages
from .models import CustomUser, Contact, Cours,Note,Collaborateur,TextNote,ImageNote,PdfNote,TextNoteResume,QuizNote,EdenConversation,EdenMessage,AudioNote,VideoNote,OcrNote, AIProvider, APIKey, AIModel
import jwt
import os
import datetime
import json
import requests
from django.conf import settings
from django.db.models import Q
from django.utils import timezone
from django.shortcuts import get_object_or_404
from django.http import JsonResponse
import markdown
from dotenv import load_dotenv
import re
import base64

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

    # Tous les cours où je suis owner ou où je suis invité (via une note)
    cours_qs = Cours.objects.filter(
        Q(user=user) | 
        Q(note__collaborateur__userCollab=user)
    ).distinct()

    # Préparer la liste annotée
    course_list = []
    for cours in cours_qs:
        invited = (cours.user != user)
        course_list.append({
            'cours': cours,
            'invited': invited
        })

    return render(request, 'landing/list_courses.html', {
        'course_list': course_list,
        'user_contact': user.contact
    })



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

    cours = get_object_or_404(Cours, id=course_id)
     # Est-ce que je suis invité (non propriétaire) pour ce cours ?
    course_invited = (cours.user != user)
    # Notes où je suis owner ou coéditeur
    notes_qs = Note.objects.filter(
        Q(cours=cours, userOwner=user) |
        Q(collaborateur__userCollab=user)
    ).distinct()

    notes_list = []
    for note in notes_qs:
        invited = (note.userOwner != user)
        notes_list.append({
            'note': note,
            'invited': invited
        })

    return render(request, 'landing/list_notes.html', {
        'course': cours,
        'notes_list': notes_list,
        'course_invited': course_invited,
        'user_contact': user.contact
    })

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
        messages.error(request, "Vous devez être connecté pour voir les détails d'une note.")
        return redirect('login')
    
    note = get_object_or_404(Note, id=note_id)
    
    # Vérifier si l'utilisateur est le propriétaire ou un collaborateur
    is_owner = note.userOwner == user
    is_collaborator = Collaborateur.objects.filter(note=note, userCollab=user).exists()
    
    if not (is_owner or is_collaborator):
        messages.error(request, "Vous n'êtes pas autorisé à voir cette note.")
        return redirect('dashboard')
    
    # Récupérer toutes les données de la note
    textnotes = TextNote.objects.filter(note=note).order_by('-date')
    imagenotes = ImageNote.objects.filter(note=note).order_by('-date')
    pdfnotes = PdfNote.objects.filter(note=note).order_by('-date')
    
    # Récupérer les données audio, vidéo et OCR
    audionotes = AudioNote.objects.filter(note=note).order_by('-date')
    videonotes = VideoNote.objects.filter(note=note).order_by('-date')
    ocrnotes = OcrNote.objects.filter(note=note).order_by('-date')
    
    # Récupérer les collaborateurs si l'utilisateur est le propriétaire
    collaborators = None
    if is_owner:
        collaborators = Collaborateur.objects.filter(note=note)
    
    context = {
        'note': note,
        'textnotes': textnotes,
        'imagenotes': imagenotes,
        'pdfnotes': pdfnotes,
        'audionotes': audionotes,
        'videonotes': videonotes,
        'ocrnotes': ocrnotes,
        'is_owner': is_owner,
        'invited': not is_owner and is_collaborator,
        'collaborators': collaborators
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

def edit_note(request, note_id):
    user = get_current_user(request)
    if not user:
        messages.error(request, "Vous devez être connecté pour modifier une note.")
        return redirect('login')

    note = get_object_or_404(Note, id=note_id, userOwner=user)
    if request.method == "POST":
        titre = request.POST.get('titre', '').strip()
        if not titre:
            messages.error(request, "Le titre ne peut pas être vide.")
            return render(request, 'landing/edit_note.html', {
                'note': note,
                'user_contact': user.contact
            })
        # Vérifier unicité du titre dans ce cours
        if Note.objects.filter(
            titre__iexact=titre,
            cours=note.cours,
            userOwner=user
        ).exclude(id=note.id).exists():
            messages.error(request, "Vous avez déjà une note avec ce titre dans ce cours.")
            return render(request, 'landing/edit_note.html', {
                'note': note,
                'user_contact': user.contact
            })
        note.titre = titre
        note.save()
        messages.success(request, "Note modifiée avec succès !")
        return redirect('list_notes', course_id=note.cours.id)

    return render(request, 'landing/edit_note.html', {
        'note': note,
        'user_contact': user.contact
    })

def delete_note(request, note_id):
    user = get_current_user(request)
    if not user:
        messages.error(request, "Vous devez être connecté pour supprimer une note.")
        return redirect('login')

    note = get_object_or_404(Note, id=note_id, userOwner=user)
    if request.method == "POST":
        course_id = note.cours.id
        note.delete()
        messages.success(request, "Note supprimée avec succès !")
        return redirect('list_notes', course_id=course_id)

    # GET → confirmation
    return render(request, 'landing/confirm_delete_note.html', {
        'note': note,
        'user_contact': user.contact
    })




def create_imagenote(request, note_id):
    user = get_current_user(request)
    if not user:
        messages.error(request, "Vous devez être connecté pour ajouter une image.")
        return redirect('login')

    note = get_object_or_404(Note, id=note_id)
    # autorisation owner ou collaborateur
    is_collab = Collaborateur.objects.filter(note=note, userCollab=user).exists()
    if note.userOwner != user and not is_collab:
        messages.error(request, "Vous n'avez pas le droit d'ajouter une image à cette note.")
        return redirect('dashboard')

    if request.method == "POST":
        uploaded = request.FILES.get('image')
        if not uploaded:
            messages.error(request, "Veuillez sélectionner une image.")
            return render(request, 'landing/create_imagenote.html', {'note': note, 'user_contact': user.contact})

         # Extension et nom de fichier unique
        ext = os.path.splitext(uploaded.name)[1]
        filename = f"{note.id}_{int(timezone.now().timestamp())}{ext}"

        # Répertoire de destination : landing/templates/landing/assets/img
        assets_dir = os.path.join(settings.BASE_DIR, 'landing', 'templates', 'landing', 'assets', 'img')
        os.makedirs(assets_dir, exist_ok=True)

        save_path = os.path.join(assets_dir, filename)
        rel_path = f"img/{filename}"


        # Sauvegarder le fichier sur le disque
        with open(save_path, 'wb') as f:
            for chunk in uploaded.chunks():
                f.write(chunk)

        # Enregistrer en base
        ImageNote.objects.create(note=note, path=rel_path, userEditeur=user)
        messages.success(request, "Image ajoutée avec succès !")
        return redirect('note_detail', note_id=note.id)

    return render(request, 'landing/create_imagenote.html', {'note': note, 'user_contact': user.contact})

def delete_imagenote(request, image_id):
    user = get_current_user(request)
    if not user:
        messages.error(request, "Vous devez être connecté pour supprimer une image.")
        return redirect('login')

    img = get_object_or_404(ImageNote, id=image_id)
    note = img.note

    # Vérification d'accès : owner ou collaborateur
    is_owner = note.userOwner == user
    is_collab = Collaborateur.objects.filter(note=note, userCollab=user).exists()
    if not (is_owner or is_collab):
        messages.error(request, "Vous n'avez pas le droit de supprimer cette image.")
        return redirect('note_detail', note_id=note.id)

    if request.method == "POST":
        # Construire le chemin réel du fichier
        file_path = os.path.join(
            settings.BASE_DIR,
            'landing', 'templates', 'landing', 'assets',
            img.path.replace('img/', 'img' + os.sep)  # adapte les slashes
        )
        # Supprimer le fichier s'il existe
        if os.path.exists(file_path):
            os.remove(file_path)
        # Supprimer l'enregistrement
        img.delete()
        messages.success(request, "Image supprimée avec succès !")
        return redirect('note_detail', note_id=note.id)

    # Si on tombe ici en GET, on renvoie simplement au détail
    return redirect('note_detail', note_id=note.id)


def create_pdfnote(request, note_id):
    user = get_current_user(request)
    if not user:
        messages.error(request, "Connectez-vous pour ajouter un PDF.")
        return redirect('login')

    note = get_object_or_404(Note, id=note_id)
    # Autorisation owner ou collaborateur
    is_collab = Collaborateur.objects.filter(note=note, userCollab=user).exists()
    if note.userOwner != user and not is_collab:
        messages.error(request, "Vous n'avez pas le droit d'ajouter un PDF à cette note.")
        return redirect('dashboard')

    if request.method == "POST":
        uploaded = request.FILES.get('pdf')
        if not uploaded or not uploaded.name.lower().endswith('.pdf'):
            messages.error(request, "Veuillez sélectionner un fichier PDF.")
            return render(request, 'landing/create_pdfnote.html', {
                'note': note,
                'user_contact': user.contact
            })

        # Générer un nom unique
        ext = '.pdf'
        filename = f"{note.id}_{int(timezone.now().timestamp())}{ext}"

        # Chemin de sauvegarde : landing/templates/landing/assets/pdf
        assets_dir = os.path.join(
            settings.BASE_DIR,
            'landing', 'templates', 'landing', 'assets', 'pdf'
        )
        os.makedirs(assets_dir, exist_ok=True)

        save_path = os.path.join(assets_dir, filename)
        rel_path = f"pdf/{filename}"

        # Sauvegarde du fichier
        with open(save_path, 'wb') as f:
            for chunk in uploaded.chunks():
                f.write(chunk)

        # Enregistrement en base
        PdfNote.objects.create(
            note=note,
            path=rel_path,
            userEditeur=user
        )
        messages.success(request, "PDF ajouté avec succès !")
        return redirect('note_detail', note_id=note.id)

    return render(request, 'landing/create_pdfnote.html', {
        'note': note,
        'user_contact': user.contact
    })


def delete_pdfnote(request, pdf_id):
    user = get_current_user(request)
    if not user:
        messages.error(request, "Connectez-vous pour supprimer un PDF.")
        return redirect('login')

    pdf = get_object_or_404(PdfNote, id=pdf_id)
    note = pdf.note

    # Autorisation owner ou collaborateur
    is_owner = (note.userOwner == user)
    is_collab = Collaborateur.objects.filter(note=note, userCollab=user).exists()
    if not (is_owner or is_collab):
        messages.error(request, "Vous n'avez pas le droit de supprimer ce PDF.")
        return redirect('note_detail', note_id=note.id)

    if request.method == "POST":
        # Supprime le fichier sur le disque
        file_path = os.path.join(
            settings.BASE_DIR,
            'landing', 'templates', 'landing', 'assets', pdf.path.replace('/', os.sep)
        )
        if os.path.exists(file_path):
            os.remove(file_path)
        pdf.delete()
        messages.success(request, "PDF supprimé avec succès !")
        return redirect('note_detail', note_id=note.id)

    # Pas de page de confirmation dédiée, on redirige
    return redirect('note_detail', note_id=note.id)


def custom_404(request, exception):
    return render(request, 'landing/404.html', status=404)

def custom_500(request):
    return render(request, 'landing/500.html', status=500)

def generate_resume(request, note_id):
    user = get_current_user(request)
    if not user:
        messages.error(request, "Vous devez être connecté pour générer un résumé.")
        return redirect('login')
    
    note = get_object_or_404(Note, id=note_id)
    
    # Vérifier si l'utilisateur est le propriétaire ou un collaborateur
    is_owner = note.userOwner == user
    is_collaborator = Collaborateur.objects.filter(note=note, userCollab=user).exists()
    
    if not (is_owner or is_collaborator):
        messages.error(request, "Vous n'êtes pas autorisé à générer un résumé pour cette note.")
        return redirect('dashboard')
    
    # Récupérer tous les textes de la note
    textnotes = TextNote.objects.filter(note=note).order_by('date')
    
    if not textnotes:
        messages.error(request, "Il n'y a pas de texte à résumer dans cette note.")
        return redirect('note_detail', note_id=note_id)
    
    # Concaténer tous les textes
    all_texts = "\n\n".join([tn.texte for tn in textnotes])
    
    # Limiter à 6000 caractères pour éviter de dépasser les limites de l'API
    if len(all_texts) > 6000:
        all_texts = all_texts[:6000] + "..."
    
    # Préparer le prompt pour le résumé avec instructions spécifiques pour les formules mathématiques
    prompt = f"""Fais un résumé concis et structuré du texte suivant. Identifie et mets en évidence les points clés.

Si le texte contient des formules mathématiques, physiques ou électriques, formate-les correctement pour MathJax en utilisant ces règles:
1. Pour les formules en ligne, utilise $...$ (par exemple: $x^2 + y^2 = r^2$)
2. Pour les formules centrées sur leur propre ligne, utilise $$...$$ (par exemple: $$\\frac{{dx}}{{dt}} = v$$)
3. Pour les formules de physique et d'électricité, utilise les conventions LaTeX appropriées:
   - Vecteurs: $\\vec{{E}}$ pour un champ électrique
   - Unités: $\\text{{V}}$, $\\text{{A}}$, $\\text{{W}}$, $\\Omega$, $\\text{{F}}$, $\\text{{H}}$
   - Constantes: $\\varepsilon_0$ pour la permittivité du vide
   - Indices et exposants: $R_{{eq}}$ pour résistance équivalente
   - Dérivées partielles: $\\frac{{\\partial V}}{{\\partial x}}$
   - Intégrales: $\\oint_S \\vec{{E}} \\cdot d\\vec{{S}}$ pour le flux électrique
4. Utilise la syntaxe LaTeX standard pour toutes les expressions mathématiques
5. N'utilise pas \\[ et \\] ou \\( et \\)

Voici le texte à résumer:

{all_texts}"""
    
    try:
        # Re-charger les variables d'environnement pour s'assurer qu'elles sont disponibles
        load_dotenv()
        
        # Récupérer le modèle actif et la clé API
        model = get_active_ai_model('openrouter')
        if not model:
            messages.error(request, "Aucun modèle d'IA n'est configuré. Veuillez configurer un modèle dans les paramètres.")
            return redirect('note_detail', note_id=note_id)
        
        api_key = get_api_key('openrouter')
        if not api_key:
            messages.error(request, "Clé API non configurée. Veuillez configurer une clé API dans les paramètres.")
            return redirect('note_detail', note_id=note_id)
        
        # Préparation de la requête à l'API
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        
        data = {
            "model": model.model_id,
            "messages": [
                {
                    "role": "user",
                    "content": prompt
                }
            ]
        }
        
        # Déterminer l'URL de l'API à partir du fournisseur
        url_api = model.provider.url_api
        
        # Envoi de la requête
        response = requests.post(
            url_api,
            headers=headers,
            json=data
        )
        
        # Récupération de la réponse
        if response.status_code == 200:
            result = response.json()
            resume_text = result["choices"][0]["message"]["content"]
            
            # Convertir le résumé Markdown en HTML tout en préservant les formules mathématiques
            # On utilise une méthode qui préserve les formules $ et $$
            resume_text = markdown.markdown(resume_text)
            
            # Déterminer la version du résumé
            latest_version = TextNoteResume.objects.filter(note=note, userEditeur=user).order_by('-version').first()
            version = 1 if not latest_version else latest_version.version + 1
            # Enregistrer le résumé
            resume = TextNoteResume(
                note=note,
                texte=resume_text,
                userEditeur=user,
                version=version
            )
            resume.save()
            
            messages.success(request, "Résumé généré avec succès !")
            return redirect('view_resumes', note_id=note_id)
        else:
            messages.error(request, f"Erreur lors de la génération du résumé: {response.text}")
            return redirect('note_detail', note_id=note_id)
            
    except Exception as e:
        messages.error(request, f"Erreur: {str(e)}")
        return redirect('note_detail', note_id=note_id)

def view_resumes(request, note_id):
    user = get_current_user(request)
    if not user:
        messages.error(request, "Vous devez être connecté pour voir les résumés.")
        return redirect('login')
    
    note = get_object_or_404(Note, id=note_id)
    
    # Vérifier si l'utilisateur est le propriétaire ou un collaborateur
    is_owner = note.userOwner == user
    is_collaborator = Collaborateur.objects.filter(note=note, userCollab=user).exists()
    
    if not (is_owner or is_collaborator):
        messages.error(request, "Vous n'êtes pas autorisé à voir les résumés de cette note.")
        return redirect('dashboard')
    
    # Récupérer tous les résumés de la note
    resumes = TextNoteResume.objects.filter(note=note).order_by('-date')
    
    context = {
        'note': note,
        'resumes': resumes,
        'is_owner': is_owner,
        'is_collaborator': is_collaborator
    }
    
    return render(request, 'landing/view_resumes.html', context)

def delete_resume(request, resume_id):
    user = get_current_user(request)
    if not user:
        messages.error(request, "Vous devez être connecté pour supprimer un résumé.")
        return redirect('login')
    
    resume = get_object_or_404(TextNoteResume, id=resume_id)
    note = resume.note
    
    # Vérifier si l'utilisateur est le propriétaire du résumé
    if resume.userEditeur != user:
        messages.error(request, "Vous n'êtes pas autorisé à supprimer ce résumé.")
        return redirect('view_resumes', note_id=note.id)
    
    if request.method == "POST":
        resume.delete()
        messages.success(request, "Résumé supprimé avec succès !")
        
    return redirect('view_resumes', note_id=note.id)

def generate_quiz(request, note_id):
    user = get_current_user(request)
    if not user:
        messages.error(request, "Vous devez être connecté pour générer un quiz.")
        return redirect('login')
    
    note = get_object_or_404(Note, id=note_id)
    
    # Vérifier si l'utilisateur est le propriétaire ou un collaborateur
    is_owner = note.userOwner == user
    is_collaborator = Collaborateur.objects.filter(note=note, userCollab=user).exists()
    
    if not (is_owner or is_collaborator):
        messages.error(request, "Vous n'êtes pas autorisé à générer un quiz pour cette note.")
        return redirect('dashboard')
    
    # Récupérer tous les textes de la note
    textnotes = TextNote.objects.filter(note=note).order_by('date')
    
    if not textnotes:
        messages.error(request, "Il n'y a pas de texte pour générer un quiz dans cette note.")
        return redirect('note_detail', note_id=note_id)
    
    # Concaténer tous les textes
    all_texts = "\n\n".join([tn.texte for tn in textnotes])
    
    # Limiter à 6000 caractères pour éviter de dépasser les limites de l'API
    if len(all_texts) > 6000:
        all_texts = all_texts[:6000] + "..."
    
    # Prompt qui demande un quiz basé sur le contenu des notes
    prompt = f"""Génère un quiz basé sur le texte suivant. 
Le quiz doit inclure AU MOINS 10 questions variées directement liées au contenu du texte.

Utilise les types de questions suivants (dans cet ordre exact):
1. Questions à réponse texte libre (3 questions)
2. Questions à choix multiples (4 questions)
3. Questions oui/non (1 question)
4. Questions vrai/faux (2 questions)

Pour chaque question, utilise le format suivant (très important):

Question: [texte de la question]
Type: [texte, qcm, oui_non, vrai_faux]
Options: [liste des options séparées par des sauts de ligne, seulement pour qcm]
Réponse: [réponse correcte]
Explication: [explication brève]

Pour les formules mathématiques ou scientifiques, utilise la notation LaTeX entre $ $ (exemple: $E=mc^2$).
N'UTILISE PAS de format JSON.

Voici le texte:
{all_texts}"""
    
    try:
        # Re-charger les variables d'environnement
        load_dotenv()
        
        # Récupérer le modèle actif et la clé API
        model = get_active_ai_model('openrouter')
        if not model:
            messages.error(request, "Aucun modèle d'IA n'est configuré. Veuillez configurer un modèle dans les paramètres.")
            return redirect('note_detail', note_id=note_id)
        
        api_key = get_api_key('openrouter')
        if not api_key:
            messages.error(request, "Clé API non configurée. Veuillez configurer une clé API dans les paramètres.")
            return redirect('note_detail', note_id=note_id)
        
        # Préparation de la requête
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        
        data = {
            "model": model.model_id,
            "messages": [
                {
                    "role": "user",
                    "content": prompt
                }
            ]
        }
        
        # Déterminer l'URL de l'API à partir du fournisseur
        url_api = model.provider.url_api
        
        # Envoi de la requête
        response = requests.post(
            url_api,
            headers=headers,
            json=data
        )
        
        if response.status_code == 200:
            result = response.json()
            content = result["choices"][0]["message"]["content"]
            
            # Analyser le contenu pour extraire les questions
            questions = parse_quiz_response(content, note.titre)
            
            if not questions:
                messages.error(request, "Erreur de format dans la génération du quiz. Veuillez réessayer.")
                return redirect('note_detail', note_id=note_id)
            
            # Déterminer la version
            latest_version = QuizNote.objects.filter(note=note, userEditeur=user).order_by('-version').first()
            version = 1 if not latest_version else latest_version.version + 1
            
            # Créer le quiz
            quiz = QuizNote(
                note=note,
                contenu=content,  # Stocker la réponse brute
                questions=json.dumps(questions),  # Stocker les questions parsées
                userEditeur=user,
                version=version
            )
            quiz.save()
            
            messages.success(request, f"Quiz généré avec succès avec {len(questions)} questions!")
            return redirect('view_quizzes', note_id=note_id)
            
        else:
            messages.error(request, f"Erreur lors de la génération du quiz: {response.text}")
            return redirect('note_detail', note_id=note_id)
            
    except Exception as e:
        messages.error(request, f"Erreur: {str(e)}")
        return redirect('note_detail', note_id=note_id)

def parse_quiz_response(response_text, note_title):
    """
    Parse la réponse de l'API pour extraire les questions.
    Retourne None si la réponse ne peut pas être parsée correctement.
    """
    try:
        # Analyse du texte pour extraire les questions manuellement
        questions = []
        # Pattern pour capturer les questions avec différents types
        pattern = r'(?:Question\s*(?:\d+)?[:.]\s*)(.*?)(?:\n\s*Type[:.]\s*(.*?)(?:\n\s*Options[:.]\s*(.*?))?(?:\n\s*Réponse[:.]\s*(.*?))\n\s*Explication[:.]\s*(.*?)(?=\n\s*(?:Question|$)))'
        
        question_matches = re.finditer(pattern, response_text, re.DOTALL | re.MULTILINE)
        
        for match in question_matches:
            question_text = match.group(1).strip()
            question_type = match.group(2).strip().lower() if match.group(2) else "qcm"
            options_text = match.group(3).strip() if match.group(3) else ""
            answer = match.group(4).strip() if match.group(4) else ""
            explanation = match.group(5).strip() if match.group(5) else ""
            
            # Normaliser le type de question
            if "vrai" in question_type or "faux" in question_type:
                question_type = "vrai_faux"
                options = ["Vrai", "Faux"]
            elif "oui" in question_type or "non" in question_type:
                question_type = "oui_non"
                options = ["Oui", "Non"]
            elif "texte" in question_type or "libre" in question_type:
                question_type = "texte"
                options = []
            else:
                question_type = "qcm"
                
                # Extraire les options pour QCM
                if options_text:
                    # Essayer de trouver des options avec des lettres (A., B., etc.)
                    option_matches = re.findall(r'(?:[A-D][.:]|[\-\*])\s*(.*?)(?=\s*(?:[A-D][.:]|[\-\*]|$))', options_text + " ")
                    if option_matches:
                        options = [opt.strip() for opt in option_matches]
                    else:
                        # Sinon, séparer par les sauts de ligne
                        options = [opt.strip() for opt in options_text.split('\n') if opt.strip()]
                else:
                    options = ["Option A", "Option B", "Option C", "Option D"]
                
                # S'assurer qu'il y a au moins 2 options
                while len(options) < 2:
                    options.append(f"Option {len(options) + 1}")
            
            # Ajouter la question seulement si nous avons un texte de question et une réponse
            if question_text and answer:
                questions.append({
                    "question": question_text,
                    "type": question_type,
                    "options": options,
                    "reponse": answer,
                    "explication": explanation
                })
        
        # Vérifier qu'on a extrait au moins une question valide
        if questions:
            return questions
        return None
    except Exception as e:
        print(f"Erreur lors du parsing: {str(e)}")
        return None

def view_quizzes(request, note_id):
    user = get_current_user(request)
    if not user:
        messages.error(request, "Vous devez être connecté pour voir les quiz.")
        return redirect('login')
    
    note = get_object_or_404(Note, id=note_id)
    
    # Vérifier si l'utilisateur est le propriétaire ou un collaborateur
    is_owner = note.userOwner == user
    is_collaborator = Collaborateur.objects.filter(note=note, userCollab=user).exists()
    
    if not (is_owner or is_collaborator):
        messages.error(request, "Vous n'êtes pas autorisé à voir les quiz de cette note.")
        return redirect('dashboard')
    
    # Récupérer tous les quiz de la note
    quizzes = QuizNote.objects.filter(note=note).order_by('-date')
    
    # Pour chaque quiz, extraire le titre du JSON s'il existe
    for quiz in quizzes:
        try:
            quiz_data = json.loads(quiz.contenu)
            quiz.titre = quiz_data.get('titre', f"Quiz {quiz.version}")
        except json.JSONDecodeError:
            quiz.titre = f"Quiz {quiz.version}"
    
    context = {
        'note': note,
        'quizzes': quizzes,
        'is_owner': is_owner,
        'is_collaborator': is_collaborator
    }
    
    return render(request, 'landing/view_quizzes.html', context)

def delete_quiz(request, quiz_id):
    user = get_current_user(request)
    if not user:
        messages.error(request, "Vous devez être connecté pour supprimer un quiz.")
        return redirect('login')
    
    quiz = get_object_or_404(QuizNote, id=quiz_id)
    note = quiz.note
    
    # Vérifier si l'utilisateur est le propriétaire du quiz
    if quiz.userEditeur != user:
        messages.error(request, "Vous n'êtes pas autorisé à supprimer ce quiz.")
        return redirect('view_quizzes', note_id=note.id)
    
    if request.method == "POST":
        quiz.delete()
        messages.success(request, "Quiz supprimé avec succès !")
        
    return redirect('view_quizzes', note_id=note.id)

def eden_chat(request):
    user = get_current_user(request)
    if not user:
        messages.error(request, "Vous devez être connecté pour utiliser Eden.")
        return redirect('login')
    
    # Récupérer ou créer une conversation
    conversation, created = EdenConversation.objects.get_or_create(
        user=user,
        defaults={'date_creation': timezone.now()}
    )
    
    # Mettre à jour la date de dernière interaction
    conversation.derniere_interaction = timezone.now()
    conversation.save()
    
    # Gérer la suppression de l'historique de conversation
    if 'clear' in request.GET and request.GET.get('clear') == 'true':
        # Supprimer tous les messages de la conversation
        EdenMessage.objects.filter(conversation=conversation).delete()
        messages.success(request, "L'historique de conversation a été effacé.")
        return redirect('eden_chat')
    
    if request.method == "POST":
        message_text = request.POST.get('message')
        
        if message_text:
            # Enregistrer le message de l'utilisateur
            user_message = EdenMessage.objects.create(
                conversation=conversation,
                est_assistant=False,
                contenu=message_text
            )
            
            # Générer et enregistrer la réponse d'Eden
            eden_response = generate_eden_response(user, message_text)
            eden_message = EdenMessage.objects.create(
                conversation=conversation,
                est_assistant=True,
                contenu=eden_response
            )
    
    # Récupérer tous les messages de la conversation (pas de limite à 30)
    messages_list = EdenMessage.objects.filter(conversation=conversation).order_by('date')
    
    return render(request, 'landing/eden_chat.html', {
        'messages': messages_list,
    })

def generate_eden_response(user, message):
    """Génère une réponse de l'assistant Eden en utilisant l'API OpenRouter"""
    try:
        # Détection des intentions de l'utilisateur
        # Si le message contient des commandes d'action, traiter avant d'envoyer à l'API
        intent, action_response = detect_user_intent(user, message)
        if action_response:
            return action_response
        
        # Re-charger les variables d'environnement pour s'assurer qu'elles sont disponibles
        load_dotenv()
        
        # Récupérer le modèle actif et la clé API
        model = get_active_ai_model('openrouter')
        if not model:
            return "Je suis désolé, mais je rencontre un problème technique. Aucun modèle d'IA n'est configuré."
        
        api_key = get_api_key('openrouter')
        if not api_key:
            return "Je suis désolé, mais je rencontre un problème technique. Ma clé API n'est pas configurée. Veuillez contacter l'administrateur."
        
        # Contexte système pour personnaliser Eden
        system_prompt = """Tu es Eden, l'assistant intelligent de l'application NoteIA, une plateforme de prise de notes collaborative avec des fonctionnalités d'IA.
Tu dois aider les utilisateurs à:
- Comprendre les fonctionnalités de NoteIA (création de notes, invitation de collaborateurs, génération de résumés et de quiz)
- Naviguer dans l'application
- Résoudre les problèmes techniques
- Comprendre comment utiliser l'IA dans leurs notes
- Gérer leurs données et les données partagées

Ton ton est amical, serviable et professionnel. Tu es spécialisé dans l'aide sur NoteIA uniquement.
Si l'utilisateur pose des questions non liées à NoteIA, rappelle-lui gentiment que tu es l'assistant de NoteIA.

Les principales fonctionnalités de NoteIA sont:
1. Création et gestion de cours
2. Création de notes (texte, image, PDF, audio, vidéo, OCR)
3. Invitation de collaborateurs pour co-éditer des notes
4. Génération de résumés de notes par IA
5. Génération de quiz interactifs par IA
6. Système d'authentification sécurisé

Si l'utilisateur demande de créer un cours, une note ou d'effectuer une action dans l'application, suggère-lui comment le faire via l'interface ou propose-lui de l'aider.
"""

        # Construire le message pour l'API
        data = {
            "model": model.model_id,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": message}
            ]
        }
        
        # Préparer les en-têtes
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        
        # Déterminer l'URL de l'API à partir du fournisseur
        url_api = model.provider.url_api
        
        # Envoi de la requête
        response = requests.post(
            url_api,
            headers=headers,
            json=data
        )
        
        # Traitement de la réponse
        if response.status_code == 200:
            result = response.json()
            return result["choices"][0]["message"]["content"]
        else:
            return f"Je suis désolé, mais je rencontre un problème technique. Erreur: {response.status_code}"
            
    except Exception as e:
        return f"Je suis désolé, mais je rencontre un problème technique. Erreur: {str(e)}"

def detect_user_intent(user, message):
    """
    Détecte l'intention de l'utilisateur et effectue des actions si nécessaire
    Retourne un tuple (intent, response) où response est None si aucune action n'a été effectuée
    """
    message_lower = message.lower()
    
    # Intention de création de cours
    if any(x in message_lower for x in ["créer un cours", "nouveau cours", "ajouter un cours"]):
        # Extraction du nom du cours à partir du message
        cours_name = extract_course_name(message)
        if cours_name:
            # Vérifier si un cours avec ce nom existe déjà
            if Cours.objects.filter(nom__iexact=cours_name, user=user).exists():
                return "create_course", f"Vous avez déjà un cours nommé '{cours_name}'. Voulez-vous en créer un autre avec un nom différent?"
            
            # Créer le cours
            Cours.objects.create(
                nom=cours_name,
                description=f"Cours créé via Eden le {timezone.now().strftime('%d/%m/%Y')}",
                user=user
            )
            return "create_course", f"J'ai créé le cours '{cours_name}' pour vous. Vous pouvez le retrouver dans la liste de vos cours."
        else:
            return "create_course", "Je serais ravi de vous aider à créer un cours. Pourriez-vous me dire quel nom vous souhaitez lui donner?"
    
    # Intention de création de note
    elif any(x in message_lower for x in ["créer une note", "nouvelle note", "ajouter une note"]):
        # On a besoin de connaître le cours pour la note
        course_id, course_name = extract_course_reference(message, user)
        if course_id:
            note_title = extract_note_title(message)
            if note_title:
                # Vérifier si une note avec ce titre existe déjà dans ce cours
                try:
                    course = Cours.objects.get(id=course_id)
                    if Note.objects.filter(titre__iexact=note_title, cours=course, userOwner=user).exists():
                        return "create_note", f"Vous avez déjà une note intitulée '{note_title}' dans le cours '{course.nom}'. Voulez-vous en créer une autre avec un titre différent?"
                    
                    # Créer la note
                    Note.objects.create(
                        titre=note_title,
                        cours=course,
                        userOwner=user
                    )
                    return "create_note", f"J'ai créé la note '{note_title}' dans le cours '{course.nom}'. Vous pouvez maintenant y ajouter du contenu."
                except Cours.DoesNotExist:
                    return "create_note", "Je n'ai pas trouvé le cours spécifié. Veuillez vérifier et réessayer."
            else:
                return "create_note", f"Pour créer une note dans le cours '{course_name}', j'ai besoin d'un titre. Quel titre souhaitez-vous donner à cette note?"
        else:
            # Récupérer la liste des cours de l'utilisateur
            user_courses = Cours.objects.filter(user=user)
            if not user_courses.exists():
                return "create_note", "Vous n'avez pas encore de cours. Créez d'abord un cours pour pouvoir y ajouter des notes."
            
            courses_list = ", ".join([f"'{c.nom}'" for c in user_courses[:5]])
            if len(user_courses) > 5:
                courses_list += f" et {len(user_courses) - 5} autres"
            
            return "create_note", f"Dans quel cours souhaitez-vous créer cette note? Vos cours disponibles sont: {courses_list}"
    
    # Intention de générer du texte pour une note
    elif any(x in message_lower for x in ["génère", "générer", "rédige", "écrire", "ajouter du texte", "créer un texte"]):
        note_reference = extract_note_reference(message, user)
        if note_reference:
            note_id, note_title = note_reference
            # Si le message contient une indication claire de génération
            if re.search(r"(génère|générer|rédige|écrire|créer)\s+(un|du|le|ce)\s+(texte|contenu)", message_lower):
                # Extraire le sujet après "sur" ou "à propos de"
                subject_match = re.search(r"(sur|à propos de|concernant|au sujet de)\s+([^\.]+)", message_lower)
                subject = subject_match.group(2).strip() if subject_match else "ce sujet"
                
                # Générer le texte avec l'API OpenRouter
                generated_text = generate_text_for_note(subject)
                
                # Enregistrer le texte dans la note
                try:
                    note = Note.objects.get(id=note_id)
                    # Vérifier que l'utilisateur a les droits
                    if note.userOwner == user or Collaborateur.objects.filter(note=note, userCollab=user).exists():
                        # Créer le TextNote
                        TextNote.objects.create(
                            note=note,
                            texte=generated_text,
                            userEditeur=user
                        )
                        return "generate_text", f"J'ai généré et ajouté le texte suivant à votre note '{note_title}':\n\n{generated_text[:150]}...\n\n(Texte complet disponible dans la note)"
                    else:
                        return "generate_text", f"Vous n'avez pas les droits pour modifier la note '{note_title}'."
                except Note.DoesNotExist:
                    return "generate_text", "Je n'ai pas trouvé la note spécifiée. Veuillez vérifier et réessayer."
            else:
                return "generate_text", f"Que souhaitez-vous que je génère comme texte pour la note '{note_title}'? Précisez un sujet."
        else:
            # Vérifier si le message précise qu'il veut générer du texte
            if re.search(r"(génère|générer|rédige|écrire|créer)\s+(un|du|le|ce)\s+(texte|contenu)", message_lower):
                # Récupérer les notes récentes
                recent_notes = Note.objects.filter(
                    Q(userOwner=user) | Q(collaborateur__userCollab=user)
                ).distinct().order_by('-id')[:5]
                
                if not recent_notes.exists():
                    return "generate_text", "Vous n'avez pas de notes disponibles. Créez d'abord une note."
                
                notes_list = "\n".join([f"• {n.titre} (cours: {n.cours.nom})" for n in recent_notes])
                return "generate_text", f"Pour quelle note souhaitez-vous que je génère du texte? Voici vos notes récentes:\n{notes_list}"
    
    # Listage des cours
    elif any(x in message_lower for x in ["liste de mes cours", "voir mes cours", "afficher mes cours", "quels sont mes cours"]):
        user_courses = Cours.objects.filter(user=user)
        if not user_courses.exists():
            return "list_courses", "Vous n'avez pas encore créé de cours. Vous pouvez en créer un en cliquant sur 'Créer cours' dans le menu."
        
        courses_list = "\n".join([f"• {c.nom}" for c in user_courses])
        return "list_courses", f"Voici la liste de vos cours:\n{courses_list}"
    
    # Listage des notes d'un cours
    elif any(x in message_lower for x in ["liste des notes", "voir mes notes", "afficher les notes", "quelles sont les notes"]):
        course_id, course_name = extract_course_reference(message, user)
        if course_id:
            try:
                course = Cours.objects.get(id=course_id)
                notes = Note.objects.filter(cours=course, userOwner=user)
                if not notes.exists():
                    return "list_notes", f"Vous n'avez pas encore créé de notes dans le cours '{course.nom}'. Vous pouvez en créer une depuis la page du cours."
                
                notes_list = "\n".join([f"• {n.titre}" for n in notes])
                return "list_notes", f"Voici la liste des notes dans le cours '{course.nom}':\n{notes_list}"
            except Cours.DoesNotExist:
                return "list_notes", "Je n'ai pas trouvé le cours spécifié. Veuillez vérifier et réessayer."
        else:
            # Récupérer la liste des cours de l'utilisateur
            user_courses = Cours.objects.filter(user=user)
            if not user_courses.exists():
                return "list_notes", "Vous n'avez pas encore de cours. Créez d'abord un cours pour pouvoir y ajouter des notes."
            
            courses_list = ", ".join([f"'{c.nom}'" for c in user_courses[:5]])
            if len(user_courses) > 5:
                courses_list += f" et {len(user_courses) - 5} autres"
            
            return "list_notes", f"Pour quels cours souhaitez-vous voir les notes? Vos cours disponibles sont: {courses_list}"
    
    # Si aucune intention d'action n'est détectée
    return None, None

def extract_note_reference(message, user):
    """
    Extrait la référence à une note à partir du message
    Retourne un tuple (note_id, note_title) ou (None, None)
    """
    # Extraire les mentions explicites de note
    patterns = [
        r"note[^\w]*[\"']?([^\"']+)[\"']?",
        r"dans[^\w]*la note[^\w]*[\"']?([^\"']+)[\"']?",
        r"pour[^\w]*la note[^\w]*[\"']?([^\"']+)[\"']?",
    ]
    
    note_title = None
    for pattern in patterns:
        match = re.search(pattern, message, re.IGNORECASE)
        if match:
            note_title = match.group(1).strip()
            break
    
    if note_title:
        # Rechercher la note par titre
        try:
            # Rechercher dans les notes que je possède ou auxquelles je collabore
            note = Note.objects.filter(
                Q(titre__iexact=note_title, userOwner=user) | 
                Q(titre__iexact=note_title, collaborateur__userCollab=user)
            ).first()
            
            if note:
                return note.id, note.titre
            
            # Recherche approximative si pas de correspondance exacte
            notes = Note.objects.filter(
                Q(userOwner=user) | 
                Q(collaborateur__userCollab=user)
            ).distinct()
            
            for note in notes:
                if note_title.lower() in note.titre.lower() or note.titre.lower() in note_title.lower():
                    return note.id, note.titre
        except Exception:
            pass
    
    return None, None

def extract_course_name(message):
    """Extrait le nom du cours à partir du message"""
    # Recherche de phrases comme "créer un cours nommé X" ou "nouveau cours intitulé X"
    patterns = [
        r"cours[^\w]*nommé[^\w]*[\"']?([^\"']+)[\"']?",
        r"cours[^\w]*intitulé[^\w]*[\"']?([^\"']+)[\"']?",
        r"cours[^\w]*appelé[^\w]*[\"']?([^\"']+)[\"']?",
        r"créer[^\w]*[\"']?([^\"']+)[\"']?[^\w]*comme cours",
        r"ajouter[^\w]*[\"']?([^\"']+)[\"']?[^\w]*comme cours",
    ]
    
    for pattern in patterns:
        match = re.search(pattern, message, re.IGNORECASE)
        if match:
            return match.group(1).strip()
    
    # Si aucun pattern ne correspond, prendre les mots après "créer un cours"
    match = re.search(r"créer un cours[^\w]*[\"']?([^\"']+)[\"']?", message, re.IGNORECASE)
    if match:
        return match.group(1).strip()
    
    return None

def extract_course_reference(message, user):
    """
    Extrait la référence à un cours à partir du message
    Retourne un tuple (course_id, course_name) ou (None, None)
    """
    # Extraire les mentions explicites de cours
    patterns = [
        r"cours[^\w]*[\"']?([^\"']+)[\"']?",
        r"dans[^\w]*[\"']?([^\"']+)[\"']?",
        r"pour[^\w]*[\"']?([^\"']+)[\"']?",
    ]
    
    course_name = None
    for pattern in patterns:
        match = re.search(pattern, message, re.IGNORECASE)
        if match:
            course_name = match.group(1).strip()
            break
    
    if course_name:
        # Rechercher le cours par nom
        try:
            course = Cours.objects.get(nom__iexact=course_name, user=user)
            return course.id, course.nom
        except Cours.DoesNotExist:
            # Recherche approximative
            courses = Cours.objects.filter(user=user)
            for course in courses:
                if course_name.lower() in course.nom.lower() or course.nom.lower() in course_name.lower():
                    return course.id, course.nom
    
    return None, None

def extract_note_title(message):
    """Extrait le titre de la note à partir du message"""
    # Recherche de phrases comme "note intitulée X" ou "note nommée X"
    patterns = [
        r"note[^\w]*intitulée[^\w]*[\"']?([^\"']+)[\"']?",
        r"note[^\w]*nommée[^\w]*[\"']?([^\"']+)[\"']?",
        r"note[^\w]*appelée[^\w]*[\"']?([^\"']+)[\"']?",
        r"créer[^\w]*[\"']?([^\"']+)[\"']?[^\w]*comme note",
    ]
    
    for pattern in patterns:
        match = re.search(pattern, message, re.IGNORECASE)
        if match:
            return match.group(1).strip()
    
    # Si aucun pattern ne correspond, prendre les mots après "créer une note"
    match = re.search(r"créer une note[^\w]*[\"']?([^\"']+)[\"']?", message, re.IGNORECASE)
    if match:
        return match.group(1).strip()
    
    return None

def generate_text_for_note(subject):
    """Génère du texte sur un sujet donné en utilisant l'API OpenRouter"""
    try:
        # Re-charger les variables d'environnement
        load_dotenv()
        
        # Récupérer le modèle actif et la clé API
        model = get_active_ai_model('openrouter')
        if not model:
            return "Désolé, je ne peux pas générer de texte car aucun modèle d'IA n'est configuré."
        
        api_key = get_api_key('openrouter')
        if not api_key:
            return "Désolé, je ne peux pas générer de texte car ma clé API n'est pas configurée."
        
        # Prompt pour la génération de texte
        prompt = f"""Génère un texte informatif et bien structuré sur le sujet suivant: {subject}.
        
Le texte doit être:
- Informatif et précis
- Bien structuré avec des paragraphes logiques
- D'une longueur de 300 à 500 mots
- Rédigé dans un style académique mais accessible
- Sans introduction ni conclusion inutiles

Si le sujet contient des aspects techniques, scientifiques ou mathématiques, inclus les informations pertinentes.
"""
        
        # Préparer la requête
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        
        data = {
            "model": model.model_id,
            "messages": [
                {"role": "user", "content": prompt}
            ]
        }
        
        # Déterminer l'URL de l'API à partir du fournisseur
        url_api = model.provider.url_api
        
        # Envoi de la requête
        response = requests.post(
            url_api,
            headers=headers,
            json=data
        )
        
        # Traitement de la réponse
        if response.status_code == 200:
            result = response.json()
            return result["choices"][0]["message"]["content"]
        else:
            return f"Désolé, je n'ai pas pu générer de texte. Erreur: {response.status_code}"
            
    except Exception as e:
        return f"Désolé, je n'ai pas pu générer de texte. Erreur: {str(e)}"

# Nouveau endpoint API pour Eden
def eden_api(request):
    if request.method != "POST":
        return JsonResponse({"error": "Méthode non autorisée"}, status=405)
    
    user = get_current_user(request)
    if not user:
        return JsonResponse({"error": "Non authentifié"}, status=401)
    
    try:
        data = json.loads(request.body)
        message_text = data.get('message')
        
        if not message_text:
            return JsonResponse({"error": "Aucun message fourni"}, status=400)
        
        # Récupérer ou créer une conversation
        conversation, created = EdenConversation.objects.get_or_create(
            user=user,
            defaults={'date_creation': timezone.now()}
        )
        
        # Mettre à jour la date de dernière interaction
        conversation.derniere_interaction = timezone.now()
        conversation.save()
        
        # Enregistrer le message de l'utilisateur
        user_message = EdenMessage.objects.create(
            conversation=conversation,
            est_assistant=False,
            contenu=message_text
        )
        
        # Générer et enregistrer la réponse d'Eden
        eden_response = generate_eden_response(user, message_text)
        eden_message = EdenMessage.objects.create(
            conversation=conversation,
            est_assistant=True,
            contenu=eden_response
        )
        
        return JsonResponse({
            "success": True,
            "response": eden_response
        })
    except json.JSONDecodeError:
        return JsonResponse({"error": "Format JSON invalide"}, status=400)
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)

def create_audionote(request, note_id):
    user = get_current_user(request)
    if not user:
        messages.error(request, "Connectez-vous pour ajouter un audio.")
        return redirect('login')

    note = get_object_or_404(Note, id=note_id)
    # Autorisation owner ou collaborateur
    is_collab = Collaborateur.objects.filter(note=note, userCollab=user).exists()
    if note.userOwner != user and not is_collab:
        messages.error(request, "Vous n'avez pas le droit d'ajouter un audio à cette note.")
        return redirect('dashboard')

    if request.method == "POST":
        titre = request.POST.get('titre', 'Audio sans titre')
        duree = request.POST.get('duree', 0)  # En secondes
        method = request.POST.get('method', 'upload')  # Méthode d'ajout : upload ou record
        
        # Chemin de destination
        assets_dir = os.path.join(
            settings.BASE_DIR,
            'landing', 'templates', 'landing', 'assets', 'audio'
        )
        os.makedirs(assets_dir, exist_ok=True)
        
        # Nom de fichier unique basé sur l'horodatage
        timestamp = int(timezone.now().timestamp())
        
        if method == 'upload':
            # Méthode 1: Import d'un fichier audio
            uploaded = request.FILES.get('audio')
            
            if not uploaded:
                messages.error(request, "Veuillez sélectionner un fichier audio.")
                return render(request, 'landing/create_audionote.html', {
                    'note': note,
                    'user_contact': user.contact
                })

            # Extension et nom de fichier unique
            ext = os.path.splitext(uploaded.name)[1]
            filename = f"{note.id}_audio_{timestamp}{ext}"
            save_path = os.path.join(assets_dir, filename)
            rel_path = f"audio/{filename}"

            # Sauvegarder le fichier
            with open(save_path, 'wb') as f:
                for chunk in uploaded.chunks():
                    f.write(chunk)
                    
        elif method == 'record':
            # Méthode 2: Enregistrement direct
            recorded_audio_data = request.POST.get('recorded_audio_data')
            
            if not recorded_audio_data:
                messages.error(request, "Aucun enregistrement audio trouvé.")
                return render(request, 'landing/create_audionote.html', {
                    'note': note,
                    'user_contact': user.contact
                })
            
            # Extraire les données base64
            if ',' in recorded_audio_data:
                format_info, base64_str = recorded_audio_data.split(',', 1)
            else:
                base64_str = recorded_audio_data
            
            # Déterminer l'extension du fichier à partir du format_info
            file_ext = '.webm'  # par défaut
            if format_info and 'data:audio/' in format_info:
                mime_type = format_info.split('data:')[1].split(';')[0]
                if mime_type == 'audio/webm':
                    file_ext = '.webm'
                elif mime_type == 'audio/mp4':
                    file_ext = '.mp4'
                elif mime_type == 'audio/ogg':
                    file_ext = '.ogg'
                elif mime_type == 'audio/wav' or mime_type == 'audio/x-wav':
                    file_ext = '.wav'
                
                print(f"Format audio détecté: {mime_type}, extension utilisée: {file_ext}")
                
            # Convertir base64 en données binaires
            audio_data = base64.b64decode(base64_str)
            
            # Sauvegarder le fichier avec l'extension appropriée
            filename = f"{note.id}_audio_record_{timestamp}{file_ext}"
            save_path = os.path.join(assets_dir, filename)
            rel_path = f"audio/{filename}"
            
            with open(save_path, 'wb') as f:
                f.write(audio_data)
        else:
            messages.error(request, "Méthode d'ajout audio non reconnue.")
            return render(request, 'landing/create_audionote.html', {
                'note': note,
                'user_contact': user.contact
            })

        # Enregistrer en base de données
        AudioNote.objects.create(
            note=note,
            path=rel_path,
            titre=titre,
            duree=duree,
            userEditeur=user
        )
        messages.success(request, "Audio ajouté avec succès !")
        return redirect('note_detail', note_id=note.id)

    return render(request, 'landing/create_audionote.html', {
        'note': note,
        'user_contact': user.contact
    })

def delete_audionote(request, audio_id):
    user = get_current_user(request)
    if not user:
        messages.error(request, "Connectez-vous pour supprimer un audio.")
        return redirect('login')

    audio = get_object_or_404(AudioNote, id=audio_id)
    note = audio.note

    # Autorisation owner ou collaborateur
    is_owner = (note.userOwner == user)
    is_collab = Collaborateur.objects.filter(note=note, userCollab=user).exists()
    if not (is_owner or is_collab):
        messages.error(request, "Vous n'avez pas le droit de supprimer cet audio.")
        return redirect('note_detail', note_id=note.id)

    if request.method == "POST":
        # Supprime le fichier sur le disque
        file_path = os.path.join(
            settings.BASE_DIR,
            'landing', 'templates', 'landing', 'assets', audio.path.replace('/', os.sep)
        )
        if os.path.exists(file_path):
            os.remove(file_path)
        audio.delete()
        messages.success(request, "Audio supprimé avec succès !")
        return redirect('note_detail', note_id=note.id)

    # Pas de page de confirmation dédiée, on redirige
    return redirect('note_detail', note_id=note.id)

def create_videonote(request, note_id):
    user = get_current_user(request)
    if not user:
        messages.error(request, "Connectez-vous pour ajouter une vidéo.")
        return redirect('login')

    note = get_object_or_404(Note, id=note_id)
    # Autorisation owner ou collaborateur
    is_collab = Collaborateur.objects.filter(note=note, userCollab=user).exists()
    if note.userOwner != user and not is_collab:
        messages.error(request, "Vous n'avez pas le droit d'ajouter une vidéo à cette note.")
        return redirect('dashboard')

    # Gestion de l'erreur RequestDataTooBig
    try:
        if request.method == "POST":
            titre = request.POST.get('titre', 'Vidéo sans titre')
            duree = request.POST.get('duree', 0)  # En secondes
            method = request.POST.get('method', 'upload')  # Méthode d'ajout : upload ou record
            
            # Répertoire de destination pour la vidéo
            video_dir = os.path.join(
                settings.BASE_DIR,
                'landing', 'templates', 'landing', 'assets', 'video'
            )
            os.makedirs(video_dir, exist_ok=True)
            
            # Répertoire pour les miniatures
            thumb_dir = os.path.join(
                settings.BASE_DIR,
                'landing', 'templates', 'landing', 'assets', 'img', 'thumbnails'
            )
            os.makedirs(thumb_dir, exist_ok=True)
            
            # Timestamp unique pour les noms de fichiers
            timestamp = int(timezone.now().timestamp())
            
            if method == 'upload':
                # Méthode 1: Import d'un fichier vidéo
                uploaded_video = request.FILES.get('video')
                uploaded_thumbnail = request.FILES.get('thumbnail')
                
                if not uploaded_video:
                    messages.error(request, "Veuillez sélectionner un fichier vidéo.")
                    return render(request, 'landing/create_videonote.html', {
                        'note': note,
                        'user_contact': user.contact
                    })

                # Extension et nom de fichier unique pour la vidéo
                video_ext = os.path.splitext(uploaded_video.name)[1]
                video_filename = f"{note.id}_video_{timestamp}{video_ext}"
                video_save_path = os.path.join(video_dir, video_filename)
                video_rel_path = f"video/{video_filename}"

                # Sauvegarder la vidéo
                with open(video_save_path, 'wb') as f:
                    for chunk in uploaded_video.chunks():
                        f.write(chunk)

                # Traitement de la miniature si fournie
                thumbnail_rel_path = None
                if uploaded_thumbnail:
                    thumb_ext = os.path.splitext(uploaded_thumbnail.name)[1]
                    thumb_filename = f"{note.id}_thumb_{timestamp}{thumb_ext}"
                    thumb_save_path = os.path.join(thumb_dir, thumb_filename)
                    thumbnail_rel_path = f"img/thumbnails/{thumb_filename}"
                    
                    with open(thumb_save_path, 'wb') as f:
                        for chunk in uploaded_thumbnail.chunks():
                            f.write(chunk)
                            
            elif method == 'record':
                # Méthode 2: Enregistrement direct avec webcam
                recorded_video_data = request.POST.get('recorded_video_data')
                recorded_thumbnail = request.POST.get('recorded_thumbnail')
                
                if not recorded_video_data:
                    messages.error(request, "Aucun enregistrement vidéo trouvé.")
                    return render(request, 'landing/create_videonote.html', {
                        'note': note,
                        'user_contact': user.contact
                    })
                
                # Extraire les données base64 de la vidéo
                if ',' in recorded_video_data:
                    format_info, base64_str = recorded_video_data.split(',', 1)
                else:
                    base64_str = recorded_video_data
                
                # Déterminer l'extension du fichier à partir du format_info
                video_ext = '.webm'  # par défaut pour l'enregistrement WebRTC
                if format_info and 'data:video/' in format_info:
                    mime_type = format_info.split('data:')[1].split(';')[0]
                    if mime_type == 'video/webm':
                        video_ext = '.webm'
                    elif mime_type == 'video/mp4':
                        video_ext = '.mp4'
                    elif mime_type == 'video/ogg':
                        video_ext = '.ogg'
                    
                # Convertir base64 en données binaires
                video_data = base64.b64decode(base64_str)
                
                # Sauvegarder le fichier vidéo
                video_filename = f"{note.id}_video_record_{timestamp}{video_ext}"
                video_save_path = os.path.join(video_dir, video_filename)
                video_rel_path = f"video/{video_filename}"
                
                with open(video_save_path, 'wb') as f:
                    f.write(video_data)
                
                # Traiter la miniature si fournie
                thumbnail_rel_path = None
                if recorded_thumbnail:
                    # Extraire les données base64 de la miniature
                    if ',' in recorded_thumbnail:
                        format_info, thumb_base64 = recorded_thumbnail.split(',', 1)
                    else:
                        thumb_base64 = recorded_thumbnail
                    
                    # Convertir en données binaires
                    thumb_data = base64.b64decode(thumb_base64)
                    
                    # Sauvegarder la miniature
                    thumb_filename = f"{note.id}_thumb_record_{timestamp}.jpg"
                    thumb_save_path = os.path.join(thumb_dir, thumb_filename)
                    thumbnail_rel_path = f"img/thumbnails/{thumb_filename}"
                    
                    with open(thumb_save_path, 'wb') as f:
                        f.write(thumb_data)
            else:
                messages.error(request, "Méthode d'ajout vidéo non reconnue.")
                return render(request, 'landing/create_videonote.html', {
                    'note': note,
                    'user_contact': user.contact
                })

            # Enregistrer en base de données (commun aux deux méthodes)
            VideoNote.objects.create(
                note=note,
                path=video_rel_path,
                titre=titre,
                duree=duree,
                thumbnail=thumbnail_rel_path,
                userEditeur=user
            )
            messages.success(request, "Vidéo ajoutée avec succès !")
            return redirect('note_detail', note_id=note.id)
            
    except Exception as e:
        if 'RequestDataTooBig' in str(e):
            messages.error(request, "La vidéo est trop volumineuse pour être traitée. Veuillez limiter l'enregistrement à 10 secondes maximum ou utiliser l'option d'importation pour les vidéos plus longues.")
        else:
            messages.error(request, f"Une erreur est survenue lors du traitement de la vidéo: {str(e)}")
        
        return render(request, 'landing/create_videonote.html', {
            'note': note,
            'user_contact': user.contact
        })

    return render(request, 'landing/create_videonote.html', {
        'note': note,
        'user_contact': user.contact
    })

def delete_videonote(request, video_id):
    user = get_current_user(request)
    if not user:
        messages.error(request, "Connectez-vous pour supprimer une vidéo.")
        return redirect('login')

    video = get_object_or_404(VideoNote, id=video_id)
    note = video.note

    # Autorisation owner ou collaborateur
    is_owner = (note.userOwner == user)
    is_collab = Collaborateur.objects.filter(note=note, userCollab=user).exists()
    if not (is_owner or is_collab):
        messages.error(request, "Vous n'avez pas le droit de supprimer cette vidéo.")
        return redirect('note_detail', note_id=note.id)

    if request.method == "POST":
        # Supprime le fichier vidéo
        video_path = os.path.join(
            settings.BASE_DIR,
            'landing', 'templates', 'landing', 'assets', video.path.replace('/', os.sep)
        )
        if os.path.exists(video_path):
            os.remove(video_path)
            
        # Supprime la miniature si elle existe
        if video.thumbnail:
            thumb_path = os.path.join(
                settings.BASE_DIR,
                'landing', 'templates', 'landing', 'assets', video.thumbnail.replace('/', os.sep)
            )
            if os.path.exists(thumb_path):
                os.remove(thumb_path)
                
        video.delete()
        messages.success(request, "Vidéo supprimée avec succès !")
        return redirect('note_detail', note_id=note.id)

    # Pas de page de confirmation dédiée, on redirige
    return redirect('note_detail', note_id=note.id)

def create_ocrnote(request, note_id):
    user = get_current_user(request)
    if not user:
        messages.error(request, "Connectez-vous pour ajouter une extraction OCR.")
        return redirect('login')

    note = get_object_or_404(Note, id=note_id)
    # Autorisation owner ou collaborateur
    is_collab = Collaborateur.objects.filter(note=note, userCollab=user).exists()
    if note.userOwner != user and not is_collab:
        messages.error(request, "Vous n'avez pas le droit d'ajouter une extraction OCR à cette note.")
        return redirect('dashboard')

    if request.method == "POST":
        uploaded = request.FILES.get('image')
        texte_manuel = request.POST.get('texte_manuel', '')
        add_to_textnote = 'add_to_textnote' in request.POST
        
        # Vérifier qu'on a soit une image, soit du texte
        if not uploaded and not texte_manuel:
            messages.error(request, "Veuillez sélectionner une image ou entrer du texte manuellement.")
            return render(request, 'landing/create_ocrnote.html', {
                'note': note,
                'user_contact': user.contact
            })

        image_rel_path = None
        # Si on a uploadé une image (méthode import)
        if uploaded:
            # Extension et nom de fichier unique
            ext = os.path.splitext(uploaded.name)[1]
            filename = f"{note.id}_ocr_{int(timezone.now().timestamp())}{ext}"

            # Répertoire de destination
            assets_dir = os.path.join(
                settings.BASE_DIR,
                'landing', 'templates', 'landing', 'assets', 'ocr'
            )
            os.makedirs(assets_dir, exist_ok=True)

            save_path = os.path.join(assets_dir, filename)
            image_rel_path = f"ocr/{filename}"

            # Sauvegarder le fichier
            with open(save_path, 'wb') as f:
                for chunk in uploaded.chunks():
                    f.write(chunk)
        # Si c'est une image capturée par la caméra (base64)
        elif 'captured-image-data' in request.POST and request.POST.get('captured-image-data'):
            image_data = request.POST.get('captured-image-data')
            
            # Extraire les données base64
            if ',' in image_data:
                format_info, base64_str = image_data.split(',', 1)
            else:
                base64_str = image_data
                
            # Convertir base64 en données binaires
            image_binary = base64.b64decode(base64_str)
            
            # Créer un nom de fichier unique
            filename = f"{note.id}_ocr_capture_{int(timezone.now().timestamp())}.png"
            
            # Répertoire de destination
            assets_dir = os.path.join(
                settings.BASE_DIR,
                'landing', 'templates', 'landing', 'assets', 'ocr'
            )
            os.makedirs(assets_dir, exist_ok=True)
            
            save_path = os.path.join(assets_dir, filename)
            image_rel_path = f"ocr/{filename}"
            
            # Sauvegarder l'image
            with open(save_path, 'wb') as f:
                f.write(image_binary)

        # Texte extrait utilisé pour les deux modèles
        texte_extrait = texte_manuel

        # 1. Créer l'entrée OcrNote
        ocr_note = OcrNote.objects.create(
            note=note,
            image_path=image_rel_path,
            texte_extrait=texte_extrait,
            userEditeur=user
        )
        
        # 2. Si demandé, créer également une entrée TextNote
        if add_to_textnote:
            TextNote.objects.create(
                note=note,
                texte=texte_extrait,
                userEditeur=user
            )
            messages.success(request, "OCR et note texte ajoutés avec succès !")
        else:
            messages.success(request, "Extraction OCR ajoutée avec succès !")
            
        return redirect('note_detail', note_id=note.id)

    return render(request, 'landing/create_ocrnote.html', {
        'note': note,
        'user_contact': user.contact
    })

def delete_ocrnote(request, ocr_id):
    user = get_current_user(request)
    if not user:
        messages.error(request, "Connectez-vous pour supprimer une extraction OCR.")
        return redirect('login')

    ocr = get_object_or_404(OcrNote, id=ocr_id)
    note = ocr.note

    # Autorisation owner ou collaborateur
    is_owner = (note.userOwner == user)
    is_collab = Collaborateur.objects.filter(note=note, userCollab=user).exists()
    if not (is_owner or is_collab):
        messages.error(request, "Vous n'avez pas le droit de supprimer cette extraction OCR.")
        return redirect('note_detail', note_id=note.id)

    if request.method == "POST":
        # Supprime l'image associée si elle existe
        if ocr.image_path:
            img_path = os.path.join(
                settings.BASE_DIR,
                'landing', 'templates', 'landing', 'assets', ocr.image_path.replace('/', os.sep)
            )
            if os.path.exists(img_path):
                os.remove(img_path)
                
        ocr.delete()
        messages.success(request, "Extraction OCR supprimée avec succès !")
        return redirect('note_detail', note_id=note.id)

    # Pas de page de confirmation dédiée, on redirige
    return redirect('note_detail', note_id=note.id)

def profile(request):
    """
    Vue pour afficher et mettre à jour le profil utilisateur.
    Permet de modifier toutes les informations sauf le nom d'utilisateur.
    """
    user = get_current_user(request)
    if not user:
        messages.error(request, "Veuillez vous connecter pour accéder à votre profil.")
        return redirect('login')
        
    try:
        contact = user.contact
        
        if request.method == 'POST':
            # Récupération des données du formulaire
            nom = request.POST.get('nom')
            postnom = request.POST.get('postnom')
            prenom = request.POST.get('prenom')
            sexe = request.POST.get('sexe')
            adresse = request.POST.get('adresse')
            tel = request.POST.get('tel')
            
            # Vérification si le numéro de téléphone existe déjà
            if Contact.objects.filter(tel=tel).exclude(id=contact.id).exists():
                messages.error(request, "Ce numéro de téléphone est déjà utilisé.")
                return render(request, 'landing/profile.html', {'user': user, 'contact': contact, 'user_contact': contact})
            
            # Mise à jour des informations du contact
            contact.nom = nom
            contact.postnom = postnom
            contact.prenom = prenom
            contact.sexe = sexe
            contact.adresse = adresse
            contact.tel = tel
            contact.save()
            
            # Mise à jour du mot de passe si fourni
            new_password = request.POST.get('new_password')
            if new_password:
                confirm_password = request.POST.get('confirm_password')
                if new_password == confirm_password:
                    user.set_password(new_password)
                    user.save()
                    messages.success(request, "Mot de passe mis à jour avec succès.")
                else:
                    messages.error(request, "Les mots de passe ne correspondent pas.")
            
            messages.success(request, "Profil mis à jour avec succès.")
            return redirect('profile')
        
        return render(request, 'landing/profile.html', {'user': user, 'contact': contact, 'user_contact': contact})
        
    except Exception as e:
        messages.error(request, f"Une erreur s'est produite: {str(e)}")
        return redirect('dashboard')

# Fonctions pour la gestion des API d'IA
def api_configuration(request):
    """Vue pour la page de configuration des API d'IA"""
    user = get_current_user(request)
    if not user:
        messages.error(request, "Veuillez vous connecter pour accéder à la configuration.")
        return redirect('login')
    
    # Vérifier si l'utilisateur est l'administrateur (username: root45)
    if user.username != 'root45':
        messages.error(request, "Vous n'avez pas les droits pour accéder à cette page. Seul l'administrateur peut configurer les API.")
        return redirect('dashboard')
    
    # Récupérer tous les fournisseurs et leurs modèles
    providers = AIProvider.objects.all().prefetch_related('models', 'api_keys')
    
    # Vérifier si des données par défaut doivent être créées
    if not providers.exists():
        create_default_ai_providers()
        providers = AIProvider.objects.all().prefetch_related('models', 'api_keys')
    
    if request.method == "POST":
        action = request.POST.get('action')
        
        if action == 'add_api_key':
            provider_id = request.POST.get('provider_id')
            api_key = request.POST.get('api_key')
            
            if provider_id and api_key:
                provider = get_object_or_404(AIProvider, id=provider_id)
                
                # Supprimer les anciennes clés pour ce fournisseur
                APIKey.objects.filter(provider=provider).delete()
                
                # Créer et enregistrer la nouvelle clé
                new_key = APIKey(provider=provider)
                new_key.set_key(api_key)
                new_key.save()
                
                messages.success(request, f"Clé API ajoutée pour {provider.nom}")
                return redirect('api_configuration')
        
        elif action == 'toggle_model':
            model_id = request.POST.get('model_id')
            
            if model_id:
                model = get_object_or_404(AIModel, id=model_id)
                model.est_actif = not model.est_actif
                
                # Si on active ce modèle comme défaut, désactiver les autres modèles par défaut du même fournisseur
                if model.est_defaut and model.est_actif:
                    AIModel.objects.filter(provider=model.provider, est_defaut=True).exclude(id=model.id).update(est_actif=False)
                
                model.save()
                
                status = "activé" if model.est_actif else "désactivé"
                messages.success(request, f"Modèle {model.nom} {status}")
                return redirect('api_configuration')
        
        elif action == 'set_default_model':
            model_id = request.POST.get('model_id')
            
            if model_id:
                model = get_object_or_404(AIModel, id=model_id)
                
                # Désactiver tous les modèles par défaut pour ce fournisseur
                AIModel.objects.filter(provider=model.provider, est_defaut=True).update(est_defaut=False)
                
                # Définir ce modèle comme défaut
                model.est_defaut = True
                model.est_actif = True  # Activer automatiquement le modèle par défaut
                model.save()
                
                messages.success(request, f"Modèle {model.nom} défini comme modèle par défaut pour {model.provider.nom}")
                return redirect('api_configuration')
        
        elif action == 'add_model':
            provider_id = request.POST.get('provider_id')
            nom = request.POST.get('nom')
            model_id = request.POST.get('model_id')
            description = request.POST.get('description')
            est_gratuit = request.POST.get('est_gratuit') == 'on'
            
            if provider_id and nom and model_id:
                provider = get_object_or_404(AIProvider, id=provider_id)
                
                # Vérifier si le modèle existe déjà
                model_exists = AIModel.objects.filter(provider=provider, model_id=model_id).exists()
                if model_exists:
                    messages.error(request, f"Un modèle avec l'ID '{model_id}' existe déjà pour {provider.nom}")
                    return redirect('api_configuration')
                
                # Déterminer l'ordre (en prenant le dernier + 1)
                last_order = AIModel.objects.filter(provider=provider).order_by('-ordre').values_list('ordre', flat=True).first() or 0
                
                # Créer le nouveau modèle
                AIModel.objects.create(
                    provider=provider,
                    nom=nom,
                    model_id=model_id,
                    description=description or f"Modèle {nom} pour {provider.nom}",
                    est_gratuit=est_gratuit,
                    est_actif=False,
                    est_defaut=False,
                    ordre=last_order + 1
                )
                
                messages.success(request, f"Modèle {nom} ajouté avec succès")
                return redirect('api_configuration')
        
        elif action == 'delete_model':
            model_id = request.POST.get('model_id')
            
            if model_id:
                model = get_object_or_404(AIModel, id=model_id)
                model_name = model.nom
                provider_name = model.provider.nom
                
                # Ne pas supprimer le modèle par défaut
                if model.est_defaut:
                    messages.error(request, f"Impossible de supprimer le modèle par défaut. Veuillez d'abord définir un autre modèle par défaut.")
                    return redirect('api_configuration')
                
                # Supprimer le modèle
                model.delete()
                
                messages.success(request, f"Modèle {model_name} de {provider_name} supprimé avec succès")
                return redirect('api_configuration')
    
    # Préparer les données pour le template
    providers_data = []
    for provider in providers:
        has_api_key = provider.api_keys.filter(est_active=True).exists()
        
        # Regrouper les modèles par type (gratuit ou payant)
        free_models = provider.models.filter(est_gratuit=True)
        paid_models = provider.models.filter(est_gratuit=False)
        
        providers_data.append({
            'provider': provider,
            'has_api_key': has_api_key,
            'free_models': free_models,
            'paid_models': paid_models
        })
    
    return render(request, 'landing/api_configuration.html', {
        'providers_data': providers_data,
        'user_contact': user.contact
    })

def create_default_ai_providers():
    """Crée les fournisseurs d'IA et les modèles par défaut"""
    # 1. OpenRouter
    openrouter, created = AIProvider.objects.get_or_create(
        code='openrouter',
        defaults={
            'nom': 'OpenRouter',
            'description': 'Plateforme qui donne accès à plusieurs modèles d\'IA via une seule API',
            'url_api': 'https://openrouter.ai/api/v1/chat/completions',
            'est_actif': True
        }
    )
    
    # Modèles gratuits OpenRouter
    free_models = [
        {
            'nom': 'DeepSeek R1 (Free)',
            'model_id': 'deepseek/deepseek-r1:free',
            'description': 'Modèle généraliste performant pour tous types de tâches',
            'est_gratuit': True,
            'est_defaut': True,
            'est_actif': True,
            'ordre': 1
        },
        {
            'nom': 'Mistral DevStral Small (Free)',
            'model_id': 'mistralai/devstral-small:free',
            'description': 'Modèle compact de Mistral AI',
            'est_gratuit': True,
            'ordre': 2
        },
        {
            'nom': 'Google Gemma 3n-e4b-it (Free)',
            'model_id': 'google/gemma-3n-e4b-it:free',
            'description': 'Modèle léger de Google',
            'est_gratuit': True,
            'ordre': 3
        },
        {
            'nom': 'Meta Llama 3.3 8B Instruct (Free)',
            'model_id': 'meta-llama/llama-3.3-8b-instruct:free',
            'description': 'Modèle instruct de Meta',
            'est_gratuit': True,
            'ordre': 4
        },
        {
            'nom': 'Deep Hermes 3 Mistral 24B (Free)',
            'model_id': 'nousresearch/deephermes-3-mistral-24b-preview:free',
            'description': 'Modèle puissant basé sur Mistral',
            'est_gratuit': True,
            'ordre': 5
        },
        {
            'nom': 'Microsoft Phi-4 Reasoning Plus (Free)',
            'model_id': 'microsoft/phi-4-reasoning-plus:free',
            'description': 'Modèle de raisonnement avancé de Microsoft',
            'est_gratuit': True,
            'ordre': 6
        },
        {
            'nom': 'InternVL3 14B (Free)',
            'model_id': 'opengvlab/internvl3-14b:free',
            'description': 'Modèle multimodal avancé',
            'est_gratuit': True,
            'ordre': 7
        },
        {
            'nom': 'Qwen3 30B (Free)',
            'model_id': 'qwen/qwen3-30b-a3b:free',
            'description': 'Modèle puissant de Qwen',
            'est_gratuit': True,
            'ordre': 8
        },
        {
            'nom': 'Qwen3 8B (Free)',
            'model_id': 'qwen/qwen3-8b:free',
            'description': 'Version compacte du modèle Qwen',
            'est_gratuit': True,
            'ordre': 9
        },
        {
            'nom': 'OpenRouter IA (Free)',
            'model_id': 'nousresearch/deephermes-3-mistral-24b-preview:free',
            'description': 'Modèle de OpenRouter',
            'est_gratuit': True,
            'ordre': 10
        }
    ]
    
    # Ajouter ou mettre à jour les modèles gratuits
    for model_data in free_models:
        AIModel.objects.update_or_create(
            provider=openrouter,
            model_id=model_data['model_id'],
            defaults=model_data
        )
    
    # 2. DeepSeek Officiel
    deepseek, created = AIProvider.objects.get_or_create(
        code='deepseek',
        defaults={
            'nom': 'DeepSeek Officiel',
            'description': 'API officielle de DeepSeek pour accéder à leurs modèles',
            'url_api': 'https://api.deepseek.com/chat/completions',
            'est_actif': True
        }
    )
    
    # Modèles DeepSeek
    deepseek_models = [
        {
            'nom': 'DeepSeek Chat',
            'model_id': 'deepseek-chat',
            'description': 'Modèle conversationnel de DeepSeek',
            'est_gratuit': False,
            'est_defaut': True,
            'ordre': 1
        },
        {
            'nom': 'DeepSeek Coder',
            'model_id': 'deepseek-coder',
            'description': 'Modèle spécialisé pour la génération de code',
            'est_gratuit': False,
            'ordre': 2
        }
    ]
    
    # Ajouter ou mettre à jour les modèles DeepSeek
    for model_data in deepseek_models:
        AIModel.objects.update_or_create(
            provider=deepseek,
            model_id=model_data['model_id'],
            defaults=model_data
        )
    
    # 3. OpenAI
    openai, created = AIProvider.objects.get_or_create(
        code='openai',
        defaults={
            'nom': 'OpenAI',
            'description': 'API officielle d\'OpenAI pour accéder à GPT et d\'autres modèles',
            'url_api': 'https://api.openai.com/v1/chat/completions',
            'est_actif': True
        }
    )
    
    # Modèles OpenAI
    openai_models = [
        {
            'nom': 'GPT-4o',
            'model_id': 'gpt-4o',
            'description': 'Dernière version multimodale du modèle GPT-4, très performant',
            'est_gratuit': False,
            'est_defaut': True,
            'ordre': 1
        },
        {
            'nom': 'GPT-4o-mini',
            'model_id': 'gpt-4o-mini',
            'description': 'Version allégée et économique de GPT-4o',
            'est_gratuit': False,
            'ordre': 2
        },
        {
            'nom': 'GPT-4 Turbo',
            'model_id': 'gpt-4-turbo',
            'description': 'Version optimisée du modèle GPT-4 avec contexte étendu',
            'est_gratuit': False,
            'ordre': 3
        },
        {
            'nom': 'GPT-3.5 Turbo',
            'model_id': 'gpt-3.5-turbo',
            'description': 'Modèle économique et rapide',
            'est_gratuit': False,
            'ordre': 4
        }
    ]
    
    # Ajouter ou mettre à jour les modèles OpenAI
    for model_data in openai_models:
        AIModel.objects.update_or_create(
            provider=openai,
            model_id=model_data['model_id'],
            defaults=model_data
        )

def get_active_ai_model(provider_code='openrouter'):
    """
    Retourne le modèle actif pour un fournisseur donné
    Si aucun modèle n'est actif, retourne le modèle par défaut
    """
    try:
        # Essayer d'abord de trouver un modèle actif
        model = AIModel.objects.filter(
            provider__code=provider_code,
            est_actif=True
        ).first()
        
        # Si aucun modèle actif, chercher le modèle par défaut
        if not model:
            model = AIModel.objects.filter(
                provider__code=provider_code,
                est_defaut=True
            ).first()
        
        # Si toujours rien, utiliser DeepSeek R1 Free comme fallback
        if not model and provider_code != 'openrouter':
            model = AIModel.objects.filter(
                provider__code='openrouter',
                model_id='deepseek/deepseek-r1:free'
            ).first()
        
        return model
    except Exception:
        # En cas d'erreur, retourner None
        return None

def get_api_key(provider_code):
    """Retourne la clé API pour un fournisseur donné"""
    try:
        api_key = APIKey.objects.filter(
            provider__code=provider_code,
            est_active=True
        ).first()
        
        if api_key:
            return api_key.get_key()
        
        # Si pas de clé spécifique pour ce fournisseur et que c'est OpenRouter, 
        # utiliser la variable d'environnement
        if provider_code == 'openrouter':
            return os.environ.get('OPENROUTER_API_KEY')
        
        return None
    except Exception:
        # En cas d'erreur, utiliser la variable d'environnement pour OpenRouter
        if provider_code == 'openrouter':
            return os.environ.get('OPENROUTER_API_KEY')
        return None

def refresh_ai_models(force=False):
    """
    Rafraîchit la liste des modèles d'IA
    Si force=True, tous les modèles seront mis à jour même s'ils existent déjà
    """
    # Récupérer ou créer les fournisseurs
    openrouter, _ = AIProvider.objects.get_or_create(
        code='openrouter',
        defaults={
            'nom': 'OpenRouter',
            'description': 'Plateforme qui donne accès à plusieurs modèles d\'IA via une seule API',
            'url_api': 'https://openrouter.ai/api/v1/chat/completions',
            'est_actif': True
        }
    )
    
    # Liste à jour des modèles gratuits OpenRouter
    free_models = [
        {
            'nom': 'DeepSeek R1 (Free)',
            'model_id': 'deepseek/deepseek-r1:free',
            'description': 'Modèle généraliste performant pour tous types de tâches',
            'est_gratuit': True,
            'est_defaut': True,
            'est_actif': True,
            'ordre': 1
        },
        {
            'nom': 'Mistral DevStral Small (Free)',
            'model_id': 'mistralai/devstral-small:free',
            'description': 'Modèle compact de Mistral AI',
            'est_gratuit': True,
            'ordre': 2
        },
        {
            'nom': 'Google Gemma 3n-e4b-it (Free)',
            'model_id': 'google/gemma-3n-e4b-it:free',
            'description': 'Modèle léger de Google',
            'est_gratuit': True,
            'ordre': 3
        },
        {
            'nom': 'Meta Llama 3.3 8B Instruct (Free)',
            'model_id': 'meta-llama/llama-3.3-8b-instruct:free',
            'description': 'Modèle instruct de Meta',
            'est_gratuit': True,
            'ordre': 4
        },
        {
            'nom': 'Deep Hermes 3 Mistral 24B (Free)',
            'model_id': 'nousresearch/deephermes-3-mistral-24b-preview:free',
            'description': 'Modèle puissant basé sur Mistral',
            'est_gratuit': True,
            'ordre': 5
        },
        {
            'nom': 'Microsoft Phi-4 Reasoning Plus (Free)',
            'model_id': 'microsoft/phi-4-reasoning-plus:free',
            'description': 'Modèle de raisonnement avancé de Microsoft',
            'est_gratuit': True,
            'ordre': 6
        },
        {
            'nom': 'InternVL3 14B (Free)',
            'model_id': 'opengvlab/internvl3-14b:free',
            'description': 'Modèle multimodal avancé',
            'est_gratuit': True,
            'ordre': 7
        },
        {
            'nom': 'Qwen3 30B (Free)',
            'model_id': 'qwen/qwen3-30b-a3b:free',
            'description': 'Modèle puissant de Qwen',
            'est_gratuit': True,
            'ordre': 8
        },
        {
            'nom': 'Qwen3 8B (Free)',
            'model_id': 'qwen/qwen3-8b:free',
            'description': 'Version compacte du modèle Qwen',
            'est_gratuit': True,
            'ordre': 9
        },
        {
            'nom': 'OpenRouter IA (Free)',
            'model_id': 'nousresearch/deephermes-3-mistral-24b-preview:free',
            'description': 'Modèle de OpenRouter',
            'est_gratuit': True,
            'ordre': 10
        }
    ]
    
    # Conserver le modèle par défaut actuel pour OpenRouter
    default_model = AIModel.objects.filter(provider=openrouter, est_defaut=True).first()
    default_model_id = default_model.model_id if default_model else 'deepseek/deepseek-r1:free'
    
    # Si force=True, supprimer tous les modèles existants de OpenRouter
    if force:
        # Ne garder que les modèles personnalisés (qui ne sont pas dans notre liste)
        model_ids_to_keep = [model['model_id'] for model in free_models]
        custom_models = AIModel.objects.filter(provider=openrouter).exclude(model_id__in=model_ids_to_keep)
        
        # Supprimer tous les modèles standard
        AIModel.objects.filter(provider=openrouter, model_id__in=model_ids_to_keep).delete()
    
    # Ajouter ou mettre à jour les modèles
    for model_data in free_models:
        # Si c'est le modèle par défaut précédent, garder son statut
        if model_data['model_id'] == default_model_id:
            model_data['est_defaut'] = True
        
        # Mettre à jour ou créer le modèle
        AIModel.objects.update_or_create(
            provider=openrouter,
            model_id=model_data['model_id'],
            defaults=model_data
        )
    
    return len(free_models)


def api_configuration(request):
    """Vue pour la page de configuration des API d'IA"""
    user = get_current_user(request)
    if not user:
        messages.error(request, "Veuillez vous connecter pour accéder à la configuration.")
        return redirect('login')
    
    # Vérifier si l'utilisateur est l'administrateur (username: root45)
    if user.username != 'root45':
        messages.error(request, "Vous n'avez pas les droits pour accéder à cette page. Seul l'administrateur peut configurer les API.")
        return redirect('dashboard')
    
    # Récupérer tous les fournisseurs et leurs modèles
    providers = AIProvider.objects.all().prefetch_related('models', 'api_keys')
    
    # Vérifier si des données par défaut doivent être créées
    if not providers.exists():
        create_default_ai_providers()
        providers = AIProvider.objects.all().prefetch_related('models', 'api_keys')
    
    if request.method == "POST":
        action = request.POST.get('action')
        
        if action == 'add_api_key':
            provider_id = request.POST.get('provider_id')
            api_key = request.POST.get('api_key')
            
            if provider_id and api_key:
                provider = get_object_or_404(AIProvider, id=provider_id)
                
                # Supprimer les anciennes clés pour ce fournisseur
                APIKey.objects.filter(provider=provider).delete()
                
                # Créer et enregistrer la nouvelle clé
                new_key = APIKey(provider=provider)
                new_key.set_key(api_key)
                new_key.save()
                
                messages.success(request, f"Clé API ajoutée pour {provider.nom}")
                return redirect('api_configuration')
        
        elif action == 'toggle_model':
            model_id = request.POST.get('model_id')
            
            if model_id:
                model = get_object_or_404(AIModel, id=model_id)
                model.est_actif = not model.est_actif
                
                # Si on active ce modèle comme défaut, désactiver les autres modèles par défaut du même fournisseur
                if model.est_defaut and model.est_actif:
                    AIModel.objects.filter(provider=model.provider, est_defaut=True).exclude(id=model.id).update(est_actif=False)
                
                model.save()
                
                status = "activé" if model.est_actif else "désactivé"
                messages.success(request, f"Modèle {model.nom} {status}")
                return redirect('api_configuration')
        
        elif action == 'set_default_model':
            model_id = request.POST.get('model_id')
            
            if model_id:
                model = get_object_or_404(AIModel, id=model_id)
                
                # Désactiver tous les modèles par défaut pour ce fournisseur
                AIModel.objects.filter(provider=model.provider, est_defaut=True).update(est_defaut=False)
                
                # Définir ce modèle comme défaut
                model.est_defaut = True
                model.est_actif = True  # Activer automatiquement le modèle par défaut
                model.save()
                
                messages.success(request, f"Modèle {model.nom} défini comme modèle par défaut pour {model.provider.nom}")
                return redirect('api_configuration')
        
        elif action == 'add_model':
            provider_id = request.POST.get('provider_id')
            nom = request.POST.get('nom')
            model_id = request.POST.get('model_id')
            description = request.POST.get('description')
            est_gratuit = request.POST.get('est_gratuit') == 'on'
            
            if provider_id and nom and model_id:
                provider = get_object_or_404(AIProvider, id=provider_id)
                
                # Vérifier si le modèle existe déjà
                model_exists = AIModel.objects.filter(provider=provider, model_id=model_id).exists()
                if model_exists:
                    messages.error(request, f"Un modèle avec l'ID '{model_id}' existe déjà pour {provider.nom}")
                    return redirect('api_configuration')
                
                # Déterminer l'ordre (en prenant le dernier + 1)
                last_order = AIModel.objects.filter(provider=provider).order_by('-ordre').values_list('ordre', flat=True).first() or 0
                
                # Créer le nouveau modèle
                AIModel.objects.create(
                    provider=provider,
                    nom=nom,
                    model_id=model_id,
                    description=description or f"Modèle {nom} pour {provider.nom}",
                    est_gratuit=est_gratuit,
                    est_actif=False,
                    est_defaut=False,
                    ordre=last_order + 1
                )
                
                messages.success(request, f"Modèle {nom} ajouté avec succès")
                return redirect('api_configuration')
        
        elif action == 'delete_model':
            model_id = request.POST.get('model_id')
            
            if model_id:
                model = get_object_or_404(AIModel, id=model_id)
                model_name = model.nom
                provider_name = model.provider.nom
                
                # Ne pas supprimer le modèle par défaut
                if model.est_defaut:
                    messages.error(request, f"Impossible de supprimer le modèle par défaut. Veuillez d'abord définir un autre modèle par défaut.")
                    return redirect('api_configuration')
                
                # Supprimer le modèle
                model.delete()
                
                messages.success(request, f"Modèle {model_name} de {provider_name} supprimé avec succès")
                return redirect('api_configuration')
                
        elif action == 'refresh_models':
            # Rafraîchir les modèles
            force_update = request.POST.get('force_update') == 'on'
            count = refresh_ai_models(force=force_update)
            messages.success(request, f"{count} modèles mis à jour avec succès")
            return redirect('api_configuration')
    
    # Préparer les données pour le template
    providers_data = []
    for provider in providers:
        has_api_key = provider.api_keys.filter(est_active=True).exists()
        
        # Regrouper les modèles par type (gratuit ou payant)
        free_models = provider.models.filter(est_gratuit=True)
        paid_models = provider.models.filter(est_gratuit=False)
        
        providers_data.append({
            'provider': provider,
            'has_api_key': has_api_key,
            'free_models': free_models,
            'paid_models': paid_models
        })
    
    return render(request, 'landing/api_configuration.html', {
        'providers_data': providers_data,
        'user_contact': user.contact
    })

