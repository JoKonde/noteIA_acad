import random
from django.shortcuts import render, redirect
from django.contrib import messages
from .models import CustomUser, Contact, Cours,Note,Collaborateur,TextNote,ImageNote,PdfNote,TextNoteResume
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
    
    # Récupérer les collaborateurs si l'utilisateur est le propriétaire
    collaborators = None
    if is_owner:
        collaborators = Collaborateur.objects.filter(note=note)
    
    context = {
        'note': note,
        'textnotes': textnotes,
        'imagenotes': imagenotes,
        'pdfnotes': pdfnotes,
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
    
    # Préparer le prompt pour le résumé
    prompt = f"Fais un résumé concis et structuré du texte suivant. Identifie et mets en évidence les points clés:\n\n{all_texts}"
    
    try:
        # Récupérer la clé API depuis les variables d'environnement
        api_key = os.environ.get('OPENROUTER_API_KEY')
        
        if not api_key:
            messages.error(request, "Clé API OpenRouter non configurée. Veuillez configurer la variable d'environnement OPENROUTER_API_KEY.")
            return redirect('note_detail', note_id=note_id)
        
        # Préparation de la requête à l'API OpenRouter
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        
        data = {
            "model": "deepseek/deepseek-r1:free",
            "messages": [
                {
                    "role": "user",
                    "content": prompt
                }
            ]
        }
        
        # Envoi de la requête
        response = requests.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers=headers,
            json=data
        )
        
        # Récupération de la réponse
        if response.status_code == 200:
            result = response.json()
            resume_text = result["choices"][0]["message"]["content"]
            # Convertir le résumé Markdown en HTML
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

