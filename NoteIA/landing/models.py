import os
import base64
import random
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