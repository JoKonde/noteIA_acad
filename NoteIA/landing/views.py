import random
from django.shortcuts import render, redirect
from django.contrib import messages
from .models import CustomUser, Contact


def index(request):
    return render(request, 'landing/index.html')

def login(request):
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
    return render(request, 'landing/dashboard.html')


def custom_404(request, exception):
    return render(request, 'landing/404.html', status=404)

def custom_500(request):
    return render(request, 'landing/500.html', status=500)

