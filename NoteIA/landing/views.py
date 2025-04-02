import random
from django.shortcuts import render, redirect
from django.contrib import messages
from .models import CustomUser, Contact
import jwt
import os
import datetime
from django.conf import settings

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
    except (jwt.ExpiredSignatureError, jwt.InvalidTokenError, CustomUser.DoesNotExist):
        messages.error(request, "Session expirée ou invalide. Veuillez vous reconnecter.")
        return redirect('login')

    return render(request, 'landing/dashboard.html', context)



def custom_404(request, exception):
    return render(request, 'landing/404.html', status=404)

def custom_500(request):
    return render(request, 'landing/500.html', status=500)

