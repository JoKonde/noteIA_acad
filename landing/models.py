import os
import base64
import random
import uuid
from django.db import models
from django.utils import timezone
from Crypto.Cipher import AES
from Crypto.Util.Padding import pad, unpad
from django.utils import timezone

# Clé secrète pour AES-256 (doit être de 32 octets)
AES_KEY = os.environ.get('AES_KEY', '0123456789abcdef0123456789abcdef').encode()  # à définir dans vos variables d'environnement

class Contact(models.Model):
    nom = models.CharField(max_length=100)
    postnom = models.CharField(max_length=100)
    prenom = models.CharField(max_length=100)
    sexe = models.CharField(max_length=1, choices=[('M', 'Masculin'), ('F', 'Féminin')])
    adresse = models.TextField()
    tel = models.CharField(max_length=20, unique=True)
    date = models.DateTimeField(default=timezone.now)

    def __str__(self):
        return f"{self.prenom} {self.nom}"


class CustomUser(models.Model):
    username = models.CharField(max_length=150, unique=True)
    password_encrypted = models.BinaryField()  # Stockage binaire du mot de passe chiffré
    contact = models.ForeignKey(Contact, on_delete=models.CASCADE)
    date = models.DateTimeField(default=timezone.now)

    def set_password(self, raw_password):
        cipher = AES.new(AES_KEY, AES.MODE_CBC)
        ct_bytes = cipher.encrypt(pad(raw_password.encode(), AES.block_size))
        # Stockage du vecteur d'initialisation (IV) avec le ciphertext
        self.password_encrypted = cipher.iv + ct_bytes

    def check_password(self, raw_password):
        iv = self.password_encrypted[:AES.block_size]
        ct = self.password_encrypted[AES.block_size:]
        cipher = AES.new(AES_KEY, AES.MODE_CBC, iv)
        try:
            pt = unpad(cipher.decrypt(ct), AES.block_size)
            return pt.decode() == raw_password
        except (ValueError, KeyError):
            return False

    def __str__(self):
        return self.username

class Cours(models.Model):
    nom = models.CharField(max_length=200, blank=False, null=False)
    description = models.TextField()
    # Lien vers l'utilisateur qui a créé le cours (suppression en cascade)
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE)
    date_creation = models.DateTimeField(default=timezone.now)

    def __str__(self):
        return self.nom

    class Meta:
        unique_together = ('nom', 'user')

#Explications :

#Le champ nom est requis et ne peut être vide.

#La contrainte unique_together = ('nom', 'user') garantit qu'un même utilisateur ne peut pas créer deux cours avec le même nom, mais autorise que différents utilisateurs puissent avoir un cours avec le même nom.


class Note(models.Model):
    titre = models.CharField(max_length=200)
    userOwner = models.ForeignKey('CustomUser', on_delete=models.CASCADE)
    date = models.DateTimeField(default=timezone.now)
    cours = models.ForeignKey('Cours', on_delete=models.CASCADE)

    def __str__(self):
        return self.titre

    class Meta:
        unique_together = ('titre', 'userOwner', 'cours')  # Vous pouvez choisir de rendre le titre unique par cours et owner

class TextNote(models.Model):
    note = models.ForeignKey(Note, on_delete=models.CASCADE)
    texte = models.TextField()
    date = models.DateTimeField(default=timezone.now)
    userEditeur = models.ForeignKey('CustomUser', on_delete=models.CASCADE)

    def __str__(self):
        return f"TextNote for {self.note.titre} by {self.userEditeur.username}"

class Collaborateur(models.Model):
    note = models.ForeignKey(Note, on_delete=models.CASCADE)
    userCollab = models.ForeignKey('CustomUser', on_delete=models.CASCADE)
    date = models.DateTimeField(default=timezone.now)

    def __str__(self):
        return f"Collaborateur {self.userCollab.username} on {self.note.titre}"
    
    
    
class ImageNote(models.Model):
    note = models.ForeignKey(Note, on_delete=models.CASCADE)
    path = models.CharField(max_length=200)   # ex. "img/ma_photo.png"
    date = models.DateTimeField(default=timezone.now)
    userEditeur = models.ForeignKey('CustomUser', on_delete=models.CASCADE)

    def __str__(self):
        return f"ImageNote for {self.note.titre} by {self.userEditeur.username}"


class PdfNote(models.Model):
    note = models.ForeignKey(Note, on_delete=models.CASCADE)
    path = models.CharField(max_length=200)    # ex. "pdf/mon_fichier.pdf"
    date = models.DateTimeField(default=timezone.now)
    userEditeur = models.ForeignKey('CustomUser', on_delete=models.CASCADE)

    def __str__(self):
        return f"PdfNote for {self.note.titre} by {self.userEditeur.username}"

class AudioNote(models.Model):
    note = models.ForeignKey(Note, on_delete=models.CASCADE)
    path = models.CharField(max_length=200)    # ex. "audio/mon_audio.mp3"
    titre = models.CharField(max_length=200, default="Audio sans titre")
    duree = models.IntegerField(default=0)  # Durée en secondes
    date = models.DateTimeField(default=timezone.now)
    userEditeur = models.ForeignKey('CustomUser', on_delete=models.CASCADE)

    def __str__(self):
        return f"AudioNote for {self.note.titre} by {self.userEditeur.username}"

class VideoNote(models.Model):
    note = models.ForeignKey(Note, on_delete=models.CASCADE)
    path = models.CharField(max_length=200)    # ex. "video/ma_video.mp4"
    titre = models.CharField(max_length=200, default="Vidéo sans titre")
    duree = models.IntegerField(default=0)  # Durée en secondes
    thumbnail = models.CharField(max_length=200, null=True, blank=True)  # Chemin vers la miniature
    date = models.DateTimeField(default=timezone.now)
    userEditeur = models.ForeignKey('CustomUser', on_delete=models.CASCADE)

    def __str__(self):
        return f"VideoNote for {self.note.titre} by {self.userEditeur.username}"

class OcrNote(models.Model):
    note = models.ForeignKey(Note, on_delete=models.CASCADE)
    image_path = models.CharField(max_length=200)  # ex. "ocr/image.jpg"
    texte_extrait = models.TextField()  # Texte extrait de l'image
    date = models.DateTimeField(default=timezone.now)
    userEditeur = models.ForeignKey('CustomUser', on_delete=models.CASCADE)

    def __str__(self):
        return f"OcrNote for {self.note.titre} by {self.userEditeur.username}"

class TextNoteResume(models.Model):
    uuid = models.UUIDField(default=uuid.uuid4, editable=False)
    note = models.ForeignKey(Note, on_delete=models.CASCADE)
    texte = models.TextField()
    date = models.DateTimeField(default=timezone.now)
    userEditeur = models.ForeignKey('CustomUser', on_delete=models.CASCADE)
    version = models.IntegerField(default=1)

    def __str__(self):
        return f"Résumé {self.version} pour {self.note.titre} par {self.userEditeur.username}"

    class Meta:
        unique_together = ('note', 'userEditeur', 'version')

class QuizNote(models.Model):
    uuid = models.UUIDField(default=uuid.uuid4, editable=False)
    note = models.ForeignKey(Note, on_delete=models.CASCADE)
    contenu = models.TextField()  # JSON stocké sous forme de texte
    questions = models.TextField(default='[]')  # Questions stockées sous forme de chaîne JSON
    date = models.DateTimeField(default=timezone.now)
    userEditeur = models.ForeignKey('CustomUser', on_delete=models.CASCADE)
    version = models.IntegerField(default=1)

    def __str__(self):
        return f"Quiz {self.version} pour {self.note.titre} par {self.userEditeur.username}"

    class Meta:
        unique_together = ('note', 'userEditeur', 'version')

class EdenConversation(models.Model):
    user = models.ForeignKey('CustomUser', on_delete=models.CASCADE)
    date_creation = models.DateTimeField(default=timezone.now)
    derniere_interaction = models.DateTimeField(default=timezone.now)
    
    def __str__(self):
        return f"Conversation de {self.user.username} du {self.date_creation.strftime('%d/%m/%Y')}"

class EdenMessage(models.Model):
    conversation = models.ForeignKey(EdenConversation, on_delete=models.CASCADE, related_name='messages')
    est_assistant = models.BooleanField(default=False)  # True pour Eden, False pour l'utilisateur
    contenu = models.TextField()
    date = models.DateTimeField(default=timezone.now)
    
    def __str__(self):
        sender = "Eden" if self.est_assistant else "Utilisateur"
        return f"Message de {sender} - {self.date.strftime('%H:%M:%S')}"
    
    class Meta:
        ordering = ['date']

# Modèles pour la gestion des API d'IA

class AIProvider(models.Model):
    """Fournisseur d'API d'IA (OpenRouter, DeepSeek, OpenAI, etc.)"""
    nom = models.CharField(max_length=100)
    code = models.CharField(max_length=50, unique=True)  # identifiant unique pour le fournisseur
    description = models.TextField(blank=True)
    url_api = models.URLField()
    est_actif = models.BooleanField(default=True)
    
    def __str__(self):
        return self.nom

class APIKey(models.Model):
    """Clé API pour un fournisseur d'IA"""
    provider = models.ForeignKey(AIProvider, on_delete=models.CASCADE, related_name='api_keys')
    key_encrypted = models.BinaryField()  # Stockage chiffré de la clé API
    date_ajout = models.DateTimeField(default=timezone.now)
    est_active = models.BooleanField(default=True)
    
    def set_key(self, raw_key):
        """Chiffre et stocke la clé API"""
        cipher = AES.new(AES_KEY, AES.MODE_CBC)
        ct_bytes = cipher.encrypt(pad(raw_key.encode(), AES.block_size))
        # Stockage du vecteur d'initialisation (IV) avec le ciphertext
        self.key_encrypted = cipher.iv + ct_bytes
    
    def get_key(self):
        """Déchiffre et retourne la clé API"""
        iv = self.key_encrypted[:AES.block_size]
        ct = self.key_encrypted[AES.block_size:]
        cipher = AES.new(AES_KEY, AES.MODE_CBC, iv)
        try:
            pt = unpad(cipher.decrypt(ct), AES.block_size)
            return pt.decode()
        except (ValueError, KeyError):
            return None
    
    def __str__(self):
        return f"Clé API pour {self.provider.nom} ({self.date_ajout.strftime('%d/%m/%Y')})"

class AIModel(models.Model):
    """Modèle d'IA disponible pour un fournisseur"""
    provider = models.ForeignKey(AIProvider, on_delete=models.CASCADE, related_name='models')
    nom = models.CharField(max_length=100)
    model_id = models.CharField(max_length=100)  # ID utilisé lors de l'appel API
    description = models.TextField(blank=True)
    est_gratuit = models.BooleanField(default=False)
    est_actif = models.BooleanField(default=False)
    est_defaut = models.BooleanField(default=False)  # Si c'est le modèle par défaut
    ordre = models.IntegerField(default=0)  # Pour trier les modèles
    
    class Meta:
        ordering = ['provider', 'ordre', 'nom']
        unique_together = ('provider', 'model_id')
    
    def __str__(self):
        return f"{self.nom} ({self.provider.nom})"
