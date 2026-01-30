# FinFit Login Credentials

## Test Accounts

### Super Admin (accès au Dashboard FinFit)
- **Email:** `admin@finfit.com`
- **Password:** `admin123`
- **Redirect:** Dashboard FinFit (http://127.0.0.1:3001/)
- **Access:** Gestion complète, Ecommerce, Blog, Statistiques

### Regular User (accès au E-commerce)
- **Email:** `user@finfit.com`
- **Password:** `user123`
- **Redirect:** Site E-commerce (http://127.0.0.1:8000/)
- **Access:** Shopping, Wishlist, Cart

### Test User (accès au E-commerce)
- **Email:** `test@example.com`
- **Password:** `test123`
- **Redirect:** Site E-commerce (http://127.0.0.1:8000/)
- **Access:** Shopping, Wishlist, Cart

---

## Serveurs en cours d'exécution

### FastAPI Backend (E-commerce API + Auth)
- **URL:** http://127.0.0.1:8000/
- **API:** http://127.0.0.1:8000/api/
- **Login:** http://127.0.0.1:8000/signin.html
- **Port:** 8000

### Next.js Dashboard (FinFit Admin)
- **URL:** http://127.0.0.1:3001/
- **Port:** 3001 (3000 était déjà utilisé)

---

## Endpoints API

### Authentication
- `POST /api/login` - Login avec email/password
- `POST /api/register` - Enregistrement utilisateur

### E-commerce
- `GET /products?limit=12&page=1` - Liste des produits
- `GET /search?q=<query>` - Recherche RAG
- `POST /api/chat` - Chat RAG

---

## Flux d'authentification

1. Utilisateur va à http://127.0.0.1:8000/signin.html
2. Entre ses credentials (admin@finfit.com / admin123)
3. Frontend envoie `POST /api/login`
4. Backend retourne le `role` de l'utilisateur
5. Frontend redirige en fonction du rôle:
   - `super_admin` → Dashboard (port 3001)
   - `user` → E-commerce (port 8000)

---

## Tous les prix en Dinars Tunisiens (DT)

- Conversion automatique USD → DT (×3.15)
- Conversion automatique IDR → DT (÷15800×3.15)
- Format: "56.54 DT"

