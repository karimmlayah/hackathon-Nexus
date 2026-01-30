# 🔐 Système d'Authentification FinFit avec Rôles

## Architecture du Système

```
┌─────────────────────────────────────────────────────────────┐
│                    Utilisateur                              │
│              http://127.0.0.1:8000/signin.html             │
└────────────────┬────────────────────────────────────────────┘
                 │
                 │ Email + Password
                 ↓
┌─────────────────────────────────────────────────────────────┐
│                  FastAPI Backend                            │
│             POST /api/login                                 │
│  - Valide credentials                                       │
│  - Récupère le rôle (super_admin ou user)                  │
│  - Génère un token JWT                                      │
└────────────────┬────────────────────────────────────────────┘
                 │
                 │ { user: { email, name, role }, token }
                 ↓
┌─────────────────────────────────────────────────────────────┐
│              Frontend (signin.html)                          │
│  - Stocke le token et user info dans localStorage           │
│  - Vérifie le rôle                                          │
└────────────────┬────────────────────────────────────────────┘
                 │
         ┌───────┴──────┐
         │              │
    super_admin      user
         │              │
         ↓              ↓
    Dashboard      E-commerce
   Port 3001       Port 8000
```

## Comptes de Test

### 1. Super Admin
- **Email:** `admin@finfit.com`
- **Password:** `admin123`
- **Role:** `super_admin`
- **Redirection:** `http://127.0.0.1:3001/` (Dashboard FinFit)
- **Accès:** 
  - Gestion des projets
  - Gestion de l'e-commerce
  - Gestion du blog
  - Statistiques et analyses

### 2. Regular User
- **Email:** `user@finfit.com`
- **Password:** `user123`
- **Role:** `user`
- **Redirection:** `http://127.0.0.1:8000/` (E-commerce)
- **Accès:** 
  - Parcourir les produits
  - Ajouter au panier
  - Ajouter aux favoris
  - Faire des achats

### 3. Test User
- **Email:** `test@example.com`
- **Password:** `test123`
- **Role:** `user`
- **Redirection:** `http://127.0.0.1:8000/` (E-commerce)

## Flux d'Utilisation

### Pour les utilisateurs réguliers:

1. Ouvrez http://127.0.0.1:8000/signin.html
2. Entrez:
   - Email: `user@finfit.com`
   - Password: `user123`
3. Cliquez "Sign In"
4. Vous serez automatiquement redirigé vers le site e-commerce

### Pour les super admins:

1. Ouvrez http://127.0.0.1:8000/signin.html
2. Entrez:
   - Email: `admin@finfit.com`
   - Password: `admin123`
3. Cliquez "Sign In"
4. Vous serez automatiquement redirigé vers le dashboard FinFit

## Données Stockées

Après un login réussi, le navigateur stocke:

```javascript
// Dans localStorage:
localStorage['finfit_token'] = "abc123def456..."
localStorage['finfit_user'] = {
  "email": "admin@finfit.com",
  "name": "Admin User",
  "role": "super_admin"
}
```

## Endpoints API

### Authentification

#### POST /api/login
Authentifier un utilisateur et récupérer son rôle.

**Request:**
```json
{
  "email": "admin@finfit.com",
  "password": "admin123"
}
```

**Response:**
```json
{
  "success": true,
  "message": "Login successful",
  "access_token": "abc123def456...",
  "token_type": "bearer",
  "user": {
    "email": "admin@finfit.com",
    "name": "Admin User",
    "role": "super_admin"
  }
}
```

#### POST /api/register
Enregistrer un nouvel utilisateur.

**Request:**
```json
{
  "email": "newuser@example.com",
  "password": "password123",
  "name": "New User"
}
```

## Serveurs en Exécution

### 1. FastAPI Backend
- **Port:** 8000
- **URL:** http://127.0.0.1:8000/
- **Commande:** `uvicorn app:app --reload`
- **Fonctionnalités:**
  - API REST pour l'e-commerce
  - Authentification avec rôles
  - Recherche RAG
  - Chat RAG
  - Gestion des produits

### 2. Next.js Dashboard
- **Port:** 3001 (3000 était utilisé)
- **URL:** http://127.0.0.1:3001/
- **Commande:** `npm run dev`
- **Fonctionnalités:**
  - Tableau de bord admin
  - Gestion des projets
  - Statistiques
  - Gestion du blog
  - Gestion de l'e-commerce

## Sécurité

⚠️ **Note:** Ce système utilise des comptes de test hardcodés pour la démo. En production:
- Utiliser une base de données pour stocker les utilisateurs
- Hasher les mots de passe avec bcrypt ou argon2
- Utiliser des tokens JWT sécurisés
- Implémenter l'authentification OAuth2
- Ajouter la validation CSRF et les en-têtes de sécurité

## Troubleshooting

### "Port 3000 is in use"
Le dashboard Next.js utilise le port 3001 au lieu de 3000 car le port 3000 est déjà utilisé.
- URL correcte: http://127.0.0.1:3001/

### Login échoue
Vérifiez:
1. Le serveur FastAPI tourne sur le port 8000
2. Le format de l'email et du mot de passe
3. Utilisez les credentials de test exacts

### Redirection ne fonctionne pas
Vérifiez:
1. Les deux serveurs (8000 et 3001) sont en exécution
2. Le localStorage est activé dans le navigateur
3. Videz le cache du navigateur (Ctrl+Shift+Delete)

