# Courses App

Application Django pour gérer des foyers (Households) et leurs membres (Memberships).

## Stack technique

- Django 5
- PostgreSQL (Docker)
- Docker Compose
- Git / GitHub

## Fonctionnalités actuelles

- Authentification Django (admin)
- Création de foyers
- Gestion des membres d’un foyer
- Affichage des foyers de l'utilisateur connecté

## Lancer le projet

### 1. Démarrer la base de données

docker compose up -d

### 2. Appliquer les migrations

python manage.py migrate

### 3. Lancer le serveur

python manage.py runserver

Application disponible sur :
http://127.0.0.1:8000/

Admin :
http://127.0.0.1:8000/admin/
